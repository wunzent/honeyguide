from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import psutil
import pytest

from adapters.base import Availability, InvalidResumeSession, Outcome, Route, get_adapter, validate_session_id
from adapters.codex_cli import CodexAdapter
from agent_loader import load_template
from model_router import RouteError, resolve
from policy import PolicyError
from runner import Runner, _tool_violation, _tool_violations
from test_bridge import call
from test_engine_restart import engine_env, runtime, start, finished, drive, wait_until
from test_path_policy import hub
from test_v1_isolation import target, routing


ROOT = Path(__file__).resolve().parents[1]
SESSION = "019c6e27-e55b-73d1-87d8-4e01f1f75043"


@pytest.fixture
def live_a_init():
    """Trimmed LIVE-A 2.1.312 schema with synthetic values only."""
    return json.loads('''{
      "type": "system", "subtype": "init", "cwd": ".", "session_id": "fixture-session",
      "tools": ["Read", "Glob", "Grep"], "mcp_servers": [], "model": "fixture",
      "permissionMode": "default", "slash_commands": [], "terminal_slash_commands": [],
      "apiKeySource": "none", "claude_code_version": "2.1.312", "output_style": "default",
      "agents": ["fixture-agent"], "skills": [], "plugins": [], "capabilities": {}
    }''')


def test_trimmed_real_init_schema(live_a_init):
    assert not _tool_violation([live_a_init], ["Read", "Glob", "Grep"])


@pytest.fixture
def unlocked_live_a_init(live_a_init):
    # Preserve observed list sizes and entry shapes; omit all real names and paths.
    live_a_init.update(
        slash_commands=["fixture-command"] * 144, skills=["fixture-skill"] * 108,
        agents=["fixture-agent"] * 19,
        plugins=[{"name": "fixture-plugin", "path": "./fixture"}] * 10,
        mcp_servers=[{"name": "fixture-server", "status": "connected", "source": "fixture"}] * 16)
    return live_a_init


def test_trimmed_unlocked_live_a_schema_rejected(unlocked_live_a_init):
    assert _tool_violations([unlocked_live_a_init], ["Read", "Glob", "Grep"]) == {
        "slash_commands": 144, "skills": 108, "plugins": 10, "mcp_servers": 16}


@pytest.mark.parametrize("field", ["tools", "mcp_servers", "slash_commands", "terminal_slash_commands",
                                   "skills", "plugins", "agents"])
@pytest.mark.parametrize("malformed", ["missing", None, {}, "unexpected", 1])
def test_init_missing_or_nonlist_fails_closed(live_a_init, field, malformed):
    if malformed == "missing":
        live_a_init.pop(field)
    else:
        live_a_init[field] = malformed
    assert _tool_violation([live_a_init], ["Read", "Glob", "Grep"])


@pytest.mark.parametrize("tool", ["Agent", "Task", "Bash", "PowerShell", "Edit", "Write", "NotebookEdit",
                                  "WebFetch", "WebSearch", "mcp__fixture__read"])
def test_forbidden_tools_rejected_even_if_allowlisted(live_a_init, tool):
    live_a_init["tools"].append(tool)
    assert _tool_violation([live_a_init], live_a_init["tools"])


def test_every_init_is_checked(live_a_init):
    unsafe = {**live_a_init, "skills": ["fixture"]}
    assert _tool_violation([unsafe, live_a_init], ["Read", "Glob", "Grep"])


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_trailing_null_session_survives_runner(runtime, monkeypatch, vendor):
    runner, _ = runtime
    monkeypatch.setenv("FAKE_SCENARIO", "trailing_null_session")
    monkeypatch.setenv("FAKE_SESSION_ID", SESSION)
    run_id = start(runtime, vendor)
    assert finished(runner, run_id).session_id == SESSION
    assert runner.store.read_state("project", "T-1")["runs"][run_id]["session_id"] == SESSION
    assert sum(e.kind == "session.invalid" for e in runner.store.read_events("project", "T-1")) == 1


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_runner_preserves_stored_session(runtime, monkeypatch, vendor):
    runner, _ = runtime
    run_id = start(runtime, vendor)
    classify = runner.adapters[vendor].classify
    monkeypatch.setattr(runner.adapters[vendor], "classify", lambda *args: replace(classify(*args), session_id=None))
    with runner.store.transaction("project", "T-1") as txn:
        txn.state["runs"][run_id]["session_id"] = SESSION
        txn.emit("fixture", {"set": {"runs": txn.state["runs"]}})
    assert finished(runner, run_id).session_id == SESSION
    assert runner.store.read_state("project", "T-1")["runs"][run_id]["session_id"] == SESSION


