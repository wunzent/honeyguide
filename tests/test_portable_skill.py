import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def load_installer():
    spec = importlib.util.spec_from_file_location("install_hub_skill", ROOT / "tools/install_hub_skill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolated_env(home):
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), PYTHONPATH="")
    for key in ("HUB_PORTABLE", "HUB_PROJECT_ROOT", "HUB_WORK_ROOT", "HUB_RECORDS_ROOT", "HUB_MODEL_CATALOG"):
        env.pop(key, None)
    return env


def installed_wrapper(tmp_path):
    installer = load_installer()
    target = tmp_path / "home/.codex/skills/multi-agent-hub"
    installer.install(target)
    return installer, target / "scripts/run.py"


def test_legacy_defaults_remain_repository_root():
    code = "import tools.hub as h; assert h.work_root() == h.ROOT; assert h.records_root() == h.ROOT / 'work'; assert h.model_catalog() == h.ROOT / 'models.toml'"
    result = subprocess.run([PYTHON, "-c", code], cwd=ROOT,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_installed_wrapper_discovers_foreign_project_without_source_runtime(tmp_path):
    _, wrapper = installed_wrapper(tmp_path)
    project = tmp_path / "documents/Codex/foreign"
    (project / ".agents/skills/project-only").mkdir(parents=True)
    (project / ".agents/skills/project-only/SKILL.md").write_text(
        "---\nname: project-only\ndescription: fixture\n---\n", encoding="utf-8")
    result = subprocess.run([PYTHON, str(wrapper), "task", "new", "sample", "--objective", "portable",
                             "--scope", "fixture", "--orchestrator", "codex"], cwd=project,
                            env=isolated_env(tmp_path / "empty-user"), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert (project / ".multi-agent-hub/sample/CHECKPOINT.md").is_file()
    assert not (ROOT / "work/sample/CHECKPOINT.md").exists()
    result = subprocess.run([PYTHON, str(wrapper), "skills"], cwd=project,
                            env=isolated_env(tmp_path / "empty-user"), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    index = (project / ".multi-agent-hub/skills-index.md").read_text(encoding="utf-8")
    assert "project-only" in index


def test_installer_repeated_updates_keep_managed_backups_and_refuse_changes(tmp_path):
    installer = load_installer()
    target = tmp_path / "home/.codex/skills/multi-agent-hub"
    installer.install(target)
    marker = json.loads((target / installer.MARKER).read_text(encoding="utf-8"))
    expected_files = set(installer.bundle())
    assert {"agents/hub-readonly.md", "agents/hub-writer.md", "skills/software-component/SKILL.md"} <= expected_files
    assert set(marker["files"]) == expected_files
    assert all((target / name).is_file() for name in expected_files)
    assert (target / "runtime/hub.py").read_bytes() == (ROOT / "tools/hub.py").read_bytes()
    assert (target / "runtime/hub_skills.py").read_bytes() == (ROOT / "tools/hub_skills.py").read_bytes()
    assert (target / "runtime/models.toml").read_bytes() == (ROOT / "models.toml").read_bytes()
    installer.install(target)
    installer.install(target)
    backups = list((target.parent.parent / ".multi-agent-hub-backups").glob("multi-agent-hub-*"))
    assert len(backups) == 2
    assert all((backup / installer.MARKER).is_file() for backup in backups)
    (target / "SKILL.md").write_text("local edit", encoding="utf-8")
    with pytest.raises(ValueError, match="modified"):
        installer.install(target)
    extra = tmp_path / "extra"
    installer.install(extra)
    (extra / "user-content.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        installer.install(extra)
    malformed = tmp_path / "malformed"
    installer.install(malformed)
    (malformed / installer.MARKER).write_text('{"format": 99}', encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        installer.install(malformed)
    unmanaged = tmp_path / "unmanaged"
    unmanaged.mkdir()
    with pytest.raises(ValueError, match="unmanaged"):
        installer.install(unmanaged)


def test_installer_rejects_symlink_destination_entry(tmp_path):
    installer = load_installer()
    linked = tmp_path / "linked"
    installer.install(linked)
    try:
        (linked / "extra-link").symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="symlink"):
        installer.install(linked)


def test_failed_update_restores_previous_active_skill(tmp_path, monkeypatch):
    installer = load_installer()
    target = tmp_path / "home/.codex/skills/multi-agent-hub"
    installer.install(target)
    before = (target / installer.MARKER).read_bytes()
    real_rename = Path.rename

    def fail_new_bundle(self, destination):
        if self.parent.name.startswith(".mah-install-") and Path(destination) == target:
            raise OSError("injected replacement failure")
        return real_rename(self, destination)

    monkeypatch.setattr(Path, "rename", fail_new_bundle)
    with pytest.raises(OSError, match="injected replacement failure"):
        installer.install(target)
    assert (target / installer.MARKER).read_bytes() == before
    assert (target / "scripts/run.py").is_file()
    backups = list((target.parent.parent / ".multi-agent-hub-backups").glob("multi-agent-hub-*"))
    assert len(backups) == 1 and (backups[0] / installer.MARKER).is_file()


def test_installed_bundle_precedes_mutated_ancestor_hub_source(tmp_path):
    installer = load_installer()
    checkout = tmp_path / "hub-checkout"
    target = checkout / ".agents/skills/multi-agent-hub"
    installer.install(target)
    (checkout / "tools").mkdir()
    (checkout / "tools/hub.py").write_text("source mutated", encoding="utf-8")
    (checkout / "models.toml").write_text("source mutated", encoding="utf-8")
    (checkout / "skills/multi-agent-hub/scripts").mkdir(parents=True)
    (checkout / "skills/multi-agent-hub/scripts/run.py").write_text("source layout", encoding="utf-8")
    source = target / "scripts/run.py"
    spec = importlib.util.spec_from_file_location("installed_portable_wrapper", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.runtime_dir() == target / "runtime"
    assert (module.runtime_dir() / "hub.py").read_bytes() == (ROOT / "tools/hub.py").read_bytes()


def test_portable_mode_blocks_source_maintenance_and_external_install(tmp_path):
    _, wrapper = installed_wrapper(tmp_path)
    project = tmp_path / "foreign"
    project.mkdir()
    for args in (["sync"], ["skills", "install"]):
        result = subprocess.run([PYTHON, str(wrapper), *args], cwd=project,
                                env=isolated_env(tmp_path / "empty-user"), text=True, capture_output=True)
        assert result.returncode == 1
        assert "unavailable in portable mode" in result.stdout


def test_task_symlink_cannot_escape_portable_project(tmp_path):
    _, wrapper = installed_wrapper(tmp_path)
    project, outside = tmp_path / "foreign", tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (project / ".multi-agent-hub").mkdir()
    try:
        (project / ".multi-agent-hub/escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    result = subprocess.run([PYTHON, str(wrapper), "task", "new", "escape", "--objective", "x", "--scope", "y",
                             "--orchestrator", "codex"], cwd=project,
                            env=isolated_env(tmp_path / "empty-user"), text=True, capture_output=True)
    assert result.returncode == 1
    assert "escapes working directory" in result.stdout
    assert not (outside / "CHECKPOINT.md").exists()


def test_portable_record_descendant_symlinks_are_rejected(tmp_path):
    _, wrapper = installed_wrapper(tmp_path)
    project, outside = tmp_path / "foreign", tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    env = isolated_env(tmp_path / "empty-user")
    subprocess.run([PYTHON, str(wrapper), "task", "new", "sample", "--objective", "x", "--scope", "y",
                    "--orchestrator", "codex"], cwd=project, env=env, check=True, capture_output=True, text=True)
    records = project / ".multi-agent-hub"
    index_target = outside / "index.md"
    index_target.write_text("preserve index", encoding="utf-8")
    try:
        (records / "skills-index.md").symlink_to(index_target)
        log_target = outside / "log"
        log_target.mkdir()
        (records / "log").symlink_to(log_target, target_is_directory=True)
        agents_target = outside / "agents"
        agents_target.mkdir()
        (agents_target / "agent-1.md").write_text("outside agent secret marker", encoding="utf-8")
        (records / "sample/agents").rmdir()
        (records / "sample/agents").symlink_to(agents_target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    index_result = subprocess.run([PYTHON, str(wrapper), "skills"], cwd=project, env=env,
                                  text=True, capture_output=True)
    assert index_result.returncode == 1
    assert "record path escapes" in index_result.stdout
    assert index_target.read_text(encoding="utf-8") == "preserve index"
    log_result = subprocess.run([PYTHON, str(wrapper), "log", "outcome", "--text", "example"], cwd=project,
                                env=env, text=True, capture_output=True)
    assert log_result.returncode == 1
    assert not (log_target / ".lock").exists()
    status_result = subprocess.run([PYTHON, str(wrapper), "status", "sample"], cwd=project, env=env,
                                   text=True, capture_output=True)
    assert status_result.returncode == 1
    assert "record path escapes" in status_result.stdout
    assert "outside agent secret marker" not in status_result.stdout


def test_portable_attempt_history_detects_repeated_no_progress(tmp_path):
    _, wrapper = installed_wrapper(tmp_path)
    project = tmp_path / "foreign"
    project.mkdir()
    env = isolated_env(tmp_path / "empty-user")
    subprocess.run([PYTHON, str(wrapper), "task", "new", "sample", "--objective", "x", "--scope", "y",
                    "--orchestrator", "codex"], cwd=project, env=env, check=True, capture_output=True, text=True)
    command = [PYTHON, str(wrapper), "attempt", "sample", "--action", "inspect", "--outcome", "same blocker"]
    first = subprocess.run(command, cwd=project, env=env, text=True, capture_output=True)
    second = subprocess.run(command, cwd=project, env=env, text=True, capture_output=True)
    assert first.returncode == 0
    assert second.returncode == 5
    assert "NO PROGRESS" in second.stdout
    assert len((project / ".multi-agent-hub/sample/attempts.jsonl").read_text().splitlines()) == 2


def test_default_install_has_no_claude_destination_or_agents(tmp_path, monkeypatch):
    installer = load_installer()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    installer.main([])
    assert (tmp_path / "home/.codex/skills/multi-agent-hub" / installer.MARKER).is_file()
    assert not (tmp_path / "home/.claude").exists()
    with pytest.raises(SystemExit):
        installer.main(["--claude", "--dest", str(tmp_path / "x")])
    with pytest.raises(SystemExit):
        installer.main(["--claude-home", str(tmp_path / "x")])
    assert not (tmp_path / "x").exists()


def test_claude_install_places_skill_and_permission_shells(tmp_path):
    installer = load_installer()
    home = tmp_path / "claude"
    installer.main(["--claude", "--claude-home", str(home)])
    skill = home / "skills/multi-agent-hub"
    assert (skill / "SKILL.md").is_file() and (skill / "skills/software-component/SKILL.md").is_file()
    readonly = (home / "agents/hub-readonly.md").read_text(encoding="utf-8")
    writer = (home / "agents/hub-writer.md").read_text(encoding="utf-8")
    assert "\ntools: Read, Grep, Glob\n" in readonly and "Bash" not in readonly.split("---")[1]
    assert 'name: "hub-writer"' in writer
    generated = ROOT / ".claude/agents/hub-readonly.md"
    if generated.is_file():  # same bytes as `hub.py sync` produces
        assert generated.read_bytes().replace(b"\r\n", b"\n") == readonly.encode()
    managed = json.loads((home / "agents" / installer.MARKER).read_text(encoding="utf-8"))
    assert set(managed["files"]) == {"hub-readonly.md", "hub-writer.md"}
    installer.main(["--claude", "--claude-home", str(home)])  # idempotent update of managed files
    assert (home / "agents/hub-readonly.md").read_text(encoding="utf-8") == readonly


def test_claude_install_refuses_unmanaged_or_modified_agents_before_any_write(tmp_path):
    installer = load_installer()
    home = tmp_path / "claude"
    (home / "agents").mkdir(parents=True)
    (home / "agents/hub-writer.md").write_text("owner agent", encoding="utf-8")
    (home / "agents/other.md").write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit):
        installer.main(["--claude", "--claude-home", str(home)])
    assert (home / "agents/hub-writer.md").read_text(encoding="utf-8") == "owner agent"
    assert not (home / "skills").exists() and not (home / "agents/hub-readonly.md").exists()
    clean = tmp_path / "claude2"
    installer.main(["--claude", "--claude-home", str(clean)])
    (clean / "agents/hub-readonly.md").write_text("local edit", encoding="utf-8")
    with pytest.raises(SystemExit):
        installer.main(["--claude", "--claude-home", str(clean)])
    assert (clean / "agents/hub-readonly.md").read_text(encoding="utf-8") == "local edit"
    with pytest.raises(ValueError, match="modified"):
        installer.check_claude_agents(clean / "agents", installer.claude_agent_files())


def test_older_smaller_managed_bundle_can_be_updated(tmp_path):
    installer = load_installer()
    target = tmp_path / "skill"
    installer.install(target)
    marker = json.loads((target / installer.MARKER).read_text(encoding="utf-8"))
    for name in [n for n in marker["files"] if n.startswith(("skills/", "agents/"))]:
        (target / name).unlink()
        del marker["files"][name]
    for directory in sorted((p for p in target.rglob("*") if p.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    (target / installer.MARKER).write_text(json.dumps(marker), encoding="utf-8")
    installer.install(target)
    assert (target / "skills/software-component/SKILL.md").is_file()


def run_task_new(tmp_path, project, name="sample"):
    wrapper = tmp_path / "home/.codex/skills/multi-agent-hub/scripts/run.py"
    if not wrapper.is_file():
        installed_wrapper(tmp_path)
    return subprocess.run([PYTHON, str(wrapper), "task", "new", name, "--objective", "x", "--scope", "y",
                           "--orchestrator", "claude"], cwd=project, env=isolated_env(tmp_path / "empty-user"),
                          text=True, capture_output=True)


def test_claude_install_midway_failure_never_strands_unmanaged_files(tmp_path, monkeypatch):
    installer = load_installer()
    home = tmp_path / "claude"
    real = installer.write_atomic
    state = {"agents": 0}

    def fail_second_agent(path, data):
        if path.parent.name == "agents" and path.suffix == ".md":
            state["agents"] += 1
            if state["agents"] == 2:
                raise OSError("injected agent write failure")
        return real(path, data)

    monkeypatch.setattr(installer, "write_atomic", fail_second_agent)
    with pytest.raises(SystemExit):
        installer.main(["--claude", "--claude-home", str(home)])
    marker = json.loads((home / "agents" / installer.MARKER).read_text(encoding="utf-8"))
    written = {path.name for path in (home / "agents").glob("*.md")}
    assert set(marker["files"]) == written == {"hub-readonly.md"}
    assert marker["files"]["hub-readonly.md"] == installer.digest_bytes((home / "agents/hub-readonly.md").read_bytes())
    monkeypatch.setattr(installer, "write_atomic", real)
    installer.main(["--claude", "--claude-home", str(home)])  # the retry is not blocked by stranded files
    assert set(json.loads((home / "agents" / installer.MARKER).read_text(encoding="utf-8"))["files"]) == {"hub-readonly.md", "hub-writer.md"}


def test_codex_agents_opt_in_matches_sync_and_refuses_unowned_files(tmp_path, monkeypatch):
    installer = load_installer()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    installer.main([])
    assert not (tmp_path / "home/.codex/agents").exists()  # no default write
    home = tmp_path / "codex"
    installer.main(["--codex-agents", "--codex-home", str(home)])
    assert not (home / "skills").exists()
    for name in ("hub-readonly.toml", "hub-writer.toml"):
        generated = ROOT / ".codex/agents" / name
        installed = (home / "agents" / name).read_bytes()
        if generated.is_file():
            assert generated.read_bytes().replace(b"\r\n", b"\n") == installed
    assert b'sandbox_mode = "read-only"' in (home / "agents/hub-readonly.toml").read_bytes()
    installer.main(["--codex-agents", "--codex-home", str(home)])  # idempotent
    (home / "agents/hub-writer.toml").write_text("local edit", encoding="utf-8")
    with pytest.raises(SystemExit):
        installer.main(["--codex-agents", "--codex-home", str(home)])
    assert (home / "agents/hub-writer.toml").read_text(encoding="utf-8") == "local edit"
    other = tmp_path / "codex2"
    (other / "agents").mkdir(parents=True)
    (other / "agents/hub-readonly.toml").write_text("owner file", encoding="utf-8")
    with pytest.raises(SystemExit):
        installer.main(["--codex-agents", "--codex-home", str(other)])
    assert (other / "agents/hub-readonly.toml").read_text(encoding="utf-8") == "owner file"
    assert not (other / "agents/hub-writer.toml").exists()
    with pytest.raises(SystemExit):
        installer.main(["--codex-home", str(other)])
    with pytest.raises(SystemExit):
        installer.main(["--codex-agents", "--dest", str(tmp_path / "x")])


def test_agent_replacement_is_undone_when_its_hash_cannot_be_recorded(tmp_path, monkeypatch):
    installer = load_installer()
    agents = tmp_path / "agents"
    files = installer.claude_agent_files()
    real = installer.write_atomic

    def fail_marker(path, data):
        if path.name == installer.MARKER:
            raise OSError("injected marker failure")
        return real(path, data)

    monkeypatch.setattr(installer, "write_atomic", fail_marker)
    with pytest.raises(OSError, match="marker"):  # first install: the unrecorded file is removed
        installer.write_agents(agents, files)
    assert not (agents / "hub-readonly.md").exists()
    monkeypatch.setattr(installer, "write_atomic", real)
    installer.write_agents(agents, files)
    old = (agents / "hub-readonly.md").read_bytes()
    newer = dict(files, **{"hub-readonly.md": files["hub-readonly.md"] + b"changed\n"})
    monkeypatch.setattr(installer, "write_atomic", fail_marker)
    with pytest.raises(OSError, match="marker"):  # update: the previous recorded bytes come back
        installer.write_agents(agents, newer)
    assert (agents / "hub-readonly.md").read_bytes() == old
    monkeypatch.setattr(installer, "write_atomic", real)
    installer.write_agents(agents, newer)  # next installation is not refused
    assert (agents / "hub-readonly.md").read_bytes() == newer["hub-readonly.md"]


def tree_digest(root):
    import hashlib
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_portable_task_new_prints_hint_and_never_touches_git(tmp_path):
    project = tmp_path / "repo"
    (project / ".git/info").mkdir(parents=True)
    (project / ".git/HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
    (project / ".git/info/exclude").write_text("# keep", encoding="utf-8")
    before = tree_digest(project / ".git")
    result = run_task_new(tmp_path, project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Records are in .multi-agent-hub/; keep them out of commits" in result.stdout
    assert ".git/info/exclude" in result.stdout
    assert tree_digest(project / ".git") == before
    assert (project / ".multi-agent-hub/sample/CHECKPOINT.md").is_file()
