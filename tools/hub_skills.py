"""Stdlib skill discovery and project-local copies; never runs skill installers."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib


SKILL_DIRS = (("skills", "both"), (".claude/skills", "claude"),
              (".codex/skills", "codex"), (".agents/skills", "codex"))


def local_skill_dirs(root):
    return sorted(marker.parent for folder in (".claude/skills", ".agents/skills")
                  for marker in (root / folder).glob("*/.hub-local"))


def manifest(root):
    path = root / "skills/external.toml"
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def markdown(value):
    return str(value).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def index_row(values):
    cells = [markdown(value) for value in values]
    for column, limit in ((0, 120), (4, 240)):
        if len(cells[column]) > limit:
            cells[column] = cells[column][:limit - 3] + "..."
    return "| " + " | ".join(cells) + " |"


def record_destination(path):
    path = Path(path)
    if os.environ.get("HUB_PORTABLE") == "1":
        root = Path(os.environ["HUB_RECORDS_ROOT"]).resolve()
        if not path.resolve().is_relative_to(root):
            raise ValueError("record path escapes working directory")
    return path


def skill_metadata(path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    front = re.match(r"\A---\s*\n(.*?)\n---", text, re.S)
    fields = dict(re.findall(r"^([\w-]+):\s*(.+)$", front[1], re.M)) if front else {}
    return {key: value.strip().strip("\"'") for key, value in fields.items()}, text


def requirements(text, entry):
    flags = list(entry.get("requires", []))
    for label, pattern in (
        ("MCP server", r"\bMCP\b|mcp__|mcpServers"),
        ("external command", r"allowed-tools:.*\bBash\b|\b(?:requires?|needs?|dependencies|prerequisites)\b[^\n]*(?:CLI|command|binary|npm|node|python|git|qwen|claude-9arm)|(?:^|\n)\s*(?:\$ |```(?:bash|sh|powershell))"),
        ("env var", r"\$\{?[A-Z][A-Z0-9_]{2,}|\b[A-Z][A-Z0-9_]*(?:_KEY|_TOKEN|_SECRET)\b|\benvironment variable\b"),
    ):
        if re.search(pattern, text, re.I if label != "env var" else 0):
            flags.append(label)
    return "; ".join("check: " + flag for flag in dict.fromkeys(flags)) or "not detected (check SKILL.md)"


def licence(path, boundary, fields, entry):
    if entry.get("licence") or fields.get("license") or fields.get("licence"):
        return entry.get("licence") or fields.get("license") or fields["licence"]
    for directory in (path.parent, *path.parent.parents):
        if not directory.is_relative_to(boundary):
            break
        files = sorted(p.name for p in directory.glob("*LICENSE*") if p.is_file())
        if files:
            return "file: " + str(directory / files[0]) + " (check terms)"
    return "unknown"


def skill_files(directory):
    # Skill managers often link directories; visit each real directory once, including Windows junctions.
    visited = set()
    for parent, folders, files in os.walk(directory, followlinks=True):
        resolved = Path(parent).resolve()
        if resolved in visited:
            folders[:] = []
            continue
        visited.add(resolved)
        folders[:] = sorted(folder for folder in folders if folder.lower() not in (".git", "node_modules"))
        if "SKILL.md" in files:
            yield Path(parent) / "SKILL.md"


def index_skills(root, destination=None):
    entries = {entry["name"]: entry for entry in manifest(root).get("skills", [])}
    roots = [(root / folder, vendor, False) for folder, vendor in SKILL_DIRS]
    home = Path.home()
    roots += [(home / folder, vendor, False) for folder, vendor in SKILL_DIRS if folder != "skills"]
    # CLIs keep installed plugin packages below these trees; do not assume plugin names or versions.
    roots += [(base / vendor / "plugins", vendor[1:], True) for base in (root, home)
              for vendor in (".claude", ".codex")]
    found, warnings = {}, []
    for directory, vendor, plugin in roots:
        if not directory.is_dir():
            continue
        for path in sorted(skill_files(directory)):
            try:
                resolved = path.resolve()
                kind = "direct"
                if plugin:
                    parts = tuple(part.lower() for part in path.relative_to(directory).parts)
                    kind = "cache" if parts[0] == "cache" and "marketplaces" not in parts else "catalog"
                locations = {v: kind for v in (("claude", "codex") if vendor == "both" else (vendor,))}
                if resolved in found:
                    priority = {"catalog": 0, "cache": 1, "direct": 2}
                    for v, location in locations.items():
                        previous = found[resolved]["vendors"].get(v, "catalog")
                        if priority[location] >= priority[previous]:
                            found[resolved]["vendors"][v] = location
                    continue
                fields, text = skill_metadata(path)
                name = fields.get("name", path.parent.name)
                # Manifest annotations apply only to our local copies, never an unrelated same-name skill.
                entry = entries.get(path.parent.name, {}) if (path.parent / ".hub-local").is_file() else {}
                found[resolved] = dict(name=name, path=path, vendors=locations,
                                       requirements=requirements(text, entry), licence=licence(path, directory, fields, entry),
                                       status=entry.get("status", "check compatibility"), notes=entry.get("notes", ""))
            except OSError as exc:
                warnings.append(f"unreadable skill {path}: {exc.strerror}")
    lines = ["# Skills index", "", "Discovery is not compatibility or dependency verification. Read requirements before use.",
             "Plugin cache activation is unverified. Catalog entries are not installed and are excluded from available counts.",
             "Same-name paths are separate entries. Name/licence cells are capped at 120/240 characters.", "",
             "| Name | Available to | Where | Requirements | Licence | Status / notes |", "|---|---|---|---|---|---|"]
    counts = dict(claude=0, codex=0, both=0)
    catalogs = 0
    for item in sorted(found.values(), key=lambda item: (item["name"].lower(), str(item["path"]))):
        available = {v: kind for v, kind in item["vendors"].items() if kind != "catalog"}
        if available:
            vendor = "both" if len(available) == 2 else next(iter(available))
            counts[vendor] += 1
            if "cache" in available.values():
                vendor += " (plugin cache, activation unverified)"
        else:
            vendor = "catalog (not installed)"
            catalogs += 1
        lines.append(index_row((item["name"], vendor, item["path"], item["requirements"],
                                item["licence"], item["status"] + "; " + item["notes"])))
    # Unsupported manifest entries remain visible even though they have no installed SKILL.md.
    for name, entry in entries.items():
        if entry.get("status") != "supported":
            lines.append(index_row((name, "none", entry.get("source", ""),
                         requirements("", entry), entry.get("licence", "unknown"),
                         entry.get("status", "unknown") + "; " + entry.get("notes", ""))))
    lines += ["", *warnings]
    destination = Path(destination) if destination is not None else root / "work/skills-index.md"
    destination = record_destination(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Skills: {sum(counts.values())} (claude: {counts['claude']}, codex: {counts['codex']}, both: {counts['both']})")
    print(f"Catalog skills (not installed): {catalogs}")
    print(destination)
    for warning in warnings:
        print("WARNING: " + warning)
    return 0


def identifier(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", value):
        raise ValueError("invalid source or skill identifier")
    return value


def git(*args, cwd=None):
    result = subprocess.run(["git", *map(str, args)], cwd=cwd, text=True, encoding="utf-8", errors="replace",
                            capture_output=True, timeout=120,
                            env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    if result.returncode:
        raise ValueError("git failed: " + (result.stderr.strip() or result.stdout.strip()))
    return result.stdout.strip()


def exclude_path(root):
    path = Path(git("rev-parse", "--git-path", "info/exclude", cwd=root))
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("git info/exclude is outside working directory; orchestrator must authorise/update it: " + str(path))
    return path


def install_skills(root):
    config = manifest(root)
    sources = {identifier(entry["id"]): entry for entry in config.get("sources", [])}
    checked_out, source_errors, failures = {}, {}, []
    for entry in config.get("skills", []):
        name = identifier(entry["name"])
        if entry.get("status") != "supported":
            print(f"UNSUPPORTED: {name} - {entry.get('notes', 'not approved for installation')}")
            continue
        try:
            source_id = identifier(entry["source"])
            source = sources[source_id]
            checkout = root / ".hub/vendor" / source_id
            if not checkout.resolve().is_relative_to(root.resolve()):
                raise ValueError("source checkout escapes working directory")
            if source_id in source_errors:
                raise ValueError("source already failed: " + source_errors[source_id])
            if source_id not in checked_out:
                try:
                    ref = source["ref"]
                    if not isinstance(ref, str) or not re.fullmatch(r"[0-9a-f]{40}", ref):
                        raise ValueError("source ref must be a full 40-character lowercase hex SHA")
                    checkout.parent.mkdir(parents=True, exist_ok=True)
                    if not checkout.exists():
                        git("clone", "--no-checkout", "--", source["repo"], checkout)
                    else:
                        if git("remote", "get-url", "origin", cwd=checkout) != source["repo"]:
                            raise ValueError("source checkout has a different origin")
                        git("fetch", "--tags", "origin", cwd=checkout)
                    git("checkout", "--detach", ref, "--", cwd=checkout)
                    actual = git("rev-parse", "HEAD", cwd=checkout)
                    if actual != ref:
                        raise ValueError("checked-out SHA does not match source ref")
                    checked_out[source_id] = actual
                except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                    source_errors[source_id] = str(exc)
                    raise
            relative = Path(entry["path"])
            directory = (checkout / relative).resolve()
            if relative.is_absolute() or not directory.is_relative_to(checkout.resolve()):
                raise ValueError("skill path escapes source checkout")
            if not (directory / "SKILL.md").is_file():
                raise ValueError("missing SKILL.md at " + str(directory))
            # Copy only repository-contained files; do not follow links out of the source.
            for path in directory.rglob("*"):
                if path.is_symlink() or not path.resolve().is_relative_to(checkout.resolve()):
                    raise ValueError("linked or escaping skill file: " + str(path))
            targets = [root / folder / name for folder in (".claude/skills", ".agents/skills")]
            for target in targets:
                if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
                    raise ValueError("linked or escaping install target: " + str(target))
                if target.exists() and not (target / ".hub-local").is_file():
                    raise ValueError("refusing to overwrite an unmarked skill: " + str(target))
            exclude = exclude_path(root)
            existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
            patterns = ["/" + target.relative_to(root).as_posix() + "/" for target in targets]
            additions = [pattern for pattern in patterns if pattern not in existing.splitlines()]
            if additions:
                exclude.parent.mkdir(parents=True, exist_ok=True)
                exclude.write_text(existing.rstrip("\n") + "\n" + "\n".join(additions) + "\n", encoding="utf-8")
            staging = root / ".hub/staging"
            if not staging.resolve().is_relative_to(root.resolve()):
                raise ValueError("staging directory escapes working directory")
            staging.mkdir(parents=True, exist_ok=True)
            for target in targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Stage the whole copy first so a failed copy preserves the previous install.
                with tempfile.TemporaryDirectory(dir=staging) as temporary:
                    staged = Path(temporary) / name
                    shutil.copytree(directory, staged)
                    (staged / ".hub-local").write_text(json.dumps(dict(source=source_id, ref=checked_out[source_id],
                                                                       licence=entry.get("licence", "unknown"))) + "\n", encoding="utf-8")
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.move(str(staged), str(target))
                print("LOCAL SKILL: " + target.relative_to(root).as_posix())
        except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
            failures.append(name)
            print(f"FAILED: {name} - {exc}")
    return 1 if failures else 0
