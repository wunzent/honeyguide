from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable

import psutil
import pytest

from adapters.base import Route, get_adapter
from agent_loader import load_template
from policy import PolicyError
from runner import Runner, is_same_process
from state_writer import StateStore
from worktree_manager import WorktreeManager
from test_path_policy import hub
from test_v1_isolation import target


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def runtime(hub, target, monkeypatch):
    from dataclasses import replace
    from adapters.codex_cli import CodexAdapter
    from adapters.claude_cli import ClaudeAdapter
    # Test controls are explicit invocation overrides, never inherited by workers.
    for cls in (CodexAdapter, ClaudeAdapter):
        build = cls.build
        def fake_build(self, *args, _build=build, **kwargs):
            invocation = _build(self, *args, **kwargs)
            env = {key: value for key, value in os.environ.items() if key.startswith('FAKE_')}
            return replace(invocation, env=invocation.env | env)
        monkeypatch.setattr(cls, 'build', fake_build)
    parse = ClaudeAdapter.parse_line
    def fake_parse(self, line):
        event = parse(self, line)
        if event and event.get('type') == 'result' and event.get('is_error') is True:
            event['error'] = {'message': event.get('result', '')}
        return event
    monkeypatch.setattr(ClaudeAdapter, 'parse_line', fake_parse)
    store = StateStore(hub.root)
    store.write_spec("project", "T-1", hub.spec)
    with store.transaction("project", "T-1") as txn:
        txn.state.update(hub.state)
        txn.emit("fixture", {"set": hub.state})
    manager = WorktreeManager()
    worktree = manager.create(hub.policy, "project", "T-1", target, "HEAD")
    adapters = {vendor: get_adapter(vendor, [sys.executable, str(ROOT / "tests" / "fakes" / f"fake_{vendor}.py")])
                for vendor in ("claude", "codex")}
    runner = Runner(store, adapters, manager, hub.root,
                    clock=lambda: datetime(2026, 11, 9, 12, 34, 56, tzinfo=timezone.utc))
    from adapters.base import Availability
    runner.availability_probe = lambda vendor: Availability(True, "codex-cli 0.167.0", True, "")
    yield runner, worktree
    for process in runner._processes.values():
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)


def start(runtime, vendor="codex", key="T-1:coder:1"):
    runner, worktree = runtime
    return runner.start("project", "T-1", "coder", Route(vendor, "sonnet" if vendor == "claude" else "gpt-6.1-sol", "high"),
                        load_template(ROOT / "agents" / "coder.md"), worktree, key,
                        {"approved_plan": "Implement hello.txt only.", "repository_context": "sk-throwaway-secret"})


