from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from datetime import datetime, timezone
import policy as policy_module
from approvals import build_record
from hashing import sha256_file
from policy import (
    Decision, PolicyError, check_data_root, check_scope, check_target_repo, expand,
    inside_git_repo, is_inside, load_policy, load_policy_unverified, may_spawn,
    question_class, team_active_seconds, worktree_path,
)
from state_writer import StateStore, plan_hash, set_approval_block


SPEC = "# Task\n\n## Proposed Plan\n\nImplement only the approved files.\n"
DEFAULTS = (Path(__file__).resolve().parents[1] / "config" / "policy.toml").read_text(encoding="utf-8")


def git_run(*args):
    return subprocess.run(["git", *map(str, args)], capture_output=True, text=True, check=True, timeout=10)


@pytest.fixture
def hub(tmp_path, monkeypatch):
    home = tmp_path / "codex-home"
    (home / ".sandbox").mkdir(parents=True)
    (home / ".sandbox" / "setup_marker.json").touch()
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setattr("adapters.codex_cli.host_skills_root", lambda: tmp_path / "host-skills")
    root = tmp_path / "hub"
    config = root / "config"
    config.mkdir(parents=True)
    secret = tmp_path / "secret"

    def record(kind, **bindings):
        return build_record(kind, quote="Approved in this conversation", desktop="codex",
                            now=datetime(2026, 11, 9, 12, tzinfo=timezone.utc), **bindings)

    text = DEFAULTS.replace(
        "data_root = 'C:\\Users\\Natthawut.j\\Desktop\\ALI\\multi-agent-hub-v2-data'",
        f"data_root = '{tmp_path / 'data'}'",
    ).replace("owner_secret_dir = '%USERPROFILE%\\.mah-v2-owner'", f"owner_secret_dir = '{secret}'")
    text = text.replace(
        "deny = ['C:\\Users\\Natthawut.j\\Desktop\\ALI\\multi-agent-hub', 'C:\\Users\\Natthawut.j\\Desktop\\ALI\\worktrees']",
        f"deny = ['{tmp_path / 'denied'}']",
    )
    (config / "policy.toml").write_text(text, encoding="utf-8")
    (root / "worker.py").write_text("VALUE = 1\n", encoding="utf-8")
    parsed = load_policy(root)
    state = {"project": "project", "task": "T-1", "status": "approved", "round": 1,
             "questions": [], "spawned_keys": {}}
    approval = record("approve-plan", project="project", task="T-1", plan_hash=plan_hash(SPEC),
                      policy_hash=parsed.policy_hash)
    state.update(approval=approval, approval_history=[approval])
    return SimpleNamespace(root=root, config=config, record=record, policy=parsed,
                           state=state, spec=set_approval_block(SPEC, approval))


def gate(hub, **changes):
    arguments = dict(policy=hub.policy, spec_text=hub.spec,
                     state=hub.state, live_runs=[], role="coder", idem_key="T-1:coder:1")
    arguments.update(changes)
    return may_spawn(**arguments)


def test_production_defaults(hub):
    import tomllib

    defaults = tomllib.loads(DEFAULTS)
    assert defaults["hub"] == {"max_processes": 2, "max_dynamic": 1,
                               "security_gate": "NOT PASS", "mode": "manual-trusted-approval"}
    assert defaults["codex"]["verified_version"] == "0.167.0"
    assert hub.policy.codex_verified_version == "0.167.0"
    assert defaults["paths"]["max_path_len"] == 200
    assert defaults["paths"]["owner_secret_dir"] == "%USERPROFILE%\\.mah-v2-owner"
    assert defaults["caps"] == {"coder_tester_rounds": 3, "review_fix_cycles": 1,
                                "respawn_per_key": 1, "team_minutes": 60}
    assert defaults["quota"] == {"backoff_minutes": [15, 30, 60, 120, 240],
                                 "max_attempts_per_episode": 5, "max_episodes_per_task_per_day": 3,
                                 "verified_reset_grace_minutes": 2}
    assert set(defaults["routing"]["roles"]) == {"planner", "coder", "tester", "reviewer", "doc-keeper"}
    assert all(settings["auto_fallback"] is False for settings in defaults["routing"]["roles"].values())
    assert defaults["routing"]["roles"]["reviewer"]["reviewer_must_differ"] is True
    assert hub.policy.policy_hash == sha256_file(hub.config / "policy.toml")
    assert hub.policy.raw["hub"]["max_processes"] == hub.policy.max_processes == 2
    assert load_policy_unverified(hub.root) == hub.policy


