from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import Counter
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

from adapters.base import Outcome
from scheduler import Item, NeedsOwner, Scheduler, main
from state_writer import StateStore
from test_path_policy import hub


NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def schedule(hub):
    return Scheduler(StateStore(hub.root), hub.policy, lambda: NOW, rng=lambda a, b: 0)


def quota(reset=None):
    return Outcome("quota_limited", "session", reset, "codex-stream" if reset else None, "", {})


def test_verified_reset_and_idempotent_table(schedule):
    item = schedule.plan_quota_retry(quota(NOW), "project", "T-1", {}, "codex")
    assert isinstance(item, Item)
    assert item.due_at == NOW + timedelta(minutes=2)
    assert "reset_source=codex-stream" in item.reason
    assert schedule.plan_quota_retry(quota(NOW + timedelta(hours=1)), "project", "T-1", {}, "codex") == item
    assert schedule.due(NOW) == []
    assert schedule.due(item.due_at) == [item]
    schedule.mark(item.id, "cancelled")
    assert schedule.due(item.due_at) == []
    schedule.mark(item.id, "pending")
    assert len(schedule.due(item.due_at)) == 1
    schedule.mark(item.id, "done")
    schedule.add("resume", "project", "T-1", NOW, "pipe | newline\nslashes \\", 1, 5)
    assert schedule.due(NOW)[0].reason == "pipe | newline\nslashes \\"


def test_bounded_backoff_and_episode_limit(schedule):
    for attempt, minutes in enumerate([15, 30, 60, 120, 240]):
        state = {"quota": {"attempt": attempt, "day": NOW.date().isoformat(), "episodes_today": 1}}
        item = schedule.plan_quota_retry(quota(), "project", "T-1", state, "claude")
        assert item.due_at == NOW + timedelta(minutes=minutes)
        assert "reset_source=backoff" in item.reason
    assert isinstance(schedule.plan_quota_retry(quota(), "project", "T-1", {"quota": {"attempt": 5}}, "claude"), NeedsOwner)
    state = {"quota": {"day": NOW.date().isoformat(), "episodes_today": 3}}
    assert isinstance(schedule.plan_quota_retry(quota(NOW), "project", "T-2", state, "codex"), NeedsOwner)
    state['quota']['day'] = "2026-11-08"
    assert isinstance(schedule.plan_quota_retry(quota(), "project", "T-2", state, "claude"), Item)


def test_last_daily_episode_can_finish_but_cannot_start_another(schedule):
    counters = {'day': NOW.date().isoformat(), 'episodes_today': 3, 'active': True, 'attempt': 4}
    item = schedule.plan_quota_retry(quota(), 'project', 'T-1', {'quota': counters}, 'claude')
    assert isinstance(item, Item) and item.attempt == 4
    counters.update(active=False, attempt=0)
    assert isinstance(schedule.plan_quota_retry(quota(), 'project', 'T-2', {'quota': counters}, 'claude'), NeedsOwner)


def test_backoff_length_also_bounds_attempts(schedule):
    schedule.policy = replace(schedule.policy, backoff_minutes=[15])
    result = schedule.plan_quota_retry(quota(), 'project', 'T-1', {'quota': {'attempt': 1}}, 'claude')
    assert isinstance(result, NeedsOwner)


def test_sessions_only_saturated_windows_and_stream_priority(schedule):
    reader = lambda: {"primary": {"used_percent": 99, "resets_at": NOW.timestamp()},
                      "secondary": {"used_percent": 100, "resets_at": (NOW + timedelta(hours=1)).timestamp()}}
    item = schedule.plan_quota_retry(quota(), "project", "T-1", {}, "codex", reader)
    assert item.due_at == NOW + timedelta(hours=1, minutes=2)
    assert "reset_source=codex-sessions" in item.reason
    item = schedule.plan_quota_retry(quota(NOW), "project", "T-2", {}, "claude", lambda: pytest.fail("stream wins"))
    assert "reset_source=claude-stream" in item.reason
    item = schedule.plan_quota_retry(quota(), "project", "T-3", {}, "codex",
                                     lambda: {"primary": {"used_percent": 99, "resets_at": NOW.timestamp()}})
    assert "backoff" in item.reason


def test_jitter_and_invalid_inputs(schedule):
    schedule.rng = lambda a, b: b
    assert schedule.plan_quota_retry(quota(), "project", "T-1", {}, "claude").due_at == NOW + timedelta(minutes=17)
    with pytest.raises(ValueError):
        schedule.add("resume", "project", "T-1", NOW.replace(tzinfo=None), "", 0, 5)
    with pytest.raises(ValueError):
        schedule.add("approve", "project", "T-1", NOW, "", 0, 5)
    with pytest.raises(KeyError):
        schedule.mark("missing", "done")
    with pytest.raises(ValueError):
        schedule.mark("missing", "approved")
    schedule.store.write_runtime_file("schedule.md", "invalid")
    with pytest.raises(ValueError, match="table"):
        schedule.due(NOW)