def finished(runner, run_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        outcome = runner.poll("project", "T-1", run_id)
        if outcome is not None:
            return outcome
        time.sleep(0.01)
    pytest.fail("fake did not finish")


def wait_until(check: Callable[[], Any], timeout_s: float = 10) -> Any:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if result := check():
            return result
        time.sleep(0.01)
    pytest.fail("condition not reached before timeout")


@pytest.fixture
def held_fakes(runtime, tmp_path, monkeypatch) -> Callable[[int], None]:
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    gate = tmp_path / "fake_gate.py"
    gate.write_text(
        "import os, runpy, sys, time\nfrom pathlib import Path\n"
        "script = sys.argv.pop(1)\n"
        "flag = '-o' if '-o' in sys.argv else '--append-system-prompt-file'\n"
        "run_id = Path(sys.argv[sys.argv.index(flag) + 1]).parent.name\n"
        "release = Path(os.environ['FAKE_RELEASE_DIR']) / run_id\n"
        "deadline = time.monotonic() + float(os.environ['FAKE_SLEEP'])\n"
        "while not release.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "os.environ['FAKE_SCENARIO'] = 'ok'\n"
        "runpy.run_path(script, run_name='__main__')\n", encoding="utf-8")
    monkeypatch.setenv("FAKE_SLEEP", "20")
    monkeypatch.setenv("FAKE_RELEASE_DIR", str(release_dir))
    for vendor in ("claude", "codex"):
        runtime[0].adapters[vendor] = get_adapter(
            vendor, [sys.executable, str(gate), str(ROOT / "tests" / "fakes" / f"fake_{vendor}.py")])

    def release(pid: int) -> None:
        for _, _, state in runtime[0]._tasks():
            for run_id, run in state.get('runs', {}).items():
                if run.get('pid') == pid:
                    (release_dir / run_id).touch()
                    return
        pytest.fail('fake process not found in task state')

    return release


def test_intent_durable_before_failed_popen(runtime, monkeypatch):
    runner, _ = runtime

    def fail(*args, **kwargs):
        state = runner.store.read_state("project", "T-1")
        assert state["spawned_keys"]["T-1:coder:1"] == 1
        record = list(state['runs'].values())[0]
        assert record['status'] == 'intent'
        assert re.fullmatch(r'[0-9a-f]{32}', record['run_token'])
        assert kwargs['env']['HUB_RUN_TOKEN'] == record['run_token']
        assert runner.store.read_events('project', 'T-1')[-1].data['run_token'] == record['run_token']
        assert runner.store.read_events("project", "T-1")[-1].kind == "spawn.intent"
        raise PermissionError("injected spawn failure")

    monkeypatch.setattr("runner.subprocess.Popen", fail)
    with pytest.raises(PermissionError):
        start(runtime)
    events = runner.store.read_events("project", "T-1")
    assert all(event.kind != "spawn.started" for event in events)
    with pytest.raises(PolicyError, match="duplicate"):
        start(runtime)
    runner.store.recover("project", "T-1")
    assert list(runner.store.read_state("project", "T-1")["runs"].values())[0]["status"] == "intent"


@pytest.mark.parametrize("dynamic,reason", [(False, "process slots"), (True, "dynamic slots")])
def test_pending_intents_reserve_slots(runtime, monkeypatch, dynamic, reason):
    runner, _ = runtime
    records = {"pending-a": {"idem_key": "other:a", "status": "intent", "dynamic": True}}
    if not dynamic:
        records["pending-b"] = {"idem_key": "other:b", "status": "intent", "dynamic": False}
    with runner.store.transaction("project", "T-1") as txn:
        txn.state["runs"] = records
        txn.emit("reserved", {"set": {"runs": records}})
    with pytest.raises(PolicyError, match=reason):
        runner.start("project", "T-1", "coder", Route("codex", "gpt-6.1-sol", "high"),
                     load_template(ROOT / "agents" / "coder.md"), runtime[1], "new:key",
                     {"approved_plan": "Approved", "repository_context": "Fixture"}, dynamic=dynamic)


def test_process_access_denied_is_not_owned(monkeypatch):
    def denied(pid):
        raise psutil.AccessDenied(pid)
    monkeypatch.setattr("runner.psutil.Process", denied)
    assert not is_same_process(os.getpid(), 1.0)


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("scenario,status", [("ok", "ok"), ("quota_reset", "quota_limited")])
def test_fake_run_finish(runtime, monkeypatch, vendor, scenario, status):
    runner, _ = runtime
    monkeypatch.setenv("FAKE_SCENARIO", scenario)
    run_id = start(runtime, vendor)
    assert re.fullmatch(r"R-20261109123456-[0-9a-f]{4}", run_id)
    outcome = finished(runner, run_id)
    assert outcome.status == status
    assert (outcome.reset_at is not None) == (scenario == "quota_reset")
    directory = runner.store.task_dir("project", "T-1") / "runs" / run_id
    assert (directory / "result.md").read_text() == outcome.result_text
    assert (directory / "meta.md").exists()
    events = runner.store.read_events("project", "T-1")
    assert [event.kind for event in events][-3:] == ["spawn.intent", "spawn.started", "run.finished"]
    assert events[-1].data["status"] == status
    assert runner.live_runs() == []
    assert finished(runner, run_id).status == status
    assert sum(event.kind == "run.finished" for event in runner.store.read_events("project", "T-1")) == 1


def test_scrub_result_and_no_agent_approval(runtime, monkeypatch):
    runner, _ = runtime
    adapter = runner.adapters["codex"]
    classify = adapter.classify

    def with_secret(*args):
        outcome = classify(*args)
        outcome.result_text = "APPROVED sk-throwaway-secret Bearer throwaway"
        return outcome

    monkeypatch.setattr(adapter, "classify", with_secret)
    run_id = start(runtime)
    assert "throwaway" not in finished(runner, run_id).result_text
    state = runner.store.read_state("project", "T-1")
    assert state["status"] == "approved" and len(state["approval_history"]) == 1
    assert state["approval"]["quote"] == "Approved in this conversation"


def test_alive_duplicate_restart_and_owned_stop(runtime, monkeypatch):
    runner, worktree = runtime
    monkeypatch.setenv("FAKE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_SLEEP", "30")
    run_id = start(runtime)
    assert runner.poll("project", "T-1", run_id) is None
    live = runner.live_runs()
    assert len(live) == 1
    restarted = Runner(runner.store, runner.adapters, runner.worktrees, runner.hub_root)
    assert restarted.poll("project", "T-1", run_id) is None
    with pytest.raises(PolicyError, match="duplicate"):
        start((restarted, worktree))
    with pytest.raises(PolicyError, match="foreign"):
        restarted.stop(live[0]["pid"], live[0]["create_time"] - 10)
    restarted.stop(live[0]["pid"], live[0]["create_time"])
    runner._processes["project", "T-1", run_id].wait(timeout=10)
    assert finished(runner, run_id).status == "failed"


def test_unsigned_spawn_is_refused(runtime):
    runner, _ = runtime
    runner.store.write_spec("project", "T-1", "## Proposed Plan\nChanged, unsigned plan\n")
    with pytest.raises(PolicyError, match="approval"):
        start(runtime)
    assert not runner.store.read_state("project", "T-1").get("runs")


@pytest.mark.parametrize("code", [0, 3])
def test_python_tests_record_real_exit(runtime, code):
    runner, worktree = runtime
    result = runner.run_tests("project", "T-1", worktree,
                              [sys.executable, "-c", f"print('sk-throwaway-secret'); raise SystemExit({code})"], 5)
    assert result["passed"] is (code == 0) and result["exit_code"] == code and result["duration"] >= 0
    event = next(e for e in reversed(runner.store.read_events("project", "T-1")) if e.kind == "tests.finished")
    assert event.kind == "tests.finished" and event.data["passed"] == (code == 0)
    log = runner.store.task_dir("project", "T-1") / "runs" / event.data["run"] / "test-log.txt"
    assert "throwaway" not in log.read_text()


def test_tests_timeout_and_executable_guard(runtime):
    runner, worktree = runtime
    with pytest.raises(ValueError):
        runner.run_tests("project", "T-1", worktree, ["untrusted.exe"], 5)
    result = runner.run_tests("project", "T-1", worktree, [sys.executable, "-c", "import time; time.sleep(30)"], 0.05)
    assert not result["passed"] and result["exit_code"] == -1


def test_scope_violation(runtime):
    runner, worktree = runtime
    assert runner.scope_check("project", "T-1", worktree, ["hello.txt"]) == []
    (worktree / "outside.txt").write_text("outside", encoding="utf-8")
    assert runner.scope_check("project", "T-1", worktree, ["hello.txt"]) == ["outside.txt"]
    assert runner.store.read_events("project", "T-1")[-1].kind == "scope.violation"
    assert runner.store.read_state("project", "T-1")["status"] == "needs-you"
    with pytest.raises(PolicyError):
        runner.worktrees.apply_patch(worktree, "diff --git a/outside.txt b/outside.txt\n--- /dev/null\n+++ b/outside.txt\n@@ -0,0 +1 @@\n+x\n", ["hello.txt"])


def test_runner_commit_requires_ready_state(runtime):
    runner, _ = runtime
    with pytest.raises(PolicyError, match="not ready"):
        runner.commit_task("project", "T-1")


# Engine integration uses approved throwaway hubs and the existing offline CLIs.
from datetime import timedelta
import json
import shutil
import weakref

import yaml

from adapters.base import Availability
from engine import Engine, EngineAlreadyRunning, EngineStartupError, main as engine_main
from policy import load_policy
from scheduler import Scheduler
from state_writer import plan_hash, set_approval_block


@pytest.fixture
def engine_env(runtime, hub, target):
    initial, worktree = runtime
    shutil.copyfile(ROOT / "config" / "models.toml", hub.config / "models.toml")
    shutil.copytree(ROOT / "agents", hub.root / "agents")
    config = {"repo": str(target), "base_ref": "HEAD", "allowed_paths": ["hello.txt"],
              "test_command": [sys.executable, "-c", "print('trusted tests pass')"], "test_timeout_s": 5}
    project_path = hub.root / "projects" / "project" / "project.md"
    project_path.write_text("# Project\n\n```hub-project\n" + yaml.safe_dump(config) + "```\n", encoding="utf-8")
    engines, runners = [], [initial]
    now = initial.clock()
    notices = []

    def factory():
        runner = Runner(initial.store, dict(initial.adapters), initial.worktrees, hub.root, lambda: now)
        runners.append(runner)
        scheduler = Scheduler(initial.store, hub.policy, lambda: now, rng=lambda a, b: 0)
        engine = Engine(hub.root, store=initial.store, policy_loader=load_policy,
                        adapters=runner.adapters, runner=runner, worktrees=initial.worktrees, scheduler=scheduler,
                        clock=lambda: now, availability_probe=lambda vendor: Availability(True, "codex-cli 0.167.0", True, ""),
                        notifier=lambda *args: notices.append(args))
        engines.append(weakref.ref(engine))
        return engine

    yield factory, initial.store, now, config, project_path, notices
    for reference in engines:
        if (engine := reference()) is not None:
            engine.close()
    for runner in runners:
        for process in runner._processes.values():
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


def drive(engine, store, now, task="T-1", wanted="ready_to_commit", *,
          condition: Callable[[dict], bool] | None = None, timeout_s: float = 15):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        engine.tick(now)
        state = store.read_state("project", task)
        if condition(state) if condition is not None else state["status"] == wanted:
            return state
        time.sleep(0.02)
    events = [(event.seq, event.kind) for event in store.read_events("project", task)[-12:]]
    pytest.fail(f"engine did not reach {wanted} within {timeout_s}s; state={state}; last events={events}")


def test_engine_restart_twice_reattaches_one_spawn(engine_env, held_fakes):
    factory, store, now, *_ = engine_env
    engine = factory()
    engine.tick(now)
    live = wait_until(engine.runner.live_runs)
    assert len(live) == 1
    for _ in range(2):
        del engine  # Release the engine lease without signalling the agent.
        engine = factory()
        attached = wait_until(engine.runner.live_runs)
        assert attached[0]["pid"] == live[0]["pid"]
        assert attached[0]["create_time"] == live[0]["create_time"]
        engine.tick(now)
        starts = [e for e in store.read_events("project", "T-1") if e.kind == "spawn.started"]
        assert len(starts) == 1
    held_fakes(live[0]["pid"])
    wait_until(lambda: not engine.runner.live_runs())
    state = drive(engine, store, now, wanted="reviewing")
    coder_runs = [r for r in state["runs"].values() if r.get("role") == "coder"]
    assert len(coder_runs) == 1 and coder_runs[0]["status"] == "ok"


def test_singleton_and_plain_policy_startup(engine_env, hub):
    factory, store, now, *_ = engine_env
    engine = factory()
    with pytest.raises(EngineAlreadyRunning):
        factory()
    engine.close()
    (hub.root / "worker.py").write_text("edited", encoding="utf-8")
    engine = factory()
    engine.close()
    (hub.config / "policy.toml").write_text("[invalid", encoding="utf-8")
    with pytest.raises(EngineStartupError, match="policy"):
        factory()


@pytest.mark.parametrize("key", ["T-1:coder:1", "T-1:coder:1:q1"])
def test_abandoned_intent_only_one_respawn(engine_env, monkeypatch, key):
    factory, store, now, *_ = engine_env
    engine = factory()
    monkeypatch.setattr('runner.psutil.process_iter', lambda: iter(()))
    engine._update("project", "T-1", "fixture.retry", {"retry_key": key})

    popen = __import__('subprocess').Popen
    def denied(argv, *args, **kwargs):
        if argv[0] == sys.executable:
            raise PermissionError("fake launch denial")
        return popen(argv, *args, **kwargs)

    monkeypatch.setattr("runner.subprocess.Popen", denied)
    engine.tick(now)
    for _ in range(3):
        state = store.read_state("project", "T-1")
        runs = state["runs"]
        for run in runs.values():
            if run["status"] == "intent":
                run["intent_at"] = (now - timedelta(seconds=61)).isoformat()
        engine._update("project", "T-1", "fixture.age", {"runs": runs})
        engine.close()
        engine = factory()
        engine.tick(now)
    state = store.read_state("project", "T-1")
    assert state['spawned_keys'][key] == 2
    assert state['status'] == "needs-you"
    assert len(state['runs']) == 2
    assert sum(e.kind == "spawn.abandoned" for e in store.read_events("project", "T-1")) == 2


def test_full_happy_path_and_agent_approval_has_no_authority(engine_env, monkeypatch):
    factory, store, now, *_ = engine_env
    engine = factory()
    claude = engine.adapters["claude"]
    original = claude.classify

    def review(*args):
        outcome = original(*args)
        outcome.result_text = 'APPROVED\nRESULT: {"verdict": "PASS"}'
        return outcome

    monkeypatch.setattr(claude, "classify", review)
    state = drive(engine, store, now)
    assert state['status'] == "ready_to_commit"
    assert state["approval"]["quote"] == "Approved in this conversation"
    assert len(state["approval_history"]) == 1
    runs = list(state['runs'].values())
    assert [(r['role'], r['route']['vendor']) for r in runs if r.get('role')] == [('coder', 'codex'), ('reviewer', 'claude')]
    assert any(r.get('kind') == 'tests' and r['passed'] for r in runs)
    spec = store.read_spec("project", "T-1")
    assert "APPROVED" not in spec


def test_unsigned_task_cannot_spawn_even_with_approved_text(engine_env):
    factory, store, now, *_ = engine_env
    engine = factory()
    store.write_spec("project", "T-1", "## Proposed Plan\nAPPROVED\n")
    engine.tick(now)
    state = store.read_state("project", "T-1")
    assert state['status'] == 'needs-you' and not state.get('runs')


def test_concurrency_four_tasks_two_dynamic(engine_env, hub, monkeypatch, held_fakes):
    factory, store, now, *_ = engine_env
    for number in range(1, 7):
        task = f"T-{number}"
        record = hub.record("approve-plan", project="project", task=task,
                            plan_hash=plan_hash(hub.spec), policy_hash=hub.policy.policy_hash)
        store.write_spec("project", task, set_approval_block(hub.spec, record))
        state = {**hub.state, "task": task, "dynamic": number > 4, "approval": record, "approval_history": [record]}
        with store.transaction("project", task) as txn:
            txn.state.update(state)
            txn.emit("fixture", {"set": state})
    engine = factory()
    original_start = engine.runner.start
    counts = []
    def sample_start(*args, **kwargs):
        run_id = original_start(*args, **kwargs)
        live = engine.runner.live_runs()
        counts.append((len(live), sum(r['dynamic'] for r in live)))
        return run_id
    monkeypatch.setattr(engine.runner, 'start', sample_start)
    seen = set()

    def sample_tick() -> bool:
        engine.tick(now)
        live = engine.runner.live_runs()
        assert len(live) <= 2
        assert sum(r['dynamic'] for r in live) <= 1
        for run in live:
            held_fakes(run['pid'])
        seen.update(task for _, task, state in engine._tasks()
                    if any(r.get('role') == 'coder' for r in state.get('runs', {}).values()))
        # The stock fake has no review verdict. Park completed coding tasks so
        # this test samples the six requested coder dispatches alone.
        for project, task, state in engine._tasks():
            if state['status'] == 'reviewing':
                engine._update(project, task, 'fixture.park', {'needs_run': False})
        return len(seen) == 6

    wait_until(sample_tick, timeout_s=45)
    assert len(counts) == 6 and all(total <= 2 and dynamic <= 1 for total, dynamic in counts)


@pytest.mark.parametrize("scenario", ["quota_reset", "quota_noreset"])
def test_engine_quota_wait_and_resume_checks(engine_env, monkeypatch, scenario):
    factory, store, now, *_ = engine_env
    monkeypatch.setenv("FAKE_SCENARIO", scenario)
    engine = factory()
    state = drive(engine, store, now, wanted='waiting-quota')
    assert engine.runner.live_runs() == []
    item = engine.scheduler.due(now + timedelta(days=10000))[0]
    if scenario == 'quota_reset':
        assert item.due_at == datetime.fromtimestamp(1900000000, timezone.utc) + timedelta(minutes=2)
        assert 'codex-stream' in item.reason
    checkpoint = state['checkpoint']
    assert checkpoint['session_id'] == 'codex-thread' and checkpoint['round'] == 1
    store.write_spec('project', 'T-1', '## Proposed Plan\nChanged after scheduling\n')
    engine.tick(item.due_at)
    assert store.read_state('project', 'T-1')['status'] == 'needs-you'
    assert len([e for e in store.read_events('project', 'T-1') if e.kind == 'spawn.started']) == 1


def test_resume_uses_vendor_session_and_attempt_key(engine_env, monkeypatch, tmp_path):
    factory, store, now, *_ = engine_env
    monkeypatch.setenv('FAKE_SCENARIO', 'quota_reset')
    engine = factory()
    state = drive(engine, store, now, wanted='waiting-quota')
    item = engine.scheduler.due(now + timedelta(days=10000))[0]
    log = tmp_path / 'resume-argv.json'
    monkeypatch.setenv('FAKE_ARGV_LOG', str(log))
    monkeypatch.setenv('FAKE_SCENARIO', 'ok')
    engine.tick(item.due_at)
    wait_until(lambda: log.exists() and log.stat().st_size)
    args = json.loads(log.read_text())
    assert args[:3] == ['exec', 'resume', 'codex-thread']
    state = drive(engine, store, now, wanted='reviewing')
    assert state['spawned_keys'] == {'T-1:coder:1': 1, 'T-1:coder:1:q1': 1}


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("invalid", ["", "bad id"])
def test_invalid_checkpoint_resume_never_starts_fresh(engine_env, monkeypatch, vendor, invalid):
    factory, store, now, *_ = engine_env
    engine = factory()
    route = {"vendor": vendor, "model": "sonnet" if vendor == "claude" else "gpt-6.1-sol", "effort": "low"}
    engine._update("project", "T-1", "fixture.resume", {
        "status": "waiting-quota", "resume_ready": True,
        "checkpoint": {"session_id": invalid, "role": "coder", "route": route,
                       "resume_key": "T-1:coder:1:q1"}})
    popen = subprocess.Popen

    def refuse_worker(argv, *args, **kwargs):
        if argv[0] == sys.executable:
            pytest.fail("invalid checkpoint launched a worker")
        return popen(argv, *args, **kwargs)

    monkeypatch.setattr("runner.subprocess.Popen", refuse_worker)
    engine.tick(now)
    state = store.read_state("project", "T-1")
    assert state["status"] == "needs-you" and not state.get("runs")
    events = store.read_events("project", "T-1")
    assert sum(e.kind == "session.resume_refused" for e in events) == 1
    assert not any(e.kind.startswith("spawn.") for e in events)


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_checkpoint_vendor_change_requires_owner_without_spawn(engine_env, monkeypatch, vendor):
    factory, store, now, *_ = engine_env
    engine = factory()
    original = "codex" if vendor == "claude" else "claude"
    checkpoint = {"session_id": "previous-session", "role": "coder", "run": "fixture-run",
                  "route": {"vendor": original, "model": "sonnet" if original == "claude" else "gpt-6.1-sol",
                            "effort": "low"}, "resume_key": "T-1:coder:1:q1"}
    engine._update("project", "T-1", "fixture.resume", {
        "status": "waiting-quota", "resume_ready": True, "checkpoint": checkpoint,
        "route_proposals": {"coder": {"vendor": vendor,
            "model": "sonnet" if vendor == "claude" else "gpt-6.1-sol", "effort": "low"}}})
    monkeypatch.setattr(engine.runner, "start", lambda *args, **kwargs: pytest.fail("changed vendor spawned"))
    engine.tick(now)
    engine.tick(now)
    state = store.read_state("project", "T-1")
    assert state["status"] == "needs-you" and state["needs_run"] is False and not state.get("runs")
    assert state["checkpoint"] == checkpoint
    question = state["questions"][-1]
    assert question["title"] == "Resume cannot keep the original vendor/model — approve a fresh session?"
    assert question["class"] == "owner-decision" and question["blocking"]
    assert len(question["options"]) == 2 and question["default"] == "none"
    assert (store.task_dir("project", "T-1") / "questions.md").exists()
    events = store.read_events("project", "T-1")
    assert sum(e.kind == "session.resume_refused" for e in events) == 1
    assert not any(e.kind.startswith("spawn.") for e in events)


def test_question_draft_class_and_atomic_mirror(engine_env, monkeypatch):
    factory, store, now, _, _, notices = engine_env
    monkeypatch.setenv('FAKE_SCENARIO', 'ask')
    engine = factory()
    state = drive(engine, store, now, wanted='needs-you')
    q = state['questions'][0]
    assert q['status'] == 'draft' and q['class'] == 'owner-decision'
    assert q['draft_text'] and notices
    text = (store.task_dir('project', 'T-1') / 'questions.md').read_text(encoding='utf-8')
    block = re.search(r'```hub-questions\n(.*?)```', text, re.S)[1]
    assert yaml.safe_load(block) == state['questions']
    assert f"## {q['id']}:" in text
    engine.close()
    factory()  # Recovery also repairs the mirror from durable state.


@pytest.mark.parametrize('scenario', ['auth', 'fail'])
def test_agent_failures_block(engine_env, monkeypatch, scenario):
    factory, store, now, *_ = engine_env
    monkeypatch.setenv('FAKE_SCENARIO', scenario)
    engine = factory()
    state = drive(engine, store, now, wanted='needs-you')
    assert not engine.runner.live_runs() and state['status'] == 'needs-you'


def test_failed_python_tests_cap_three_rounds(engine_env):
    factory, store, now, config, path, _ = engine_env
    config['test_command'] = [sys.executable, '-c', 'raise SystemExit(2)']
    path.write_text('```hub-project\n' + yaml.safe_dump(config) + '```\n', encoding='utf-8')
    engine = factory()
    state = drive(engine, store, now, wanted='needs-you')
    assert len([r for r in state['runs'].values() if r.get('role') == 'coder']) == 3
    assert len([r for r in state['runs'].values() if r.get('kind') == 'tests']) == 3


def test_engine_cli_once_and_run_forever(engine_env, hub, monkeypatch):
    factory, store, now, *_ = engine_env
    # No tasks ready means --once cannot probe or call an agent.
    with store.transaction('project', 'T-1') as txn:
        txn.state['status'] = 'draft'
        txn.emit('fixture', {'set': {'status': 'draft'}})
    assert engine_main(['--hub-root', str(hub.root), '--once']) == 0
    engine = factory()
    with pytest.raises(ValueError):
        engine.run_forever(0)
    calls = []
    monkeypatch.setattr(engine, 'tick', lambda now: calls.append(now))
    def stop(interval):
        assert interval == 30
        raise KeyboardInterrupt
    monkeypatch.setattr('engine.time.sleep', stop)
    with pytest.raises(KeyboardInterrupt):
        engine.run_forever()
    assert calls == [now]


@pytest.mark.parametrize('session', [None, 'recoverable-session'])
def test_gone_pid_without_output_is_lost(engine_env, runtime, session):
    factory, store, now, *_ = engine_env
    run_id = 'R-20261109123456-aaaa'
    run = {'status': 'running', 'pid': 99999999, 'create_time': 1.0,
           'role': 'coder', 'idem_key': 'T-1:coder:1', 'session_id': session,
           'route': {'vendor': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'high'},
           'worktree': str(runtime[1])}
    with store.transaction('project', 'T-1') as txn:
        updates = {'status': 'coding', 'runs': {run_id: run}, 'spawned_keys': {'T-1:coder:1': 1}}
        txn.state.update(updates)
        txn.emit('fixture.dead', {'set': updates})
    engine = factory()
    state = store.read_state('project', 'T-1')
    assert state['runs'][run_id]['status'] == 'lost'
    assert state['status'] == ('waiting-quota' if session else 'needs-you')
    assert bool(engine.scheduler.due(now)) == bool(session)
    assert not engine.runner.live_runs()
    assert any(e.kind == 'run.lost' for e in store.read_events('project', 'T-1'))


def test_claude_patch_and_scope_rejection(engine_env, runtime, monkeypatch):
    factory, store, now, *_ = engine_env
    with store.transaction('project', 'T-1') as txn:
        route = {'vendor': 'claude', 'model': 'sonnet', 'effort': 'high'}
        txn.state['route'] = route
        txn.emit('fixture.route', {'set': {'route': route}})
    engine = factory()
    adapter = engine.adapters['claude']
    classify = adapter.classify
    def patch(*args):
        result = classify(*args)
        result.result_text = ('```diff\ndiff --git a/hello.txt b/hello.txt\n--- a/hello.txt\n'
                              '+++ b/hello.txt\n@@ -1 +1 @@\n-hello\n+updated\n```\nRESULT: {}')
        return result
    monkeypatch.setattr(adapter, 'classify', patch)
    drive(engine, store, now, wanted='reviewing')
    assert (runtime[1] / 'hello.txt').read_text() == 'updated\n'
    assert any(e.kind == 'tests.finished' and e.data['passed'] for e in store.read_events('project', 'T-1'))


def test_scope_breach_blocks_tests(engine_env, runtime):
    factory, store, now, *_ = engine_env
    (runtime[1] / 'outside.txt').write_text('scope breach', encoding='utf-8')
    engine = factory()
    state = drive(engine, store, now, wanted='needs-you')
    assert not any(run.get('kind') == 'tests' for run in state['runs'].values())
    assert any(e.kind == 'scope.violation' for e in store.read_events('project', 'T-1'))


def test_review_has_only_one_fix_cycle(engine_env, monkeypatch):
    factory, store, now, *_ = engine_env
    monkeypatch.setenv('FAKE_SCENARIO', 'ok')
    monkeypatch.delenv('FAKE_SLEEP', raising=False)
    engine = factory()
    adapter = engine.adapters['claude']
    classify = adapter.classify
    def fail_review(*args):
        result = classify(*args)
        result.result_text = 'RESULT: {"verdict": "FAIL", "issues": ["Missing behavior"]}'
        return result
    monkeypatch.setattr(adapter, 'classify', fail_review)

    def stop_fake(process: subprocess.Popen) -> None:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    with ExitStack() as cleanup:
        cleanup.callback(engine.close)
        processes: dict[str, subprocess.Popen] = {}
        original_start = engine.runner.start

        def track_start(*args, **kwargs):
            try:
                return original_start(*args, **kwargs)
            finally:
                for (_, _, run_id), process in engine.runner._processes.items():
                    if run_id not in processes:
                        processes[run_id] = process
                        cleanup.callback(stop_fake, process)

        monkeypatch.setattr(engine.runner, 'start', track_start)
        # Four dispatches plus durable writes can exceed one 15s Windows budget.
        # Wait for each handled result, with its own deadline and event diagnostics.
        for round_no in (1, 2):
            for role in ('coder', 'reviewer'):
                key = f'T-1:{role}:{round_no}'
                state = drive(
                    engine, store, now, wanted=f'{key} handled', timeout_s=60,
                    condition=lambda state: any(
                        run.get('idem_key') == key and run.get('handled')
                        for run in state.get('runs', {}).values()))
                run = next(run for run in state['runs'].values() if run.get('idem_key') == key)
                assert run['status'] == 'ok'
                assert processes[run['run']].wait(timeout=10) == 0

        assert state['status'] == 'needs-you'
        assert state['review_fix_cycles'] == 1
        assert [r['route']['vendor'] for r in state['runs'].values() if r.get('role') == 'reviewer'] == ['claude', 'claude']
        assert [r['route']['vendor'] for r in state['runs'].values() if r.get('role') == 'coder'] == ['codex', 'codex']
        events = store.read_events('project', 'T-1')
        assert sum(event.kind == 'round.next' for event in events) == 1
        assert sum(event.kind == 'review.exhausted' for event in events) == 1
        assert sum(event.kind == 'run.finished' for event in events) == 4
        assert not engine.runner.live_runs()


def test_quota_fallback_is_signed_and_bounded(engine_env, hub, monkeypatch):
    factory, store, now, *_ = engine_env
    path = hub.config / 'policy.toml'
    path.write_text(path.read_text().replace('auto_fallback = false', 'auto_fallback = true'), encoding='utf-8')
    hub.policy = load_policy(hub.root)
    approval = hub.record('approve-plan', project='project', task='T-1',
                          plan_hash=plan_hash(hub.spec), policy_hash=hub.policy.policy_hash)
    store.write_spec('project', 'T-1', set_approval_block(hub.spec, approval))
    with store.transaction('project', 'T-1') as txn:
        updates = {'approval': approval, 'approval_history': [approval]}
        txn.state.update(updates)
        txn.emit('fixture.approval', {'set': updates})
    monkeypatch.setenv('FAKE_SCENARIO', 'quota_noreset')
    engine = factory()
    state = drive(engine, store, now, wanted='waiting-quota')
    starts = [e for e in store.read_events('project', 'T-1') if e.kind == 'spawn.started']
    assert len(starts) == 2
    assert [r['route']['vendor'] for r in state['runs'].values()] == ['codex', 'claude']
    assert any(e.kind == 'route.fallback' for e in store.read_events('project', 'T-1'))
    assert not engine.runner.live_runs()


def test_codex_sessions_fallback_is_injectable_in_engine(engine_env, monkeypatch):
    factory, store, now, *_ = engine_env
    monkeypatch.setenv('FAKE_SCENARIO', 'quota_noreset')
    engine = factory()
    engine.scheduler.sessions_reader = lambda: {'primary': {'used_percent': 100, 'resets_at': now.timestamp()}}
    drive(engine, store, now, wanted='waiting-quota')
    item = engine.scheduler.due(now + timedelta(minutes=2))[0]
    assert 'codex-sessions' in item.reason
    assert item.due_at == now + timedelta(minutes=2)


def test_elapsed_team_cap_uses_clock_and_survives_restart(engine_env, held_fakes):
    factory, store, now, *_ = engine_env
    engine = factory()
    engine.tick(now)
    state = store.read_state('project', 'T-1')
    assert state['first_dispatch_at'] == now.isoformat()
    engine.close()
    engine = factory()
    engine.clock = lambda: now + timedelta(minutes=61)
    engine.tick(now + timedelta(minutes=61))
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'needs-you'
    assert state.get('team_active_seconds', 0) == 0
    assert sum(e.kind == 'spawn.started' for e in store.read_events('project', 'T-1')) == 1


def test_completed_review_after_team_deadline_needs_owner(engine_env):
    from adapters.base import Outcome
    factory, store, now, *_ = engine_env
    engine = factory()
    run_id = 'R-20261109123456-abcd'
    run = {'role': 'reviewer', 'status': 'ok', 'route': {'vendor': 'claude'}}
    engine._update('project', 'T-1', 'fixture', {'status': 'reviewing', 'runs': {run_id: run},
        'team_active_seconds': 61 * 60})
    engine._handle('project', 'T-1', run_id, Outcome('ok', None, None, None, 'RESULT: {"verdict":"PASS"}', {}))
    assert store.read_state('project', 'T-1')['status'] == 'needs-you'


@pytest.mark.parametrize('kind', ['agent', 'tests'])
def test_child_environment_allowlist(runtime, monkeypatch, tmp_path, kind):
    from dataclasses import replace
    runner, worktree = runtime
    monkeypatch.setenv('HUB_SECRET_SENTINEL', 'must-not-escape')
    script = "import os; assert 'HUB_SECRET_SENTINEL' not in os.environ; assert os.environ['HUB_WORKER'] == '1'"
    if kind == 'tests':
        assert runner.run_tests('project', 'T-1', worktree, [sys.executable, '-c', script], 5)['passed']
    else:
        adapter = runner.adapters['codex']
        build = adapter.build
        script += "; assert os.environ['EXPLICIT_OVERRIDE'] == 'yes'; print('{\"type\":\"turn.completed\"}')"
        monkeypatch.setattr(adapter, 'build', lambda *a, **k: replace(build(*a, **k),
            argv=[sys.executable, '-c', script], stdin_text=None, env={'EXPLICIT_OVERRIDE': 'yes', 'CODEX_HOME': os.environ['CODEX_HOME']}))
        assert finished(runner, start(runtime)).status == 'ok'


def test_pid_file_written_before_started_event(runtime, monkeypatch):
    runner, _ = runtime
    event = runner._event
    def check(project, task, kind, data, run_id, changes):
        if kind == 'spawn.started':
            directory = runner._directory(project, task, run_id)
            import json
            assert int((directory / 'pid').read_text()) == data['pid']
            identity = json.loads((directory / 'pid.json').read_text())
            assert all(identity[k] == data[k] for k in ('pid', 'create_time', 'run_token', 'exe'))
            assert identity['run_token'] == psutil.Process(data['pid']).environ()['HUB_RUN_TOKEN']
        return event(project, task, kind, data, run_id, changes)
    monkeypatch.setattr(runner, '_event', check)
    finished(runner, start(runtime))


@pytest.mark.parametrize('case', ['editor', 'valid', 'token-mismatch', 'unreadable', 'pid-reused', 'wrong-vendor', 'candidate'])
def test_orphan_requires_recorded_identity(engine_env, runtime, tmp_path, monkeypatch, case):
    import json
    from types import SimpleNamespace
    factory, store, now, *_ = engine_env
    engine = factory()
    run_id = 'R-20261109123456-abcd'
    directory = store.task_dir('project', 'T-1') / 'runs' / run_id
    directory.mkdir(parents=True)
    token = 'a' * 32
    run = {'status': 'intent', 'role': 'coder', 'idem_key': 'T-1:coder:1',
           'intent_at': (now - timedelta(seconds=61)).isoformat(), 'worktree': str(runtime[1]),
           'run_token': token, 'route': {'vendor': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'high'}}
    def environ():
        if case == 'unreadable':
            raise psutil.AccessDenied(123)
        return {} if case == 'editor' else {'HUB_RUN_TOKEN': 'wrong' if case == 'token-mismatch' else token}
    command = list(engine.adapters['codex'].executable) + ['exec']
    if case in {'editor', 'wrong-vendor'}:
        command = [sys.executable, 'editor.py', str(directory)]
    candidate = SimpleNamespace(pid=123, cmdline=lambda: command, cwd=lambda: str(runtime[1]),
        is_running=lambda: True, status=lambda: psutil.STATUS_RUNNING, environ=environ,
        create_time=lambda: now.timestamp() + (5 if case == 'pid-reused' else 0), exe=lambda: sys.executable)
    if case not in {'editor', 'candidate'}:
        (directory / 'pid.json').write_text(json.dumps({'pid': 123, 'create_time': now.timestamp(),
            'run_token': token, 'exe': sys.executable}), encoding='utf-8')
    monkeypatch.setattr('runner.psutil.process_iter', lambda: iter([candidate]))
    engine._update('project', 'T-1', 'fixture', {'status': 'coding', 'runs': {run_id: run},
        'spawned_keys': {'T-1:coder:1': 1}})
    engine.reconcile()
    state = store.read_state('project', 'T-1')
    if case in {'valid', 'candidate'}:
        assert state['runs'][run_id]['status'] == 'running'
        assert state['runs'][run_id]['pid'] == 123
        assert any(e.kind == 'spawn.adopted' for e in store.read_events('project', 'T-1'))
        assert json.loads((directory / 'pid.json').read_text())['run_token'] == token
    else:
        assert state['status'] == 'needs-you' and state['needs_run'] is False
        assert state['runs'][run_id]['status'] == 'inspection-failed'
    assert len(state['runs']) == 1
    assert not any(e.kind == 'spawn.started' for e in store.read_events('project', 'T-1'))


def test_orphan_inspection_failure_blocks_retry(engine_env, runtime, monkeypatch):
    factory, store, now, *_ = engine_env
    engine = factory()
    run_id = 'R-20261109123456-abcd'
    run = {'status': 'intent', 'role': 'coder', 'idem_key': 'T-1:coder:1',
           'intent_at': (now - timedelta(seconds=61)).isoformat(), 'worktree': str(runtime[1])}
    engine._update('project', 'T-1', 'fixture', {'status': 'coding', 'runs': {run_id: run},
        'spawned_keys': {'T-1:coder:1': 1}})
    def denied(*a, **k):
        raise psutil.AccessDenied(123)
    monkeypatch.setattr('runner.psutil.process_iter', denied)
    engine.reconcile()
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'needs-you' and state.get('needs_run') is False
    assert state['runs'][run_id]['status'] == 'inspection-failed'


def test_abandoned_intent_is_checked_again_at_dispatch(runtime, monkeypatch, tmp_path):
    import subprocess
    runner, worktree = runtime
    run_id, directory = runner._new_run('project', 'T-1')
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', str(directory)], cwd=worktree)
    try:
        monkeypatch.setattr('runner.psutil.process_iter', lambda: iter([psutil.Process(process.pid)]))
        run = {'role': 'coder', 'status': 'abandoned', 'idem_key': 'T-1:coder:1', 'worktree': str(worktree),
               'route': {'vendor': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'high'}}
        with runner.store.transaction('project', 'T-1') as txn:
            updates = {'runs': {run_id: run}, 'spawned_keys': {'T-1:coder:1': 1}}
            txn.state.update(updates)
            txn.emit('fixture', {'set': updates})
        with pytest.raises(PolicyError):
            start(runtime)
        state = runner.store.read_state('project', 'T-1')
        assert len(state['runs']) == 1 and state['runs'][run_id]['status'] == 'abandoned'
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_active_time_accumulates_across_runs_and_restart(engine_env, runtime, held_fakes):
    factory, store, now, *_ = engine_env
    engine = factory()
    first = start((engine.runner, runtime[1]))
    engine.runner.clock = lambda: now + timedelta(seconds=1900)
    pid = store.read_state('project', 'T-1')['runs'][first]['pid']
    held_fakes(pid)
    finished(engine.runner, first)
    assert store.read_state('project', 'T-1')['team_active_seconds'] == 1900
    # Repeated polls and event replay must not add the same interval twice.
    finished(engine.runner, first)
    store.recover('project', 'T-1')
    assert store.read_state('project', 'T-1')['team_active_seconds'] == 1900
    engine.close()
    engine = factory()
    engine.runner.clock = lambda: now + timedelta(seconds=1900)
    second = start((engine.runner, runtime[1]), key='T-1:coder:2')
    engine.runner.clock = engine.clock = lambda: now + timedelta(seconds=3800)
    held_fakes(store.read_state('project', 'T-1')['runs'][second]['pid'])
    finished(engine.runner, second)
    assert store.read_state('project', 'T-1')['team_active_seconds'] == 3800
    engine.tick(engine.clock())
    assert store.read_state('project', 'T-1')['status'] == 'needs-you'


def test_long_quota_wait_does_not_use_active_budget(engine_env, monkeypatch):
    factory, store, now, *_ = engine_env
    engine = factory()
    monkeypatch.setenv('FAKE_SCENARIO', 'quota_noreset')
    waiting = drive(engine, store, now, wanted='waiting-quota')
    used = waiting['team_active_seconds']
    engine.close()
    engine = factory()
    later = now + timedelta(hours=10)
    engine.clock = engine.runner.clock = lambda: later
    monkeypatch.setenv('FAKE_SCENARIO', 'ok')
    engine.tick(later)
    resumed = store.read_state('project', 'T-1')
    assert resumed['status'] == 'coding'
    assert resumed['team_active_seconds'] == used
    assert len(resumed['runs']) == 2


def test_two_coder_rounds_ignore_only_python_test_artifacts(runtime):
    runner, worktree = runtime
    (worktree / '.gitignore').write_text('__pycache__/\n.pytest_cache/\n*.pyc\n', encoding='utf-8')
    (worktree / 'test_sample.py').write_text('def test_ok():\n    assert 2 + 2 == 4\n', encoding='utf-8')
    for round_no in (1, 2):
        run = start(runtime, key=f'T-1:coder:{round_no}')
        assert finished(runner, run).status == 'ok'
        assert runner.run_tests('project', 'T-1', worktree,
            [sys.executable, '-m', 'pytest', '-q'], 30)['passed']
        assert list((worktree / '__pycache__').glob('*.pyc'))
        assert (worktree / '.pytest_cache').exists()
        assert runner.scope_check('project', 'T-1', worktree,
            ['hello.txt', 'test_sample.py', '.gitignore']) == []
    assert runner.store.read_state('project', 'T-1')['status'] != 'needs-you'


@pytest.mark.parametrize('path,ignore', [
    ('secrets.env', 'secrets.env'), ('build/out.bin', 'build/'),
    ('outside.pyc', '__pycache__/'), ('outside.pyc', '*.pyc')])
def test_artifact_allowlist_does_not_hide_other_changes(runtime, path, ignore):
    runner, worktree = runtime
    (worktree / '.gitignore').write_text(ignore + '\n', encoding='utf-8')
    file = worktree / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('coder write', encoding='utf-8')
    if ignore == '*.pyc':
        # A tracked artifact still has to be inside the approved scope.
        import subprocess
        subprocess.run(['git', '-c', f'safe.directory={worktree.as_posix()}', 'add', '-f', '--', path],
                       cwd=worktree, check=True, capture_output=True, timeout=10)
        file.write_text('modified tracked artifact', encoding='utf-8')
    violations = runner.scope_check('project', 'T-1', worktree, ['hello.txt', '.gitignore'])
    assert violations == [path]
    assert runner.store.read_state('project', 'T-1')['status'] == 'needs-you'