def test_auto_fallback_defaults_false(hub):
    path = hub.config / "policy.toml"
    path.write_text(path.read_text(encoding="utf-8").replace("auto_fallback = false\n", ""), encoding="utf-8")
    assert all(s["auto_fallback"] is False for s in load_policy(hub.root).routing_roles.values())


@pytest.mark.parametrize("before,after", [
    ("max_processes = 2", "max_processes = true"),
    ("max_dynamic = 1", "max_dynamic = 3"),
    ("respawn_per_key = 1", "respawn_per_key = -1"),
    ("max_attempts_per_episode = 5", "max_attempts_per_episode = 6"),
    ('mode = "manual-trusted-approval"', 'mode = "automatic"'),
    ('security_gate = "NOT PASS"', 'security_gate = "PASS"'),
    ('"choose-approach"]', '"security"]'),
    ("reviewer_must_differ = true", "reviewer_must_differ = false"),
    ('allowed_vendors = ["claude", "codex"]', 'allowed_vendors = ["other"]'),
    ("auto_fallback = false", 'auto_fallback = "false"'),
    ("[routing.roles.planner]", "[routing.roles.unknown]"),
    ('routine = "low"', ''),
    ('standard = "medium"', 'standard = "xhigh"'),
    ('complex = "high"', 'complex = true'),
    ('max_default_effort = "low"', 'max_default_effort = "max"'),
])
def test_policy_schema_fails_closed(hub, before, after):
    path = hub.config / "policy.toml"
    path.write_text(path.read_text(encoding="utf-8").replace(before, after), encoding="utf-8")
    with pytest.raises(PolicyError, match="invalid policy"):
        load_policy_unverified(hub.root)