@pytest.mark.parametrize("source", ["run", "checkpoint"])
def test_quota_preserves_stored_session(engine_env, source):
    factory, store, now, *_ = engine_env
    engine = factory()
    state = store.read_state("project", "T-1")
    run = {"idem_key": "fixture-key", "role": "coder", "route": {"vendor": "codex", "model": "gpt-6.1-sol", "effort": "medium"}}
    if source == "run":
        run["session_id"] = SESSION
    else:
        state["checkpoint"] = {"session_id": SESSION}
    engine._quota("project", "T-1", state, "fixture-run", run,
                  Outcome("quota_limited", None, None, None, "", {}))
    assert store.read_state("project", "T-1")["checkpoint"]["session_id"] == SESSION


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("invalid", ["", "bad id", 42])
def test_invalid_resume_refuses_spawn_and_blocks(engine_env, monkeypatch, vendor, invalid):
    factory, store, now, *_ = engine_env
    from engine import _ResumeAdapter
    engine = factory()
    original = engine.runner.adapters[vendor]
    engine.runner.adapters[vendor] = _ResumeAdapter(original, invalid)
    worktree = engine.worktrees.create(engine.policy, "project", "T-1", Path(engine._project("project")["repo"]), "HEAD")
    monkeypatch.setattr("runner.subprocess.Popen", lambda *args, **kwargs: pytest.fail("invalid resume spawned"))
    with pytest.raises(InvalidResumeSession):
        engine.runner.start("project", "T-1", "coder", Route(vendor, "sonnet", "low"),
                            load_template(ROOT / "agents/coder.md"), worktree, "fixture-key",
                            {"approved_plan": "Fixture", "repository_context": "Fixture"})
    state = store.read_state("project", "T-1")
    assert state["status"] == "needs-you" and not state.get("runs")
    events = store.read_events("project", "T-1")
    assert sum(e.kind == "session.resume_refused" for e in events) == 1
    assert not any(e.kind.startswith("spawn.") for e in events)


def test_route_rejections_deduplicated_across_ticks_and_restart(engine_env):
    factory, store, now, *_ = engine_env
    propose(store.root, "coder", "codex", "invalid-model")
    engine = factory()
    engine.availability_probe = lambda vendor: Availability(False, "fake", False, "offline")
    for index in range(8):
        engine._update("project", "T-1", "fixture.retry", {"status": "approved"})
        engine.tick(now)
        if index == 3:
            engine.close()
            engine = factory()
            engine.availability_probe = lambda vendor: Availability(False, "fake", False, "offline")
    assert sum(e.kind == "route.rejected" for e in store.read_events("project", "T-1")) == 1
    propose(store.root, "coder", "codex", "another-invalid-model")
    engine._update("project", "T-1", "fixture.retry", {"status": "approved"})
    engine.tick(now)
    assert sum(e.kind == "route.rejected" for e in store.read_events("project", "T-1")) == 2


def test_route_rejections_changed_reason_emits_again(engine_env, monkeypatch):
    factory, store, now, *_ = engine_env
    propose(store.root, "coder", "codex", "invalid-model")
    engine = factory()
    state = store.read_state("project", "T-1")
    for reason in ("first refusal", "first refusal", "different refusal"):
        def reject(*args, **kwargs):
            raise RouteError(reason)
        monkeypatch.setattr("engine.resolve", reject)
        with pytest.raises(RouteError):
            engine._route("coder", state, set(), project="project", task="T-1")
    assert sum(e.kind == "route.rejected" for e in store.read_events("project", "T-1")) == 2


