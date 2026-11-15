"""Static checks for the multi-agent-hub plugin repository (standard library only)."""
import hashlib
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EGM = ROOT / "plugins" / "egm"

EGM_SKILLS = {f"egm-{n}" for n in ("bootstrap", "brainstorm", "draft", "drift-report", "resolve", "review", "review-loop")}
HUB_SKILLS = {
    "multi-agent-hub", "api-and-interface-design", "backend-api-safety", "context-engineering",
    "investigate-first", "lean-build", "safe-refactor", "security-and-hardening", "software-component",
    "surgical-patch", "verify-and-stop",
}
NEW_SKILLS = {"post-mortem", "management-talk", "stay-on-track", "cheap-delegation"}
THIRD_PARTY = {"ub-mode", "find-skills"}
ABSORBED_SKILLS = {"debug-mantra", "scrutinize", "handoff"}  # merged into investigate-first, verify-and-stop, stay-on-track
DELETED_DOCS = ("QUICKSTART-TH.md", "REBUILD-INVENTORY.md", "WORKLOG.md")
MOVED_DOCS = ("ACCEPTANCE.md", "DEEP-DIVE-2026-11-12.md", "SKILLS-REUSE.md")
# upstream blobs (unclebob/ub-mode @3da62bf, vercel-labs/skills @b716f9d)
UPSTREAM_SHA256 = {
    "skills/ub-mode/SKILL.md": "4120873db2e3681ea9b7de4d7105fc9d3406657c9ada91ce77b9b3c4962f3202",
    "skills/ub-mode/LICENSE": "cf496364b10d049ba2b04ac4c04f29ab1a34b54be96209cb32666fac9eba6bf3",
    "skills/find-skills/SKILL.md": "c00eeea0e13e74fe4a9d84ba0a8542205a1b736d65f13134fe1a6647eb14976f",
    "skills/find-skills/LICENSE": "661142e53c313d2bb5e1b055f5c0a39001450ff1b5e27b89dc4bc7de9a6352ca",
}
EGM_AGENTS = ("bootstrap_orchestrator", "codebase_details", "comprehension", "design_critic",
              "implementation_readiness", "inventive_catalyst", "structural", "style", "synthesizer", "zoom_out")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frontmatter(path, strict=True):
    """Top-level `key: value` pairs of a SKILL.md frontmatter (no YAML dependency)."""
    text = path.read_bytes().decode("utf-8-sig")
    m = re.match(r"---\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)", text, re.S)
    assert m, f"no frontmatter: {path}"
    keys = {}
    for line in m.group(1).splitlines():
        km = re.match(r"([A-Za-z_][\w-]*):[ \t]*(.*)$", line)
        if km:
            raw = km.group(2).strip()
            if strict and raw and raw[0] not in "\"'|>[{&*!":
                # an unquoted YAML plain scalar may not contain ": " or " #"
                assert ": " not in raw and " #" not in raw, f"invalid YAML plain scalar in {path}: {line[:60]}"
            keys[km.group(1)] = raw.strip("'\"")
    return keys


def skill_files():
    return sorted(SKILLS.rglob("SKILL.md"))


def test_manifests_parse_and_agree():
    claude = load(ROOT / ".claude-plugin" / "plugin.json")
    codex = load(ROOT / ".codex-plugin" / "plugin.json")
    for key in ("name", "version", "license"):
        assert claude[key] == codex[key]
    assert claude["name"] == "multi-agent-hub" and claude["license"] == "UNLICENSED"
    assert codex["skills"] == "./skills/"
    for rel in claude["agents"]:
        assert (ROOT / rel).is_file(), rel