def test_policy_read_failures(hub, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(policy_module, "read_text_retry", lambda _: (_ for _ in ()).throw(PermissionError("denied")))
        with pytest.raises(PolicyError, match="could not read"):
            load_policy(hub.root)
    (hub.config / "policy.toml").write_text("[broken", encoding="utf-8")
    with pytest.raises(PolicyError):
        load_policy_unverified(hub.root)


def test_expand_and_containment(tmp_path, monkeypatch):
    monkeypatch.setenv("MAH_TEST_ROOT", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert expand("%MAH_TEST_ROOT%/missing") == (tmp_path / "missing").resolve()
    assert expand("~/missing") == (tmp_path / "missing").resolve()
    assert is_inside(tmp_path / "missing", tmp_path)
    assert is_inside(tmp_path, tmp_path)
    assert not is_inside(tmp_path.with_name(tmp_path.name + "-sibling"), tmp_path)
    if os.name == "nt":
        assert is_inside(Path(str(tmp_path).upper()) / "child", Path(str(tmp_path).lower()))
        assert not is_inside(Path("X:/data"), Path("Y:/data"))
    monkeypatch.delenv("MAH_UNSET_TEST_VAR", raising=False)
    with pytest.raises(PolicyError):
        expand("%MAH_UNSET_TEST_VAR%/data")


def test_git_detection_real_and_injected(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git_run("init", repo)
    assert inside_git_repo(repo / "missing" / "child")
    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    assert inside_git_repo(linked)
    calls = []

    def git(arguments, **options):
        calls.append(arguments)
        return SimpleNamespace(returncode=0 if Path(arguments[2]) == tmp_path else 128)

    assert inside_git_repo(tmp_path / "nonexistent", git=git)
    assert calls[0][2] == str(tmp_path.resolve())
    calls.clear()
    assert not inside_git_repo(tmp_path / "nonexistent", git=lambda *a, **k: SimpleNamespace(returncode=128))


def test_git_failure_does_not_prove_safe(tmp_path):
    def denied(*args, **kwargs):
        raise PermissionError("git unavailable")

    with pytest.raises(PolicyError, match="git ancestry"):
        inside_git_repo(tmp_path, git=denied)


def test_data_root_valid_outside_repos(hub):
    root = check_data_root(hub.policy, hub.root)
    assert root == expand(hub.policy.data_root)
    assert not root.exists()  # Validation never creates or deletes paths.


def test_data_root_in_real_git_repo_rejected(hub, tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    git_run("init", repo)
    with pytest.raises(PolicyError, match="git repo"):
        check_data_root(replace(hub.policy, data_root=str(repo / "missing" / "data")), hub.root)


@pytest.mark.parametrize("kind", ["hub", "deny", "v1", "P7", "registered"])
def test_data_root_forbidden(hub, tmp_path, kind):
    roots = {"hub": hub.root, "deny": tmp_path / "denied", "v1": tmp_path / "multi-agent-hub",
             "P7": tmp_path / "worktrees", "registered": tmp_path / "registered"}
    configured = replace(hub.policy, data_root=str(roots[kind] / "data"))
    with pytest.raises(PolicyError, match="forbidden"):
        check_data_root(configured, hub.root, registered_repos=[roots["registered"]])


@pytest.mark.parametrize("project,task", [("..", "T-1"), ("p", "../T-1"), ("p/x", "T-1"),
                                         ("p", "T_1"), ("p", ""), ("p", "x" * 33), ("p\n", "T-1")])
def test_worktree_ids_reject_traversal(hub, project, task):
    with pytest.raises(PolicyError, match="ID"):
        worktree_path(hub.policy, project, task)


def test_worktree_path_and_length(hub):
    path = worktree_path(hub.policy, "project-1", "T-1")
    assert path == expand(hub.policy.data_root) / "worktrees" / "project-1" / "T-1"
    assert worktree_path(replace(hub.policy, max_path_len=len(str(path))), "project-1", "T-1") == path
    with pytest.raises(PolicyError, match="max_path_len"):
        worktree_path(replace(hub.policy, max_path_len=len(str(path)) - 1), "project-1", "T-1")
    traversal = str(Path(hub.policy.data_root) / ".." / "data")
    with pytest.raises(PolicyError, match="traversal"):
        worktree_path(replace(hub.policy, data_root=traversal), "p", "T-1")


def test_junction_worktree_escape_rejected(hub, tmp_path):
    root = expand(hub.policy.data_root)
    root.mkdir()
    destination = tmp_path / "outside"
    destination.mkdir()
    link = root / "worktrees"
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(destination)],
                                capture_output=True, text=True, check=False, timeout=10)
        if result.returncode:
            pytest.skip("junction creation is not permitted")
    else:
        link.symlink_to(destination, target_is_directory=True)
    try:
        with pytest.raises(PolicyError, match="alias"):
            worktree_path(hub.policy, "p", "T-1")
    finally:
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()
    assert destination.is_dir()


def test_target_repo_constraints(hub, tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    git_run("init", repo)
    assert check_target_repo(hub.policy, repo, hub.root) == repo.resolve()
    for path in (hub.root, tmp_path / "multi-agent-hub", tmp_path / "denied", tmp_path / "worktrees",
                 expand(hub.policy.data_root) / "target", tmp_path / "not-repo"):
        with pytest.raises(PolicyError):
            check_target_repo(hub.policy, path, hub.root)


@pytest.mark.parametrize("paths,globs,expected", [
    (["src/a.py", "src/nested/b.py", "README.md"], ["src/*.py"], ["README.md"]),
    (["src\\a.py"], ["src/*.py"], []),
    (["../x", "src/../x", "src\\..\\x", "/tmp/x", "C:\\x", "C:x", "\\root", "\\\\host\\share\\x", ""],
     ["*"], ["../x", "src/../x", "src\\..\\x", "/tmp/x", "C:\\x", "C:x", "\\root", "\\\\host\\share\\x", ""]),
    (["a.py"], [], ["a.py"]),
    (["A.py", "a.py"], ["a.py"], ["A.py"]),
])
def test_scope(paths, globs, expected):
    assert check_scope(paths, globs) == expected


@pytest.mark.parametrize("qtype,expected", [("clarify", "clarify"), ("naming", "clarify"),
                                           ("choose-approach", "clarify"), ("unknown", "owner-decision"),
                                           ("approve-plan", "owner-decision"), ("security", "owner-decision"),
                                           ("scope", "owner-decision"), ("policy", "owner-decision")])
def test_question_classes(hub, qtype, expected):
    assert question_class(hub.policy, qtype) == expected
    assert question_class(replace(hub.policy, relay_types=[]), qtype) == "owner-decision"


def test_valid_spawn_checks_plain_approval(hub, monkeypatch):
    calls = []
    verify = policy_module.check_approval
    def observed(record, **bindings):
        calls.append(record["kind"])
        return verify(record, **bindings)
    monkeypatch.setattr(policy_module, "check_approval", observed)
    assert gate(hub) == Decision(True, "approval and spawn checks passed")
    assert calls == ["approve-plan"]
    assert hub.policy.security_gate == "NOT PASS"


@pytest.mark.parametrize("change", ["absent", "wrong-plan", "policy-changed", "forged", "wrong-task",
                                    "wrong-project", "duplicate-nonce", "agent-text", "verification-exception"])
def test_spawn_approval_failures(hub, monkeypatch, change):
    spec = hub.spec
    if change == "absent":
        hub.state.pop("approval")
    elif change == "wrong-plan":
        spec = spec.replace("approved files", "other files")
    elif change == "policy-changed":
        with (hub.config / "policy.toml").open("a", encoding="utf-8") as stream:
            stream.write("\n# changed after approval\n")
        hub.policy = load_policy(hub.root)
    elif change == "forged":
        hub.state["approval"] = {"approved": True}
    elif change in {"wrong-task", "wrong-project"}:
        hub.state[change.removeprefix("wrong-")] = "other"
    elif change == "duplicate-nonce":
        hub.state["approval_history"].append(hub.state["approval"])
    elif change == "agent-text":
        hub.state.pop("approval")
        spec = SPEC + "\n## Approval\nAPPROVED\n"
    else:
        def broken(*args, **kwargs):
            raise RuntimeError("verifier unavailable")
        monkeypatch.setattr(policy_module, "check_approval", broken)
    assert not gate(hub, spec_text=spec).ok


def test_spawn_rechecks_loaded_policy(hub):
    assert not gate(hub, policy=replace(hub.policy, max_processes=999)).ok
    hub.policy.raw["hub"]["max_processes"] = 999
    assert not gate(hub).ok
    hub.policy = load_policy(hub.root)
    (hub.root / "worker.py").write_text("changed", encoding="utf-8")
    assert gate(hub).ok


@pytest.mark.parametrize("status", ["draft", "awaiting-approval", "needs-you", "waiting-quota", "done", "failed"])
def test_spawn_status_blocked(hub, status):
    hub.state["status"] = status
    assert not gate(hub).ok


@pytest.mark.parametrize("role,status", [("planner", "approved"), ("coder", "running"),
                                         ("tester", "testing"), ("tester", "running"),
                                         ("reviewer", "reviewing"), ("doc-keeper", "reviewing")])
def test_spawn_role_status_allowlist(hub, role, status):
    hub.state["status"] = status
    assert gate(hub, role=role).ok
    assert not gate(hub, role="unknown").ok


def test_spawn_blocking_questions(hub):
    hub.state["questions"] = [{"blocking": True, "status": "open"}]
    assert "blocking" in gate(hub).reason
    hub.state["questions"][0]["status"] = "relayed"
    assert not gate(hub).ok
    hub.state["questions"][0]["status"] = "answered"
    assert gate(hub).ok
    hub.state["questions"] = [{"blocking": False, "status": "open"}]
    assert gate(hub).ok


def test_spawn_slots(hub):
    assert gate(hub, live_runs=[{}]).ok
    assert "process slots" in gate(hub, live_runs=[{}, {}]).reason
    assert "dynamic slots" in gate(hub, dynamic=True, live_runs=[{"dynamic": True}]).reason
    assert gate(hub, dynamic=True, live_runs=[{"dynamic": False}]).ok
    assert gate(hub, dynamic=True).ok


def test_spawn_team_cap_counts_active_runs_only(hub):
    from datetime import datetime, timedelta, timezone
    first = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
    hub.state.update(first_dispatch_at=first.isoformat(), team_active_seconds=120)
    assert gate(hub, now=first + timedelta(hours=10)).ok
    hub.state['runs'] = {'run': {'status': 'running', 'started_at': first.isoformat()}}
    assert team_active_seconds(hub.state, first + timedelta(seconds=30)) == 150
    assert gate(hub, now=first + timedelta(minutes=57)).ok
    assert gate(hub, now=first + timedelta(minutes=58)).reason == 'team time cap reached'
    hub.state['runs']['run'] = {'status': 'running', 'create_time': first.timestamp()}
    assert team_active_seconds(hub.state, first + timedelta(seconds=30)) == 150
    hub.state['runs']['run']['status'] = 'ok'
    assert team_active_seconds(hub.state, first + timedelta(hours=10)) == 120


def test_spawn_duplicate_and_bounded_respawn(hub):
    key = "T-1:coder:1"
    assert not gate(hub, live_runs=[{"idem_key": key}]).ok
    for keys in ({key: 2}, [key, key]):
        hub.state["spawned_keys"] = keys
        assert "duplicate key" in gate(hub).reason
    for keys in ({key: 1}, [key]):
        hub.state["spawned_keys"] = keys
        assert gate(hub).ok  # Exactly one respawn; recording the next start exhausts it.


@pytest.mark.parametrize("name,value,allowed", [("round", 3, True), ("round", 4, False),
                                               ("review_fix_cycles", 1, True), ("review_fix_cycles", 2, False),
                                               ("team_active_seconds", 3599, True), ("team_active_seconds", 3600, False),
                                               ("round", -1, False), ("round", True, False),
                                               ("team_active_seconds", float("nan"), False)])
def test_spawn_caps(hub, name, value, allowed):
    hub.state[name] = value
    assert gate(hub).ok is allowed


@pytest.mark.parametrize("change", [{"questions": ["invalid"]}, {"spawned_keys": None},
                                    {"spawned_keys": {"T-1:coder:1": True}}, {"project": None}])
def test_spawn_malformed_state_fails_closed(hub, change):
    hub.state.update(change)
    assert not gate(hub).ok


def test_gate_is_read_only_and_works_with_state_store(hub):
    store = StateStore(hub.root)
    store.write_spec("project", "T-1", hub.spec)
    with store.transaction("project", "T-1") as txn:
        txn.state.update(hub.state)
        txn.emit("approval.signed", {"set": hub.state})
    state = store.read_state("project", "T-1")
    before = deepcopy(state)
    spec = store.read_spec("project", "T-1")
    assert gate(hub, state=state, spec_text=spec).ok
    assert state == before
    assert store.read_state("project", "T-1") == before


@pytest.mark.parametrize('value', ['*', [1], [None], ['']])
def test_artifact_allowlist_schema(hub, value):
    raw = deepcopy(hub.policy.raw)
    raw['scope']['ignored_artifact_globs'] = value
    with pytest.raises(PolicyError, match='invalid policy'):
        policy_module._parse_policy(hub.root, raw, hub.policy.policy_hash)


def test_artifact_allowlist_is_explicit(hub):
    assert hub.policy.ignored_artifact_globs == [
        '**/__pycache__/**', '**/*.pyc', '.pytest_cache/**', '**/.pytest_cache/**']


@pytest.mark.parametrize("value", [None, {}, {"verified_version": 167}, {"verified_version": ""}])
def test_missing_or_invalid_codex_pin_keeps_claude_policy_usable(hub, value):
    from policy import _parse_policy
    raw = deepcopy(hub.policy.raw)
    if value is None:
        raw.pop("codex")
    else:
        raw["codex"] = value
    parsed = _parse_policy(hub.root, raw, "test-policy-hash")
    assert parsed.codex_verified_version is None
    assert parsed.routing_roles["coder"] == hub.policy.routing_roles["coder"]
    assert parsed.security_gate == "NOT PASS"