def test_route_rejection_key_uses_canonical_proposal_and_role(engine_env, monkeypatch):
    factory, store, now, *_ = engine_env
    propose(store.root, "coder", "codex", "invalid-model")
    engine = factory()
    state = store.read_state("project", "T-1")

    def reject(*args, **kwargs):
        raise RouteError("same refusal")

    monkeypatch.setattr("engine.resolve", reject)
    for changed in (False, False, True):
        proposal = dict(reversed(list(state["route_proposals"]["coder"].items())))
        if changed:
            proposal["effort"] = "high"
        state["route_proposals"]["coder"] = proposal
        with pytest.raises(RouteError):
            engine._route("coder", state, set(), project="project", task="T-1")
    assert sum(e.kind == "route.rejected" for e in store.read_events("project", "T-1")) == 2
    state["route_proposals"]["reviewer"] = dict(proposal)
    with pytest.raises(RouteError):
        engine._route("reviewer", state, set(), project="project", task="T-1")
    assert sum(e.kind == "route.rejected" for e in store.read_events("project", "T-1")) == 3


def test_init_agents_count_recorded_without_names(runtime):
    runner, _ = runtime
    run_id = start(runtime, "claude")
    assert finished(runner, run_id).status == "ok"
    directory = runner.store.task_dir("project", "T-1") / "runs" / run_id
    meta = (directory / "meta.md").read_text()
    assert '"agents_count": 1' in meta and "fixture-agent" not in meta


def propose(root, role, vendor, model, effort="low", *extra):
    return call(root, "propose-route", "project", "T-1", "--role", role,
                "--vendor", vendor, "--model", model, "--effort", effort,
                "--reason", "Owner-approved LIVE-A fix", *extra)


def test_role_proposals_dispatch_and_claude_budget(engine_env):
    factory, store, now, *_ = engine_env
    propose(store.root, "coder", "codex", "gpt-6-luna", "high")
    propose(store.root, "reviewer", "claude", "haiku", "low", "--budget-usd", "0.5")
    proposals = store.read_state("project", "T-1")["route_proposals"]
    assert set(proposals) == {"coder", "reviewer"}
    engine = factory()
    state = drive(engine, store, now, wanted="reviewing")
    coder = next(run for run in state["runs"].values() if run.get("role") == "coder")
    assert coder["route"] == {"vendor": "codex", "model": "gpt-6-luna", "effort": "high", "max_budget_usd": None}
    engine.tick(now)
    reviewer = next(run for run in store.read_state("project", "T-1")["runs"].values() if run.get("role") == "reviewer")
    assert reviewer["route"] == {"vendor": "claude", "model": "haiku", "effort": "low", "max_budget_usd": 0.5}
    assert reviewer["argv"][reviewer["argv"].index("--max-budget-usd") + 1] == "0.5"


@pytest.mark.parametrize("model,effort", [("not-in-catalog", "low"), ("gpt-6-luna", "invalid")])
def test_invalid_proposal_rejected_then_policy_default(engine_env, model, effort):
    factory, store, now, *_ = engine_env
    propose(store.root, "coder", "codex", model, effort)
    engine = factory()
    engine.tick(now)
    state = store.read_state("project", "T-1")
    assert state["coder_route"]["model"] == "gpt-6.1-sol"
    assert state["coder_route"]["effort"] == "medium"
    event = next(event for event in store.read_events("project", "T-1") if event.kind == "route.rejected")
    assert event.data["role"] == "coder" and "not allowed" in event.data["reason"]


