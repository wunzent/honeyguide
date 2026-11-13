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
    expected_files = set(installer.FILES) | {"runtime/" + name for name in installer.RUNTIME}
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
        if self.parent.name.startswith(".multi-agent-hub-install-") and Path(destination) == target:
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