def test_once_subprocess_is_only_enqueue(schedule, hub):
    with schedule.store.transaction("project", "T-1") as txn:
        txn.state["status"] = "waiting-quota"
        txn.emit("waiting", {"set": {"status": "waiting-quota"}})
    item = schedule.plan_quota_retry(quota(), "project", "T-1", {}, "claude")
    # A past due item remains an enqueue even with an invalid/absent task approval.
    schedule.mark(item.id, "cancelled")
    ident = schedule.add("resume", "project", "T-1", NOW - timedelta(days=1), "offline", 0, 5)
    result = subprocess.run([sys.executable, str(ROOT / "scheduler.py"), "--hub-root", str(hub.root), "--once"],
                            capture_output=True, text=True, timeout=15,
                            env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"})
    assert result.returncode == 0, result.stderr
    state = schedule.store.read_state("project", "T-1")
    assert state["status"] == "waiting-quota" and state["resume_ready"]
    assert not state.get("runs") and not state.get("approval")
    assert state["resume_schedule_id"] == ident
    assert schedule.due(NOW) == []
    assert main(["--hub-root", str(hub.root), "--once"]) == 0
    assert sum(e.kind == "schedule.ready" for e in schedule.store.read_events("project", "T-1")) == 1


@pytest.mark.parametrize('episodes_today', [0, 2])
def test_claude_five_quota_attempts_have_distinct_keys(engine_env, hub, monkeypatch, episodes_today):
    from policy import load_policy
    from state_writer import plan_hash, set_approval_block
    factory, store, now, *_ = engine_env
    # Exercise the five backoffs independently of the separately tested team cap.
    path = hub.config / 'policy.toml'
    path.write_text(path.read_text().replace('team_minutes = 60', 'team_minutes = 600'), encoding='utf-8')
    hub.policy = load_policy(hub.root)
    spec = store.read_spec('project', 'T-1')
    approval = hub.record('approve-plan', project='project', task='T-1',
                          plan_hash=plan_hash(spec), policy_hash=hub.policy.policy_hash)
    store.write_spec('project', 'T-1', set_approval_block(spec, approval))
    with store.transaction('project', 'T-1') as txn:
        updates = {'approval': approval, 'approval_history': [approval]}
        txn.state.update(updates)
        txn.emit('fixture.approval', {'set': updates})
    monkeypatch.setenv('FAKE_SCENARIO', 'quota_noreset')
    engine = factory()
    current = [now]
    engine.clock = engine.scheduler.clock = engine.runner.clock = lambda: current[0]
    route = {'vendor': 'claude', 'model': 'sonnet', 'effort': 'high'}
    engine._update('project', 'T-1', 'fixture.quota', {
        'route': route, 'coder_route': route,
        'quota': {'day': now.date().isoformat(), 'episodes_today': episodes_today, 'active': False, 'attempt': 0}})
    start = engine.runner.start
    live_counts = []

    def counted(*args, **kwargs):
        run_id = start(*args, **kwargs)
        live_counts.append(len(engine.runner.live_runs()))
        assert live_counts[-1] <= 2
        return run_id

    monkeypatch.setattr(engine.runner, 'start', counted)
    state = drive(engine, store, current[0], wanted='waiting-quota')
    base_key = 'T-1:coder:1'
    for attempt, minutes in enumerate([15, 30, 60, 120, 240], 1):
        item, = engine.scheduler.due(current[0] + timedelta(days=10000))
        assert item.attempt == attempt - 1 and item.due_at == current[0] + timedelta(minutes=minutes)
        engine.tick(item.due_at - timedelta(microseconds=1))
        assert len(store.read_state('project', 'T-1')['runs']) == attempt
        current[0] = item.due_at
        engine.tick(current[0])
        spawned = store.read_state('project', 'T-1')
        assert spawned['runs'][spawned['active_run']]['idem_key'] == f'{base_key}:q{attempt}'
        assert len(engine.runner.live_runs()) <= 2
        state = drive(engine, store, current[0], wanted='needs-you' if attempt == 5 else 'waiting-quota')
        assert not engine.runner.live_runs()
    assert state['quota']['attempt'] == 5
    assert state['quota']['episodes_today'] == episodes_today + 1
    assert engine.scheduler.due(current[0] + timedelta(days=10000)) == []
    starts = [e for e in store.read_events('project', 'T-1') if e.kind == 'spawn.started']
    keys = Counter(state['runs'][event.data['run']]['idem_key'] for event in starts)
    assert keys == {base_key: 1, **{f'{base_key}:q{attempt}': 1 for attempt in range(1, 6)}}
    assert state['spawned_keys'] == dict(keys)
    assert len(live_counts) == 6 and max(live_counts) <= 2
    engine.tick(current[0] + timedelta(days=1))
    assert store.read_state('project', 'T-1')['status'] == 'needs-you'
    assert sum(e.kind == 'spawn.started' for e in store.read_events('project', 'T-1')) == 6


from test_engine_restart import drive, engine_env, runtime
from test_v1_isolation import target
