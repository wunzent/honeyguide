"""Install the owned portable Hub skill without changing CLI configuration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills/multi-agent-hub"
FILES = ("SKILL.md", "references/brief.md", "scripts/run.py")
RUNTIME = {"hub.py": ROOT / "tools/hub.py", "hub_skills.py": ROOT / "tools/hub_skills.py",
           "models.toml": ROOT / "models.toml"}
MARKER = ".multi-agent-hub-managed.json"


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_source(relative):
    source = SKILL / relative if relative in FILES else RUNTIME[Path(relative).name]
    if any(part.is_symlink() for part in (source, *source.parents) if part != ROOT.parent) or not source.is_file():
        raise ValueError("refusing symlink or missing source: " + str(source))
    if not source.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("source escapes repository: " + str(source))
    return source.read_bytes()


def validate_existing(destination):
    marker = destination / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("refusing unmanaged destination: " + str(destination))
    try:
        old = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid managed provenance") from exc
    if not isinstance(old, dict) or old.get("format") != 1 or old.get("source") != "multi-agent-hub" or not isinstance(old.get("files"), dict):
        raise ValueError("invalid managed provenance format")
    expected = set(FILES) | {"runtime/" + name for name in RUNTIME}
    if set(old["files"]) != expected or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in old["files"].values()):
        raise ValueError("managed provenance file list is invalid")
    for relative, expected_hash in old["files"].items():
        path = destination / relative
        if Path(relative).is_absolute() or not path.resolve().is_relative_to(destination.resolve()):
            raise ValueError("invalid managed file path")
        if path.is_symlink() or not path.is_file() or digest_bytes(path.read_bytes()) != expected_hash:
            raise ValueError("managed file was modified; refusing update: " + relative)
    allowed = expected | {MARKER}
    actual = set()
    for path in destination.rglob("*"):
        if path.is_symlink():
            raise ValueError("refusing symlink destination entry: " + str(path.relative_to(destination)))
        if path.is_file():
            actual.add(path.relative_to(destination).as_posix())
    if actual != allowed:
        raise ValueError("managed destination contains unexpected or missing content")
    allowed_dirs = {str(Path(name).parent).replace("\\", "/") for name in allowed if "/" in name}
    actual_dirs = {path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_dir()}
    if actual_dirs != allowed_dirs:
        raise ValueError("managed destination contains unexpected directories")


def install(destination):
    destination = Path(os.path.abspath(destination.expanduser()))
    for parent in (destination, *destination.parents):
        if parent.is_symlink():
            raise ValueError("refusing symlink install path: " + str(parent))
    hashes = {name: digest_bytes(read_source(name)) for name in FILES}
    hashes.update({"runtime/" + name: digest_bytes(read_source("runtime/" + name)) for name in RUNTIME})
    if destination.exists():
        validate_existing(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage_root = Path(tempfile.mkdtemp(prefix=".multi-agent-hub-install-", dir=destination.parent))
    staged = stage_root / destination.name
    try:
        for relative in FILES:
            target = staged / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(read_source(relative))
        for name in RUNTIME:
            target = staged / "runtime" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(read_source("runtime/" + name))
        (staged / MARKER).write_text(json.dumps({"format": 1, "source": "multi-agent-hub", "files": hashes}, indent=2) + "\n", encoding="utf-8")
        backup = None
        if destination.exists():
            backup_root = destination.parent.parent / ".multi-agent-hub-backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_root / (destination.name + "-" + uuid.uuid4().hex)
            destination.rename(backup)
        try:
            staged.rename(destination)
        except OSError as replacement_error:
            if backup is not None and backup.exists() and not destination.exists():
                try:
                    shutil.copytree(backup, destination)
                except OSError as restore_error:
                    raise OSError(f"replacement failed ({replacement_error}); old managed skill remains at {backup}; restore failed ({restore_error})") from replacement_error
            elif backup is None and not destination.exists():
                # First install has no active bundle to restore. A copy fallback
                # is safe only while the destination is still absent.
                shutil.copytree(staged, destination)
                return print(destination)
            raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
    print(destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, help="native skill directory (default: ~/.codex/skills/multi-agent-hub)")
    args = parser.parse_args(argv)
    try:
        install(args.dest or Path.home() / ".codex/skills/multi-agent-hub")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