@pytest.mark.parametrize("case", ["unavailable", "quota", "invalid-other-vendor", "reviewer"])
def test_proposal_cannot_bypass_policy(engine_env, case):
    factory, store, now, *_ = engine_env
    propose(store.root, "coder", "claude" if case == "invalid-other-vendor" else "codex",
            "unknown" if case == "invalid-other-vendor" else "gpt-6-luna")
    if case == "quota":
        with store.transaction("project", "T-1") as txn:
            txn.state["quota_blocked"] = ["codex"]
            txn.emit("fixture.quota", {"set": {"quota_blocked": ["codex"]}})
    if case == "reviewer":
        propose(store.root, "reviewer", "codex", "gpt-6-luna")
        with store.transaction("project", "T-1") as txn:
            updates = {"status": "reviewing", "coder_vendor": "codex", "needs_run": True}
            txn.state.update(updates)
            txn.emit("fixture.review", {"set": updates})
    engine = factory()
    if case == "unavailable":
        engine.availability_probe = lambda vendor: Availability(vendor != "codex", "fake", True, "offline")
    engine.tick(now)
    state = store.read_state("project", "T-1")
    assert state["status"] == "needs-you" and not state.get("runs")
    assert any(event.kind == "route.rejected" for event in store.read_events("project", "T-1"))


@pytest.mark.parametrize("vendor,budget", [("codex", "0.5"), ("claude", "0"), ("claude", "-1"),
                                          ("claude", "nan"), ("claude", "inf")])
def test_bridge_budget_refused(runtime, vendor, budget):
    runner, _ = runtime
    call(runner.hub_root, "propose-route", "project", "T-1", "--role", "coder", "--vendor", vendor,
         "--model", "sonnet", "--effort", "low", "--reason", "test", "--budget-usd", budget, expected=2)
    assert not runner.store.read_state("project", "T-1").get("route_proposals")


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "0.5"])
def test_router_budget_validation(routing, value):
    with pytest.raises(RouteError, match="budget"):
        resolve(Route("claude", "sonnet", "low", value), "coder", **routing)
    with pytest.raises(RouteError, match="budget"):
        resolve(Route("codex", "gpt-6.1-sol", "low", 0.5), "coder", **routing)


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_uuid_session_survives_state_events_meta_and_resume(runtime, monkeypatch, vendor):
    runner, worktree = runtime
    monkeypatch.setenv("FAKE_SESSION_ID", SESSION)
    run_id = start(runtime, vendor)
    outcome = finished(runner, run_id)
    assert outcome.session_id == SESSION
    state = runner.store.read_state("project", "T-1")
    assert state["runs"][run_id]["session_id"] == SESSION
    assert next(e for e in runner.store.read_events("project", "T-1") if e.kind == "run.finished").data["session_id"] == SESSION
    directory = runner.store.task_dir("project", "T-1") / "runs" / run_id
    assert SESSION in (directory / "meta.md").read_text()
    template = load_template(ROOT / "agents" / "coder.md")
    spec = runner.adapters[vendor].build(template, Route(vendor, "sonnet", "low"), directory,
                                         worktree, directory / "prompt.md", outcome.session_id)
    if vendor == "claude":
        assert spec.argv[-2:] == ["--resume", SESSION]
    else:
        index = spec.argv.index("exec")
        assert spec.argv[index:index + 3] == ["exec", "resume", SESSION]


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("change_model", [False, True])
def test_latest_proposal_on_quota_resume(engine_env, monkeypatch, tmp_path, vendor, change_model):
    factory, store, now, *_ = engine_env
    role = "reviewer" if vendor == "claude" else "coder"
    model = "sonnet" if vendor == "claude" else "gpt-6.1-sol"
    propose(store.root, role, vendor, model)
    if role == "reviewer":
        with store.transaction("project", "T-1") as txn:
            changes = {"status": "reviewing", "coder_vendor": "codex", "needs_run": True}
            txn.state.update(changes)
            txn.emit("fixture", {"set": changes})
    monkeypatch.setenv("FAKE_SCENARIO", "quota_noreset")
    monkeypatch.setenv("FAKE_SESSION_ID", SESSION)
    engine = factory()
    state = drive(engine, store, now, wanted="waiting-quota")
    assert state["checkpoint"]["session_id"] == SESSION
    if change_model:
        model = "haiku" if vendor == "claude" else "gpt-6-luna"
    propose(store.root, role, vendor, model, "high")
    log = tmp_path / "resume-argv.json"
    monkeypatch.setenv("FAKE_ARGV_LOG", str(log))
    monkeypatch.setenv("FAKE_SCENARIO", "ok")
    with store.transaction("project", "T-1") as txn:
        txn.state["resume_ready"] = True
        txn.emit("fixture.resume", {"set": {"resume_ready": True}})
    engine.tick(now)
    wait_until(log.exists)
    argv = json.loads(log.read_text())
    assert (SESSION in argv) is (not change_model)
    assert ("--resume" in argv if vendor == "claude" else "resume" in argv) is (not change_model)
    run = store.read_state("project", "T-1")["runs"][store.read_state("project", "T-1")["active_run"]]
    assert run["route"]["model"] == model and run["route"]["effort"] == "high"
    assert sum(e.kind == "session.resume_refused" for e in store.read_events("project", "T-1")) == int(change_model)


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("session", ["bad id", "x" * 129, "short", "session/unsafe", "[REDACTED]"])
def test_invalid_session_refused(runtime, monkeypatch, vendor, session):
    runner, _ = runtime
    monkeypatch.setenv("FAKE_SESSION_ID", session)
    run_id = start(runtime, vendor)
    assert finished(runner, run_id).session_id is None
    assert runner.store.read_state("project", "T-1")["runs"][run_id]["session_id"] is None
    invalid = [e for e in runner.store.read_events("project", "T-1") if e.kind == "session.invalid"]
    assert len(invalid) == 1
    assert session not in json.dumps(invalid[0].data)