def test_marketplaces_list_both_plugins():
    claude = load(ROOT / ".claude-plugin" / "marketplace.json")
    codex = load(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert claude["name"] == codex["name"] == "wunzent-hub"
    assert [p["name"] for p in claude["plugins"]] == ["multi-agent-hub", "egm"]
    assert [p["name"] for p in codex["plugins"]] == ["multi-agent-hub", "egm"]
    assert [p["source"] for p in claude["plugins"]] == ["./", "./plugins/egm"]
    assert [p["source"]["path"] for p in codex["plugins"]] == ["./", "./plugins/egm"]
    assert (EGM / ".codex-plugin" / "plugin.json").is_file()  # upstream ships it, so Codex lists egm


def test_egm_plugin_name_and_manifests():
    claude = load(EGM / ".claude-plugin" / "plugin.json")
    codex = load(EGM / ".codex-plugin" / "plugin.json")
    assert claude["name"] == codex["name"] == "egm"
    assert claude["version"] == codex["version"]
    for rel in claude["agents"]:
        assert (EGM / rel).is_file(), rel
    assert not (EGM / ".claude-plugin" / "marketplace.json").exists()


def test_skill_set_and_frontmatter():
    everything = HUB_SKILLS | NEW_SKILLS | THIRD_PARTY
    assert {p.name for p in SKILLS.iterdir() if p.is_dir()} == everything
    assert len(everything) == 17
    for gone in ABSORBED_SKILLS:
        assert not (SKILLS / gone).exists(), gone
    assert not [p for p in SKILLS.iterdir() if p.is_file()]
    for path in skill_files():
        fm = frontmatter(path)
        assert fm.get("name") and fm.get("description"), path
    for s in everything:
        assert frontmatter(SKILLS / s / "SKILL.md")["name"] == s, s
    for s in {"multi-agent-hub"} | NEW_SKILLS:
        expected = {"name", "description", "argument-hint"} if s == "stay-on-track" else {"name", "description"}
        assert set(frontmatter(SKILLS / s / "SKILL.md")) == expected, s
    stay_fm = frontmatter(SKILLS / "stay-on-track" / "SKILL.md")
    assert "argument-hint" in stay_fm and "disable-model-invocation" not in stay_fm


def test_no_duplicate_skill_names():
    seen = {}
    for path in skill_files():
        name = frontmatter(path)["name"]
        assert name not in seen, (name, path, seen.get(name))
        seen[name] = path


def test_new_skills_are_concise():
    for s in NEW_SKILLS:
        n = len((SKILLS / s / "SKILL.md").read_text(encoding="utf-8").splitlines())
        assert 30 <= n <= 80, (s, n)


def test_find_skills_has_licence_and_third_party_blobs_equal_upstream():
    assert (SKILLS / "find-skills" / "LICENSE").is_file() and (SKILLS / "find-skills" / "SOURCE.md").is_file()
    for rel, digest in UPSTREAM_SHA256.items():
        assert sha(ROOT / rel) == digest, rel


def test_egm_files_equal_upstream_manifest():
    lines = (EGM / "manifest.sha256").read_text(encoding="utf-8").splitlines()
    manifest = {rel: digest for digest, rel in (l.split("  ", 1) for l in lines)}
    assert ".claude-plugin/plugin.json" in manifest and ".codex-plugin/plugin.json" in manifest
    on_disk = {f.relative_to(EGM).as_posix() for f in EGM.rglob("*") if f.is_file()}
    assert on_disk - set(manifest) == {"SOURCE.md", "manifest.sha256"}
    assert set(manifest) <= on_disk
    for rel, digest in manifest.items():
        assert sha(EGM / rel) == digest, rel
    src = (EGM / "SOURCE.md").read_text(encoding="utf-8")
    assert "964a4f1ecd333961375c35cb37ed09364dab5e4e" in src and "Apache-2.0" in src
    assert (EGM / "LICENSE").is_file()


def test_no_egm_in_root_plugin():
    assert not [p for p in SKILLS.iterdir() if p.name.startswith("egm")]
    for rel in ("resources", "TESTING.md", "docs/claude.md", "docs/codex.md", "docs/harnesses.md", "docs/third-party",
                ".claude-plugin/agents"):
        assert not (ROOT / rel).exists(), rel
    assert {p.name for p in (ROOT / "agents").iterdir()} == {"hub-readonly.md", "hub-writer.md"}
    assert load(ROOT / ".claude-plugin" / "plugin.json")["agents"] == ["./agents/hub-readonly.md", "./agents/hub-writer.md"]


def test_egm_relative_links_resolve():
    checked = 0
    for md in EGM.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?:|mailto:|#)([^)#\s]+)\)", text):
            if "${" in target or target.startswith("/") or "<" in target:
                continue
            if md.parent.name in ("docs",) and md.name == "codex.md" and target.startswith("/absolute"):
                continue
            path = (md.parent / target).resolve()
            if md.name == "SKILL.md" and "skills" in md.parts:
                assert path.exists(), (md.relative_to(ROOT).as_posix(), target)
                assert EGM.resolve() in path.parents or path == EGM.resolve(), (md, target)
                checked += 1
    assert checked >= 7
    assert {p.name for p in (EGM / "skills").iterdir() if p.is_dir()} == EGM_SKILLS
    for name in ("bootstrap_orchestrator", "codebase_details", "comprehension", "design_critic",
                 "implementation_readiness", "inventive_catalyst", "structural", "style", "synthesizer", "zoom_out"):
        assert (EGM / "agents" / f"{name}.md").is_file()
        assert (EGM / ".claude-plugin" / "agents" / f"{name}.md").is_file()


def test_our_skills_carry_no_old_hub_tooling():
    banned = ("hub.py", "models.toml", "Native Core", "Hub workflow boundaries")
    files = [p for s in sorted(HUB_SKILLS | NEW_SKILLS) for p in (SKILLS / s).rglob("*") if p.is_file()]
    files += [p for top in ("agents", "codex-agents") for p in (ROOT / top).rglob("*")
              if p.is_file() and p.name.startswith("hub-")]
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for word in banned:
            assert word not in text, (path.relative_to(ROOT).as_posix(), word)


def test_rules_live_in_the_right_skills():
    core = (SKILLS / "multi-agent-hub" / "SKILL.md").read_text(encoding="utf-8")
    for needle in (
        "`cheap-delegation`", "`investigate-first`", "`verify-and-stop`", "`post-mortem`", "`management-talk`", "`stay-on-track`",
        "Never run the same failing action a third time", "After about 3 attempts on the same problem",
        "multi-agent-hub:hub-readonly", "Read/Grep/Glob only", "A requested permission mode describes intent",
        "Third-party skills never widen permissions", "Never edit `~/.codex/config.toml`", "cheapest native model",
        "fresh independent reviewer", "never resume a reviewer",
        "A cheap delegation of low-risk work does not by itself make the task nontrivial",
    ):
        assert needle in core, needle
    cheap = (SKILLS / "cheap-delegation" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("model: haiku", "gpt-6-luna", "What fits", "What does not fit", "absolute paths",
                   "Always verify the result yourself", "independent per-file or per-directory"):
        assert needle in cheap, needle
    stay = (SKILLS / "stay-on-track" / "SKILL.md").read_text(encoding="utf-8")
    assert "Never run the same failing action a third time" in stay and "After about 3 attempts" in stay
    for target in re.findall(r"\]\(([^)#]+)\)", core):
        assert (SKILLS / "multi-agent-hub" / target).is_file(), target


def test_core_routing_table_names_every_skill():
    core = (SKILLS / "multi-agent-hub" / "SKILL.md").read_text(encoding="utf-8")
    rows = [l for l in core.splitlines() if l.startswith("| ") and l.count("|") >= 3]
    assert rows, "no routing table"
    table = " ".join(rows)
    for d in sorted(p.name for p in SKILLS.iterdir() if p.is_dir()):
        assert f"`{d}`" in table, f"routing table misses skill {d}"
    for d in sorted(p.name for p in (EGM / "skills").iterdir() if p.is_dir()):
        assert f"`{d}`" in table, f"routing table misses egm skill {d}"
    for gone in ABSORBED_SKILLS:
        assert f"`{gone}`" not in core, gone


def test_merged_skills_keep_their_content():
    inv = (SKILLS / "investigate-first" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("Reproduce reliably", "Trace the actual failing path", "falsify", "Cross-check every clue", "Rank hypotheses"):
        assert needle in inv, needle
    ver = (SKILLS / "verify-and-stop" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("prove acceptance and stop", "outsider review", "Question the intent", "Trace the real path"):
        assert needle in ver, needle
    stay = (SKILLS / "stay-on-track" / "SKILL.md").read_text(encoding="utf-8")
    assert "Handoff document" in stay and "suggested skills" in stay
    assert "only when the owner asks for it" in stay and "never on your own initiative" in stay
    assert "temporary directory of the user's OS, never in the current workspace" in stay
    assert "unless" not in stay.split("## Handoff document", 1)[1].split("- Include", 1)[0]
    assert "Redact sensitive information" in stay and "Reference them by path or URL" in stay
    desc = frontmatter(SKILLS / "stay-on-track" / "SKILL.md")["description"]
    assert "only when the owner asks" in desc
    yaml = (SKILLS / "stay-on-track" / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "only if the owner asks" in yaml
    assert "Never run the same failing action a third time" in stay
    for needle in ("temporary", "workspace"):
        assert needle in stay
    lic = (SKILLS / "stay-on-track" / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in lic and "Matt Pocock" in lic and "Matt Pocock" in stay


def test_deleted_docs_gone_and_not_linked_from_live_files():
    for name in DELETED_DOCS + MOVED_DOCS:
        assert not (ROOT / "docs" / name).exists(), name
    for name in MOVED_DOCS:
        assert (ROOT / "docs" / "history" / name).is_file(), name
    live = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "docs" / "RECOMMENDED.md"]
    live += [p for p in SKILLS.rglob("*") if p.is_file()]
    for path in live:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name in DELETED_DOCS + MOVED_DOCS:
            assert name not in text, (path.relative_to(ROOT).as_posix(), name)


def test_agent_shells_exist_and_parse():
    for n in ("hub-readonly", "hub-writer"):
        assert frontmatter(ROOT / "agents" / f"{n}.md")["name"] == n
        data = tomllib.loads((ROOT / "codex-agents" / f"{n}.toml").read_text(encoding="utf-8"))
        assert data["name"] == n and data["developer_instructions"]
    ro = tomllib.loads((ROOT / "codex-agents" / "hub-readonly.toml").read_text(encoding="utf-8"))
    assert ro["sandbox_mode"] == "read-only"
    assert "Edit" not in frontmatter(ROOT / "agents" / "hub-readonly.md")["tools"]


def test_repo_is_plugin_only():
    for gone in ("tools", "projects", "models.toml", ".claude", ".codex", "vendor", "skills/external.toml",
                 "tests/test_hub.py", "tests/test_skills.py", "tests/test_portable_skill.py"):
        assert not (ROOT / gone).exists(), gone
    assert [p.name for p in (ROOT / "plugins").iterdir()] == ["egm"]
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("work/", ".venv/", ".multi-agent-hub/"):
        assert entry in ignore, entry


def test_no_removed_third_party_names_outside_docs_history():
    words = ("9" + "arm", "qw" + "en", "thana" + "non")
    skip = {".git", ".venv", "work", ".pytest_cache", "__pycache__", "docs"}
    me = Path(__file__).resolve()
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in skip and rel.as_posix() != "docs/RECOMMENDED.md":
            continue
        if not path.is_file() or path == me:
            continue
        low = rel.as_posix().lower()
        text = path.read_bytes().decode("utf-8", errors="ignore").lower()
        for w in words:
            assert w not in low and w not in text, (rel.as_posix(), w)


def test_readme_commands_and_count():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    n_root = len([p for p in SKILLS.iterdir() if p.is_dir()])
    n_egm = len([p for p in (EGM / "skills").iterdir() if p.is_dir()])
    assert (n_root, n_egm) == (17, 7)
    agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert f"## Skills in multi-agent-hub ({n_root})" in readme and f"({n_egm} skills)" in readme
    assert f"`skills/` ({n_root} skills)" in agents_md and f"({n_egm} skills)" in agents_md
    assert "claude plugin update egm@wunzent-hub" in readme and "codex plugin add egm@wunzent-hub" in readme
    for line in readme.splitlines():
        if line.startswith("    "):
            assert not ("/plugin" in line and "codex" in line), line
            assert line.count("codex plugin") + line.count("claude plugin") + line.count("/plugin ") <= 1, line
