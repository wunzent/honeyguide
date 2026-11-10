from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import subprocess

import psutil
import pytest

from adapters.base import Availability, Route
from model_router import RouteError, load_catalog, resolve
from policy import PolicyError
from runner import Runner, is_same_process
from state_writer import StateStore, plan_hash
from worktree_manager import GitForbidden, WorktreeManager, run_git
from test_path_policy import hub


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def unchanged_v1(tmp_path_factory):
    # This round is offline and must never access the owner's v1 checkout.
    v1 = tmp_path_factory.mktemp('isolation') / 'multi-agent-hub'
    v1.mkdir()
    assert run_git(['init'], v1)[0] == 0

    def snapshot():
        result = subprocess.run(["git", "--no-optional-locks", "-c", f"safe.directory={v1.as_posix()}",
                                 "-C", str(v1), "status", "--porcelain"], capture_output=True,
                                env=os.environ | {"GIT_OPTIONAL_LOCKS": "0"}, check=True, timeout=20)
        return result.stdout

    before = snapshot()
    yield before
    assert snapshot() == before, "v1 git status changed during the session"


def test_v1_status_snapshot(unchanged_v1):
    if unchanged_v1 is None:
        pytest.skip("v1 path missing")
    assert isinstance(unchanged_v1, bytes)


@pytest.mark.parametrize('args', [
    ['diff', '--output=escape'], ['diff', '--output', 'escape'], ['diff', '-o', 'escape'],
    ['log', '-1', '--exec=evil'], ['status', '-c', 'alias.x=evil'],
    ['status', '--config=x'], ['status', '-C', '..'],
    ['commit', '-F', 'message'], ['commit', '--file=message'],
    ['diff', '--upload-pack=evil'], ['diff', '--receive-pack', 'evil'],
    ['status', '--git-dir=elsewhere'], ['status', '--work-tree=elsewhere'],
    ['add', '--all'], ['add', '-f', 'ignored'], ['add', '--', '../escape'],
    ['add', '--', 'C:/escape'], ['add', '--', ':(top)../escape'],
    ['add', '--', '.git/config'], ['commit', '--interactive'],
    ['diff', '--', '--git-dir=elsewhere'], ['status', '--', '--work-tree=elsewhere'],
])
def test_git_subcommand_flags_rejected(tmp_path, monkeypatch, args):
    monkeypatch.setattr('worktree_manager.subprocess.run', lambda *a, **k: pytest.fail('unsafe git reached subprocess'))
    with pytest.raises(GitForbidden):
        run_git(args, tmp_path)


def test_ignored_writes_are_scope_changes(target):
    (target / '.gitignore').write_text('ignored/\n', encoding='utf-8')
    (target / 'ignored').mkdir()
    (target / 'ignored' / 'secret.txt').write_text('write', encoding='utf-8')
    changes = WorktreeManager().changed_files(target)
    assert 'ignored/secret.txt' in changes


def test_ignored_artifact_filter_preserves_status_boundaries(hub, tmp_path):
    output = "\0".join([
        "!! __pycache__/module.pyc", "!! nested/__pycache__/module.pyc",
        "!! .pytest_cache/v/cache/nodeids", "!! nested/.pytest_cache/v/cache/nodeids",
        "!! cached.pyc", "!! build/out.bin", "!! secrets.env",
        "?? outside.pyc", " M tracked.pyc", "",
    ])
    manager = WorktreeManager(lambda args, cwd: (0, output, ""))
    assert manager.changed_files(tmp_path, hub.policy.ignored_artifact_globs) == [
        "build/out.bin", "outside.pyc", "secrets.env", "tracked.pyc"]