@pytest.mark.parametrize("value,valid", [(SESSION, True), ("a" * 128, True), ("thread_123", True),
                                        ("bad id", False), (None, False), (12, False)])
def test_identifier_validation(value, valid):
    assert validate_session_id(value) == (value if valid else None)


def test_structured_usage_keeps_identifiers_and_scrubs_prose(runtime, monkeypatch):
    runner, _ = runtime
    adapter = runner.adapters["codex"]
    classify = adapter.classify

    def usage(*args):
        return replace(classify(*args), usage={"session_id": SESSION, "thread_id": SESSION,
                                              "text": "sk-throwaway-usage"})

    monkeypatch.setattr(adapter, "classify", usage)
    outcome = finished(runner, start(runtime))
    assert outcome.usage == {"session_id": SESSION, "thread_id": SESSION, "text": "[REDACTED]"}


@pytest.mark.parametrize("scenario", ["extra_tools", "extra_mcp", "missing_init", "extra_slash_commands",
                                      "extra_terminal_slash_commands", "extra_skills", "extra_plugins", "missing_key"])
@pytest.mark.parametrize("role", ["coder", "reviewer"])
def test_tool_violation_fails_closed(engine_env, monkeypatch, scenario, role):
    factory, store, now, *_ = engine_env
    monkeypatch.setenv("FAKE_SCENARIO", scenario)
    propose(store.root, role, "claude", "sonnet")
    if role == "reviewer":
        with store.transaction("project", "T-1") as txn:
            changes = {"status": "reviewing", "coder_vendor": "codex", "needs_run": True}
            txn.state.update(changes)
            txn.emit("fixture", {"set": changes})
    engine = factory()
    worktree = engine.worktrees.create(engine.policy, "project", "T-1", Path(engine._project("project")["repo"]), "HEAD")
    before = (worktree / "hello.txt").read_bytes()
    monkeypatch.setattr(engine.worktrees, "apply_patch", lambda *args: pytest.fail("violating result applied a patch"))
    state = drive(engine, store, now, wanted="needs-you")
    run_id, run = next(iter(state["runs"].items()))
    assert run["status"] == "failed" and run["reason"] == "tool_restriction_violated"
    assert not state.get("review") and not state.get("last_coder_run")
    assert (Path(run["worktree"]) / "hello.txt").read_bytes() == before
    directory = store.task_dir("project", "T-1") / "runs" / run_id
    assert (directory / "result.md").read_text() == ""
    assert sum(e.kind == "security.tool_violation" for e in store.read_events("project", "T-1")) == 1
    violation = next(e for e in store.read_events("project", "T-1") if e.kind == "security.tool_violation")
    expected = {"extra_tools": {"tools": 6}, "extra_mcp": {"mcp_servers": 1}, "missing_init": {"init": 0},
                "extra_slash_commands": {"slash_commands": 1},
                "extra_terminal_slash_commands": {"terminal_slash_commands": 1},
                "extra_skills": {"skills": 1}, "extra_plugins": {"plugins": 1}, "missing_key": {"skills": -1}}
    assert violation.data["fields"] == expected[scenario]
    assert "fixture-agent" not in json.dumps(violation.data)
    assert "./fixture" not in json.dumps(violation.data)


@pytest.mark.parametrize("tools,servers,violation", [
    (["Read", "Glob", "Grep"], [], False), (["Read"], [{"status": "disabled"}], False),
    ([], [{"status": "failed"}], False), (["CronCreate"], [], True),
    (["Read"], [{"status": "connected"}], True), (["Read"], [{}], True),
    (None, [], True), ([], None, True), ([{}], [], True),
])
def test_init_validation(tools, servers, violation):
    assert _tool_violation([{"type": "system", "subtype": "init", "tools": tools, "mcp_servers": servers,
                            "slash_commands": [], "terminal_slash_commands": [], "skills": [],
                            "plugins": [], "agents": []}],
                           ["Read", "Glob", "Grep"]) is violation


def test_claude_flags_follow_template_capabilities(tmp_path):
    template = load_template(ROOT / "agents" / "coder.md")
    adapter = get_adapter("claude", [sys.executable, str(ROOT / "tests/fakes/fake_claude.py")])
    for capabilities, tools in [(template.capabilities, "Read,Glob,Grep"), (("read",), "Read"),
                                (("search",), "Glob,Grep")]:
        spec = adapter.build(replace(template, capabilities=capabilities), Route("claude", "sonnet", "low"),
                             tmp_path, tmp_path, tmp_path / "prompt.md")
        assert spec.argv[spec.argv.index("--tools") + 1] == tools
        assert spec.argv[spec.argv.index("--allowedTools") + 1] == tools
        assert "--strict-mcp-config" in spec.argv and "--disable-slash-commands" in spec.argv
        assert "--mcp-config" not in spec.argv


@pytest.mark.parametrize("resolved", [True, False])
def test_codex_node_resolution(tmp_path, monkeypatch, resolved):
    command = tmp_path / "codex.cmd"
    command.write_text('@echo off\nnode "%~dp0\\node_modules\\@openai\\codex\\bin\\codex.js" %*\n')
    script = tmp_path / "node_modules/@openai/codex/bin/codex.js"
    script.parent.mkdir(parents=True)
    if resolved:
        script.write_text("// throwaway target")
    node = tmp_path / "node.exe"
    node.write_bytes(b"fake")
    monkeypatch.setattr("adapters.codex_cli.shutil.which", lambda name: str(node if name == "node" else command))
    adapter = CodexAdapter()
    assert adapter.executable == ([str(node.resolve()), str(script.resolve())] if resolved else [str(command)])
    assert (adapter.launcher_note is None) is resolved