@pytest.fixture
def target(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    assert run_git(["init"], repo)[0] == 0
    (repo / "hello.txt").write_text("hello\n", encoding="utf-8")
    assert run_git(["add", "--", "hello.txt"], repo)[0] == 0
    env = os.environ | {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                        "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
    subprocess.run(["git", "-c", f"safe.directory={repo.as_posix()}", "-c", "core.hooksPath=NUL" if os.name == "nt"
                    else "core.hooksPath=/dev/null", "commit", "--no-gpg-sign", "-m", "fixture"],
                   cwd=repo, env=env, capture_output=True, check=True, timeout=20)
    return repo


@pytest.mark.parametrize("args", [
    ["push"], ["pull"], ["fetch"], ["merge"], ["rebase"], ["reset"],
    ["remote", "add", "origin", "never"], ["branch", "-D", "x"], ["branch", "-d", "x"],
    ["worktree", "remove", "x"], ["worktree", "prune"], ["clean", "-fd"], ["checkout", "x"],
    ["-c", "alias.x=push", "x"], ["worktree", "move", "x", "y"], ["log"],
    ["apply", "--unsafe-paths"], [],
    ["apply", "--check", "--unsafe-paths", "patch.diff"],
])
def test_git_forbidden(tmp_path, monkeypatch, args):
    def forbidden(*args, **kwargs):
        pytest.fail("forbidden command reached subprocess")
    monkeypatch.setattr("worktree_manager.subprocess.run", forbidden)
    with pytest.raises(GitForbidden):
        run_git(args, tmp_path)


def test_worktree_create_and_idempotency(hub, target):
    manager = WorktreeManager()
    path = manager.create(hub.policy, "project", "T-1", target, "HEAD")
    assert path == Path(hub.policy.data_root) / "worktrees" / "project" / "T-1"
    assert run_git(["rev-parse", "--abbrev-ref", "HEAD"], path)[1].strip() == "hub/T-1"
    assert manager.create(hub.policy, "project", "T-1", target, "HEAD") == path
    assert manager.changed_files(path) == []
    (path / "new file.txt").write_text("untracked", encoding="utf-8")
    (path / "hello.txt").write_text("changed\n", encoding="utf-8")
    assert manager.changed_files(path) == ["hello.txt", "new file.txt"]


def test_worktree_collision_and_denied_targets(hub, target):
    manager = WorktreeManager()
    for denied in (hub.root, Path(hub.policy.deny[0])):
        with pytest.raises(PolicyError):
            manager.create(hub.policy, "project", "T-1", denied, "HEAD")
    collision = Path(hub.policy.data_root) / "worktrees" / "project" / "T-1"
    collision.mkdir(parents=True)
    with pytest.raises(PolicyError, match="collides"):
        manager.create(hub.policy, "project", "T-1", target, "HEAD")
    with pytest.raises(PolicyError, match="base ref"):
        manager.create(hub.policy, "project", "T-2", target, "--detach")
    with pytest.raises(PolicyError):
        manager.create(replace(hub.policy, data_root=str(target / "data")), "project", "T-2", target, "HEAD")


PATCH = "diff --git a/hello.txt b/hello.txt\n--- a/hello.txt\n+++ b/hello.txt\n@@ -1 +1 @@\n-hello\n+updated\n"


def test_apply_check_and_scope_before_git(target):
    manager = WorktreeManager()
    calls = []

    def git(args, cwd):
        calls.append(args[:2])
        return run_git(args, cwd)

    manager = WorktreeManager(git)
    with pytest.raises(PolicyError, match="outside scope"):
        manager.apply_patch(target, PATCH, ["other.txt"])
    assert calls == []
    assert manager.apply_patch(target, PATCH, ["hello.txt"]) == ["hello.txt"]
    assert calls == [["apply", "--check"], ["apply", "--"]]
    assert (target / "hello.txt").read_text() == "updated\n"
    with pytest.raises(PolicyError):
        manager.apply_patch(target, PATCH, ["hello.txt"])
    assert not list(target.glob("*.patch"))


@pytest.mark.parametrize("path", ["../escape", ".git/config", "C:/outside", "sub/../../escape"])
def test_patch_rejects_traversal_metadata(target, path):
    patch = f"diff --git a/{path} b/{path}\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+x\n"
    with pytest.raises(PolicyError):
        WorktreeManager().apply_patch(target, patch, ["*"])


def test_rename_scope_checks_both_paths(target):
    patch = "diff --git a/hello.txt b/other.txt\nsimilarity index 100%\nrename from hello.txt\nrename to other.txt\n"
    with pytest.raises(PolicyError, match="outside scope"):
        WorktreeManager().apply_patch(target, patch, ["other.txt"])
    assert WorktreeManager().apply_patch(target, patch, ["hello.txt", "other.txt"]) == ["hello.txt", "other.txt"]
    assert "other.txt" in WorktreeManager().changed_files(target)


def test_commit_requires_record_and_never_pushes(target, hub, monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Fixture")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "fixture@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Fixture")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "fixture@example.invalid")
    calls = []

    def git(args, cwd):
        calls.append(args[0])
        return run_git(args, cwd)

    manager = WorktreeManager(git)
    with pytest.raises(PolicyError):
        manager.commit(target, "no authority", {})
    assert not calls
    # WorktreeManager's caller-verification contract is exercised by Runner.commit tests.
    (target / "hello.txt").write_text("changed\n", encoding="utf-8")
    record = hub.signed("commit", project="project", task="T-1", plan_hash=plan_hash(hub.spec),
                        policy_hash=hub.policy.policy_hash)
    manager.commit(target, "local change", record)
    assert calls == ["add", "commit"]
    assert run_git(["log", "-1", "--format=%s"], target)[1].strip() == "local change"


def test_multiple_plain_diff_sections_checked_before_apply(target):
    calls = []
    manager = WorktreeManager(lambda args, cwd: (calls.append(args) or (0, "", "")))
    appended = "--- /dev/null\n+++ b/outside.txt\n@@ -0,0 +1 @@\n+outside\n"
    with pytest.raises(PolicyError, match="outside scope"):
        manager.apply_patch(target, PATCH + appended, ["hello.txt"])
    assert calls == []


def test_staged_rename_returns_source_and_destination(target):
    (target / "hello.txt").rename(target / "renamed.txt")
    assert run_git(["add", "-A"], target)[0] == 0
    assert WorktreeManager().changed_files(target) == ["hello.txt", "renamed.txt"]


def test_patch_hunk_content_and_quoted_unicode_paths(target):
    manager = WorktreeManager()
    content = "diff --git a/hello.txt b/hello.txt\n--- a/hello.txt\n+++ b/hello.txt\n@@ -1 +1 @@\n-hello\n+++ b/content-only\n"
    assert manager.apply_patch(target, content, ["hello.txt"]) == ["hello.txt"]
    assert (target / "hello.txt").read_text() == "++ b/content-only\n"
    patch = ('diff --git "a/\\303\\251.txt" "b/\\303\\251.txt"\nnew file mode 100644\n'
             '--- /dev/null\n+++ "b/\\303\\251.txt"\n@@ -0,0 +1 @@\n+hello\n')
    assert manager.apply_patch(target, patch, ["é.txt"]) == ["é.txt"]
    assert (target / "é.txt").read_text() == "hello\n"


def test_git_permission_denied_is_reported(tmp_path):
    def denied(args, cwd):
        raise PermissionError("injected")
    with pytest.raises(PolicyError, match="permission denied"):
        WorktreeManager(denied).changed_files(tmp_path)


def test_process_identity_and_foreign_stop(hub):
    runner = Runner(StateStore(hub.root), {}, WorktreeManager(), hub.root)
    foreign = os.getppid()
    created = psutil.Process(foreign).create_time()
    assert is_same_process(foreign, created)
    assert not is_same_process(foreign, created - 10)
    assert not is_same_process(-1, created)
    assert not is_same_process(99999999, created)
    with pytest.raises(PolicyError, match="foreign"):
        runner.stop(foreign, created)
    assert runner.live_runs() == []


@pytest.fixture
def routing(hub):
    catalog = load_catalog(ROOT / "config" / "models.toml")
    availability = {vendor: Availability(True, "fake", True, "") for vendor in catalog}
    return dict(policy=hub.policy, catalog=catalog, availability=availability, quota_blocked=set())


def test_catalog_and_route_validation(routing, tmp_path):
    route = Route("claude", "sonnet", "max")
    assert resolve(route, "coder", **routing) == (route, [])
    for invalid in (replace(route, model="unknown"), replace(route, effort="extreme"), replace(route, vendor="unknown")):
        with pytest.raises(RouteError):
            resolve(invalid, "coder", **routing)
    with pytest.raises(RouteError):
        resolve(route, "unknown", **routing)
    file = tmp_path / "bad.toml"
    for text in ("broken!", '[vendors.codex]\nmodels=["x"]\nefforts=["unknown"]',
                 '[vendors.codex]\nmodels=[]\nefforts=["low"]'):
        file.write_text(text, encoding="utf-8")
        with pytest.raises(RouteError):
            load_catalog(file)


def test_fallback_owner_gate_and_effort_downgrade(routing):
    proposal = Route("claude", "sonnet", "max", 0.5)
    routing["quota_blocked"] = {"claude"}
    with pytest.raises(RouteError, match="needs owner:"):
        resolve(proposal, "coder", **routing)
    policy = routing["policy"]
    roles = {role: {**settings, "auto_fallback": True} for role, settings in policy.routing_roles.items()}
    routing["policy"] = replace(policy, routing_roles=roles)
    route, reasons = resolve(proposal, "coder", **routing)
    assert route == Route("codex", "gpt-6.1-sol", "xhigh", 0.5)
    assert reasons
    routing["quota_blocked"] = {"claude", "codex"}
    with pytest.raises(RouteError, match="no available"):
        resolve(proposal, "coder", **routing)


def test_reviewer_vendor_separation(routing):
    proposal = Route("codex", "gpt-6-luna", "high")
    with pytest.raises(RouteError, match="needs owner:"):
        resolve(proposal, "reviewer", coder_vendor="codex", **routing)
    routing["quota_blocked"] = {"claude"}
    route, reasons = resolve(proposal, "reviewer", coder_vendor="codex", **routing)
    assert route == proposal and reasons == ["SAME-VENDOR review"]
    routing["quota_blocked"] = set()
    policy = routing["policy"]
    roles = {role: {**settings, "auto_fallback": True} for role, settings in policy.routing_roles.items()}
    routing["policy"] = replace(policy, routing_roles=roles)
    route, reasons = resolve(proposal, "reviewer", coder_vendor="codex", **routing)
    assert route.vendor == "claude" and reasons


def test_router_disallowed_vendor_and_missing_availability(routing):
    policy = routing["policy"]
    roles = {**policy.routing_roles, "coder": {**policy.routing_roles["coder"], "allowed_vendors": ["codex"]}}
    with pytest.raises(RouteError, match="not allowed"):
        resolve(Route("claude", "sonnet", "high"), "coder", **{**routing, "policy": replace(policy, routing_roles=roles)})
    with pytest.raises(RouteError, match="no available"):
        resolve(Route("codex", "gpt-6-luna", "high"), "coder", **{**routing, "availability": {}})