def test_stop_owned_tree_preserves_unrelated_and_checks_token(runtime, tmp_path):
    runner, _ = runtime
    launcher = tmp_path / "tree.py"
    child_pid_file = tmp_path / "child.pid"
    launcher.write_text("import subprocess, sys, time\nfrom pathlib import Path\n"
                        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                        f"Path({str(child_pid_file)!r}).write_text(str(child.pid))\n"
                        "time.sleep(60)\n", encoding="utf-8")
    runner.adapters["codex"] = get_adapter("codex", [sys.executable, str(launcher)])
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], cwd=tmp_path)
    child = None
    try:
        run_id = start(runtime)
        wait_until(child_pid_file.exists)
        child = psutil.Process(int(child_pid_file.read_text()))
        record = runner.store.read_state("project", "T-1")["runs"][run_id]
        restarted = Runner(runner.store, runner.adapters, runner.worktrees, runner.hub_root)
        with pytest.raises(PolicyError, match="foreign"):
            restarted.stop(record["pid"], record["create_time"] - 10)
        with runner.store.transaction("project", "T-1") as txn:
            txn.state["runs"][run_id]["run_token"] = "incorrect-token"
            txn.emit("fixture", {"set": {"runs": txn.state["runs"]}})
        with pytest.raises(PolicyError, match="foreign"):
            restarted.stop(record["pid"], record["create_time"])
        assert child.is_running() and unrelated.poll() is None
        with runner.store.transaction("project", "T-1") as txn:
            txn.state["runs"][run_id] = record
            txn.emit("fixture", {"set": {"runs": txn.state["runs"]}})
        restarted.stop(record["pid"], record["create_time"])
        runner._processes["project", "T-1", run_id].wait(timeout=5)
        assert not child.is_running()
        assert unrelated.poll() is None
    finally:
        if child is not None and child.is_running():
            child.kill()
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_timeout_stops_test_process_tree(runtime, tmp_path):
    runner, worktree = runtime
    launcher = tmp_path / "test_tree.py"
    pid_file = tmp_path / "test-child.pid"
    launcher.write_text("import subprocess, sys, time\nfrom pathlib import Path\n"
                        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                        f"Path({str(pid_file)!r}).write_text(str(child.pid))\n"
                        "time.sleep(60)\n", encoding="utf-8")
    try:
        result = runner.run_tests("project", "T-1", worktree, [sys.executable, str(launcher)], 2)
        assert result["exit_code"] == -1 and not result["passed"]
        assert pid_file.exists()
        assert not psutil.pid_exists(int(pid_file.read_text()))
    finally:
        if pid_file.exists() and psutil.pid_exists(int(pid_file.read_text())):
            psutil.Process(int(pid_file.read_text())).kill()


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_metadata_evidence_without_secrets(runtime, monkeypatch, vendor):
    runner, _ = runtime
    adapter = runner.adapters[vendor]
    build = adapter.build
    secret = "Bearer test-free-text-secret"

    def with_secret(*args, **kwargs):
        spec = build(*args, **kwargs)
        return replace(spec, argv=spec.argv + [secret, "sk-throwaway-test"],
                       env=spec.env | {"PRIVATE_TEST_VALUE": "never-record-this-env"})

    monkeypatch.setattr(adapter, "build", with_secret)
    run_id = start(runtime, vendor)
    directory = runner.store.task_dir("project", "T-1") / "runs" / run_id
    initial_meta = (directory / "meta.md").read_text()
    finished(runner, run_id)
    meta_text = (directory / "meta.md").read_text()
    meta = json.loads(meta_text.split("```json\n", 1)[1].split("\n```", 1)[0])
    assert meta["prompt_sha256"] == hashlib.sha256((directory / "prompt.md").read_bytes()).hexdigest()
    assert meta["body_sha256"] == load_template(ROOT / "agents/coder.md").body_sha256
    assert meta["template_role"] == "coder" and meta["route"]["vendor"] == vendor
    assert {"vendor", "model", "effort", "max_budget_usd"} <= meta["route"].keys()
    assert Path(meta["executable_resolved_path"]) == Path(sys.executable).resolve()
    token = runner.store.read_state("project", "T-1")["runs"][run_id]["run_token"]
    for text in (initial_meta, meta_text):
        for forbidden in (secret, "sk-throwaway", "never-record-this-env", "HUB_RUN_TOKEN", "run_token", token,
                          "Implement hello.txt only."):
            assert forbidden not in text
    assert "[REDACTED]" in meta_text
