"""Focused CLI acceptance tests; all mutable data lives under tmp_path."""
import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone

import pytest


@pytest.fixture
def hub(tmp_path):
    source = Path(__file__).resolve().parents[1]
    root = tmp_path / "hub"
    (root / "tools").mkdir(parents=True)
    shutil.copyfile(source / "tools/hub.py", root / "tools/hub.py")
    shutil.copyfile(source / "models.toml", root / "models.toml")
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
               HUB_CODEX_SESSIONS=str(tmp_path / "sessions"),
               FAKE_LOG=str(tmp_path / "argv.json"), FAKE_MODE="success")
    env.pop("HUB_SIMULATE_QUOTA", None)

    def call(*args, expected=0):
        process = subprocess.run([sys.executable, "-B", str(root / "tools/hub.py"), *args],
                                 cwd=root, env=env, text=True, capture_output=True)
        assert process.returncode == expected, process.stdout + process.stderr
        return process.stdout

    call("task", "new", "sample", "--objective", "Build a CLI", "--scope", "Three files", "--orchestrator", "codex")
    (root / "brief.txt").write_text("Do the assigned work.", encoding="utf-8")
    return root, env, call


FAKE = r'''
import json, os, pathlib, subprocess, sys, time
argv = sys.argv[1:]
prompt = sys.stdin.read()
pathlib.Path(os.environ['FAKE_LOG']).write_text(json.dumps({'argv': argv, 'prompt': prompt, 'cwd': os.getcwd()}))
mode = os.environ['FAKE_MODE']
if mode == 'sleep':
    child = subprocess.Popen([sys.executable, '-c',
        'import pathlib, sys, time\np = pathlib.Path(sys.argv[1])\nend = time.monotonic() + 8\nwhile time.monotonic() < end:\n p.write_text(str(time.time()))\n time.sleep(0.05)',
        os.environ['FAKE_LOG'] + '.heartbeat'])
    time.sleep(60)
if mode == 'quota':
    print('Usage limit exceeded: quota 429', file=sys.stderr)
    sys.exit(1)
if mode == 'failure':
    print('worker failed', file=sys.stderr)
    sys.exit(7)
if argv[0] == 'exec':
    model = argv[argv.index('-m') + 1]
    effort = argv[argv.index('-c') + 1].split('=', 1)[1]
    if mode == 'mismatch':
        model = 'wrong-model'
    directory = pathlib.Path(os.environ['HUB_CODEX_SESSIONS']) / 'nested'
    directory.mkdir(parents=True, exist_ok=True)
    events = [{'type': 'turn_context', 'payload': {'model': model, 'effort': effort}},
              {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'total_tokens': 123}}}}]
    if mode == 'multiple':
        events.append({'type': 'turn_context', 'payload': {'model': 'other-model', 'effort': 'high'}})
    if mode != 'no-evidence':
        with (directory / 'rollout-test-thread123.jsonl').open('a', encoding='utf-8') as stream:
            stream.write('\n'.join(json.dumps(e) for e in events) + '\n')
    pathlib.Path(argv[argv.index('-o') + 1]).write_text(os.environ.get('FAKE_RESULT', 'Codex finished with evidence'))
    if mode != 'no-id':
        print(json.dumps({'type': 'thread.started', 'thread_id': 'thread123'}))
else:
    model = 'claude-' + argv[argv.index('--model') + 1] + '-5-5'
    print(json.dumps({'type': 'system', 'subtype': 'init', 'model': model,
                      **({'session_id': 'session-abc'} if mode != 'no-id' else {})}))
    print(json.dumps({'type': 'assistant', 'message': {'model': model}}))
    print(json.dumps({'type': 'result', 'result': os.environ.get('FAKE_RESULT', 'Claude finished with evidence')}))
'''


def fake(hub, vendor):
    root, env, _ = hub
    directory = root / "bin"
    directory.mkdir(exist_ok=True)
    script = directory / (vendor + ".py")
    script.write_text(FAKE, encoding="utf-8")
    if os.name == "nt":
        (directory / (vendor + ".cmd")).write_text(f'@echo off\n"{sys.executable}" "{script}" %*\n', encoding="utf-8")
    else:
        launcher = directory / vendor
        launcher.write_text(f'#!{sys.executable}\n' + FAKE, encoding="utf-8")
        launcher.chmod(0o755)
    env["PATH"] = str(directory) + os.pathsep + env.get("PATH", "")


def route(hub, vendor="codex", model=None, effort="low", reason="Focused implementation", extra=(), expected=0):
    root, _, call = hub
    return call("delegate", "sample", "--to", vendor, "--role", "coder", "--model", model or ("gpt-6.1-sol" if vendor == "codex" else "sonnet"),
                "--effort", effort, "--brief", str(root / "brief.txt"), "--reason", reason, "--parent", "codex", *extra, expected=expected)


def record(hub, agent_id="coder-1"):
    return (hub[0] / "work/sample/agents" / (agent_id + ".md")).read_text(encoding="utf-8")


def parallel(hub, commands):
    root, env, _ = hub
    processes = [subprocess.Popen([sys.executable, "-B", str(root / "tools/hub.py"), *args],
                                 cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for args in commands]
    outputs = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=40)
        assert process.returncode == 0, stdout + stderr
        outputs.append(stdout.strip())
    return outputs


def test_parallel_agent_ids(hub):
    args = ["agent", "new", "sample", "--role", "researcher", "--vendor", "codex", "--model", "gpt-6.1-sol",
            "--effort", "low", "--assignment", "Read the logs", "--parent", "owner"]
    ids = parallel(hub, [args] * 8)
    assert set(ids) == {f"researcher-{number}" for number in range(1, 9)}
    files = list((hub[0] / "work/sample/agents").glob("*.md"))
    assert len(files) == 8
    for agent_id in ids:
        assert f"| Agent ID | {agent_id} |" in record(hub, agent_id)


@pytest.mark.parametrize("operation", ["checkpoint", "update", "attempt"])
def test_parallel_updates(hub, operation):
    root, _, call = hub
    lines = [f"Completed item {letter}" for letter in "abcdefgh"]
    if operation == "update":
        call("agent", "new", "sample", "--role", "coder", "--vendor", "codex", "--model", "gpt-6.1-sol",
             "--effort", "low", "--assignment", "Implement", "--parent", "owner")
        commands = [["agent", "update", "sample", "coder-1", "--progress", line] for line in lines]
    elif operation == "attempt":
        commands = [["attempt", "sample", "--action", line, "--outcome", "Failed"] for line in lines]
    else:
        commands = [["checkpoint", "sample", "--section", "Completed work", "--text", line] for line in lines]
    parallel(hub, commands)
    text = record(hub) if operation == "update" else (root / "work/sample/CHECKPOINT.md").read_text(encoding="utf-8")
    for line in lines:
        assert text.count(line) == 1
    if operation == "attempt":
        entries = [json.loads(line) for line in (root / "work/sample/attempts.jsonl").read_text().splitlines()]
        assert {entry["action"] for entry in entries} == set(lines)
    assert not (root / "work/sample/.lock").exists()


def test_records_and_status(hub):
    root, _, call = hub
    cp = root / "work/sample/CHECKPOINT.md"
    initial = cp.read_text(encoding="utf-8")
    titles = [line for line in initial.splitlines() if line.startswith("## ")]
    assert titles == ["## " + name for name in ["Objective", "Approved scope", "Current state", "Completed work", "Remaining work", "Files and artifacts", "Evidence and test results", "Failures and attempted approaches", "Next recommended action"]]
    call("checkpoint", "sample", "--section", "current STATE", "--text", "Coding", "--replace")
    call("checkpoint", "sample", "--section", "Completed work", "--text", "Parser")
    changed = cp.read_text(encoding="utf-8")
    assert "## Current state\n- Coding" in changed and "Planning" not in changed
    assert initial.splitlines()[1] != changed.splitlines()[1]
    new_args = ["agent", "new", "sample", "--role", "coder", "--vendor", "codex", "--model", "gpt-6.1-sol", "--effort", "low", "--assignment", "Implement | CLI", "--parent", "owner", "--skills", "python,tests"]
    assert call(*new_args).strip() == "coder-1"
    assert call(*new_args).strip() == "coder-2"
    assert "| Actual model | Unverified |" in record(hub)
    assert "| Session / run | Unknown |" in record(hub)
    call("agent", "update", "sample", "coder-1", "--status", "running", "--actual-model", "gpt-6.1-sol", "--actual-effort", "low", "--session", "run1", "--progress", "Started", "--result", "Ready", "--blocker", "None")
    text = record(hub)
    assert "| Status | running |" in text and "Started" in text and "Ready" in text
    assert "coder-1" in call("status", "sample")
    assert "Current state: - Coding" in call("status")


def test_invalid_inputs(hub):
    root, _, call = hub
    call("task", "new", "../bad", "--objective", "x", "--scope", "y", "--orchestrator", "claude", expected=1)
    call("task", "new", "sample", "--objective", "x", "--scope", "y", "--orchestrator", "claude", expected=1)
    cp = root / "work/sample/CHECKPOINT.md"
    before = cp.read_bytes()
    call("checkpoint", "sample", "--section", "wrong", "--text", "x", expected=1)
    assert cp.read_bytes() == before
    call("agent", "new", "missing", "--role", "coder", "--vendor", "codex", "--model", "gpt-6.1-sol", "--effort", "low", "--assignment", "x", "--parent", "owner", expected=1)


@pytest.mark.parametrize("vendor,model,effort,reason,extra", [
    ("codex", "gpt-5.6-sol", "low", "A valid route reason", ("--premium", "Owner authorized this")),
    ("claude", "fable", "low", "A valid route reason", ()),
    ("claude", "opus", "low", "A valid route reason", ()),
    ("codex", "gpt-6.1-sol", "xhigh", "A valid route reason", ()),
    ("codex", "gpt-6.1-sol", "low", "short", ()),
])
def test_refusals_start_nothing(hub, vendor, model, effort, reason, extra):
    fake(hub, vendor)
    assert route(hub, vendor, model, effort, reason, extra, expected=2).startswith("REFUSED:")
    assert not Path(hub[1]["FAKE_LOG"]).exists()
    assert not list((hub[0] / "work/sample/agents").iterdir())


@pytest.mark.parametrize("vendor", ["codex", "claude"])
def test_write_requires_explicit_cwd(hub, vendor):
    fake(hub, vendor)
    assert route(hub, vendor, extra=("--write",), expected=2) == "REFUSED: --write requires explicit --cwd\n"
    assert not Path(hub[1]["FAKE_LOG"]).exists()
    assert not list((hub[0] / "work/sample/agents").iterdir())


def test_codex_verified_route(hub):
    fake(hub, "codex")
    summary = json.loads(route(hub, extra=("--write", "--cwd", str(hub[0]))))
    assert summary["status"] == "done" and summary["actual_effort"] == "low"
    log = json.loads(Path(hub[1]["FAKE_LOG"]).read_text())
    argv = log["argv"]
    assert argv.count("-m") == 1 and argv[argv.index("-m") + 1] == "gpt-6.1-sol"
    assert argv[argv.index("-s") + 1] == "workspace-write"
    assert argv[argv.index("-c") + 1] == "model_reasoning_effort=low"
    assert log["prompt"].startswith("You are a worker agent delegated by the codex orchestrator for task sample.")
    assert log["prompt"].endswith("Do the assigned work.")
    text = record(hub)
    assert "| Actual model | gpt-6.1-sol |" in text and "| Actual effort | low |" in text
    assert "rollout-test-thread123.jsonl" in text and "Total tokens: 123" in text
    assert "Codex finished with evidence" in text


def test_codex_mismatch_and_missing_evidence(hub):
    fake(hub, "codex")
    for mode in ("mismatch", "no-evidence"):
        hub[1]["FAKE_MODE"] = mode
        for path in Path(hub[1]["HUB_CODEX_SESSIONS"]).rglob("*.jsonl"):
            path.unlink()
        summary = json.loads(route(hub, expected=3))
        assert summary["status"] == "failed"
        assert summary["actual_model"] == ("wrong-model" if mode == "mismatch" else "Unverified")


def test_claude_route_and_permissions(hub):
    fake(hub, "claude")
    summary = json.loads(route(hub, "claude"))
    assert summary["actual_model"] == "claude-sonnet-5-5"
    assert summary["actual_effort"] == "Unverified" and summary["session"] == "session-abc"
    assert (hub[0] / "work/sample/agents/coder-1.last.md").read_text() == "Claude finished with evidence"
    argv = json.loads(Path(hub[1]["FAKE_LOG"]).read_text())["argv"]
    assert argv[argv.index("--allowedTools") + 1] == "Read,Glob,Grep"
    route(hub, "claude", model="opus", effort="xhigh", extra=("--premium", "Owner approved premium", "--write", "--cwd", str(hub[0]), "--allow-shell"))
    argv = json.loads(Path(hub[1]["FAKE_LOG"]).read_text())["argv"]
    assert argv[argv.index("--allowedTools") + 1] == "Read,Edit,Write,Glob,Grep,Bash"
    assert "acceptEdits" in argv


@pytest.mark.parametrize("vendor", ["codex", "claude"])
def test_quota(hub, vendor):
    fake(hub, vendor)
    hub[1]["FAKE_MODE"] = "quota"
    summary = json.loads(route(hub, vendor, expected=4))
    assert summary["status"] == "quota-unavailable"
    assert "Usage limit exceeded" in record(hub)


def test_simulated_quota(hub):
    fake(hub, "codex")
    hub[1]["HUB_SIMULATE_QUOTA"] = "codex"
    assert json.loads(route(hub, expected=4))["status"] == "quota-unavailable"
    assert not Path(hub[1]["FAKE_LOG"]).exists()
    assert "simulated quota-unavailable" in record(hub)


def test_attempt_repetition(hub):
    root, _, call = hub
    call("attempt", "sample", "--action", "Retry 123", "--outcome", "Failed 456")
    message = call("attempt", "sample", "--action", " RETRY   789", "--outcome", "FAILED 987", expected=5)
    assert "seen 2 times" in message
    call("attempt", "sample", "--action", "Retry 123", "--outcome", "Passed")
    assert len((root / "work/sample/attempts.jsonl").read_text().splitlines()) == 3


def test_sync_and_drift(hub):
    root, _, call = hub
    source = root / "agents/shared/reviewer.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nname: reviewer\ndescription: Review changes\ntools: Read,Glob,Grep\nsandbox: read-only\nskills: python,review\n---\nReview carefully.\n")
    skipped = root / "agents/shared/private.md"
    skipped.write_text("---\nname: private\ndescription: Internal\nnative: false\n---\nInternal\n")
    skill = root / "skills/review/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Review\nRead the changes.\n")
    assert "reviewer" in call("sync", "--check", expected=1)
    assert not (root / ".claude").exists()
    call("sync")
    claude = root / ".claude/agents/reviewer.md"
    codex = root / ".codex/agents/reviewer.toml"
    claude_text, codex_text = claude.read_text(), codex.read_text()
    assert "\nmodel:" not in claude_text and "\nmodel =" not in codex_text
    assert "Suggested skills: python,review" in claude_text
    assert tomllib.loads(codex_text)["developer_instructions"].startswith("Review carefully.")
    assert not (root / ".claude/agents/private.md").exists()
    assert "Read the changes." in (root / ".agents/skills/review/SKILL.md").read_text()
    assert "Read the changes." in (root / ".claude/skills/review/SKILL.md").read_text()
    call("sync", "--check")
    claude.write_text(claude_text + "drift\n")
    assert ".claude/agents/reviewer.md" in call("sync", "--check", expected=1)
    call("sync")
    preserved = root / ".codex/agents/manual.toml"
    preserved.write_text("name = 'manual'\n")
    source.unlink()
    skill.unlink()
    call("sync")
    assert not claude.exists() and not codex.exists()
    assert not (root / ".agents/skills/review/SKILL.md").exists()
    assert preserved.exists()
    call("sync", "--check")


@pytest.mark.parametrize("target", [".claude/agents/reviewer.md", ".codex/agents/reviewer.toml",
                                   ".claude/skills/review/SKILL.md", ".agents/skills/review/SKILL.md"])
def test_sync_preserves_unmarked_target(hub, target):
    root, _, call = hub
    source = root / "agents/shared/reviewer.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nname: reviewer\ndescription: Review changes\n---\nReview carefully.\n")
    skill = root / "skills/review/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Review\nRead the changes.\n")
    path = root / target
    path.parent.mkdir(parents=True)
    original = b"Owner-authored content\n"
    path.write_bytes(original)
    for args in [("sync", "--check"), ("sync",)]:
        assert "CONFLICT: " + target in call(*args, expected=1)
        assert path.read_bytes() == original


def test_missing_executable_and_process_failure(hub):
    hub[1]["PATH"] = str(hub[0] / "absent")
    assert json.loads(route(hub, expected=1))["status"] == "failed"
    assert "executable not found" in record(hub)
    fake(hub, "codex")
    hub[1]["FAKE_MODE"] = "failure"
    assert json.loads(route(hub, expected=1))["status"] == "failed"
    assert "process exited 7" in record(hub, "coder-2")


def test_codex_distinct_contexts(hub):
    fake(hub, "codex")
    hub[1]["FAKE_MODE"] = "multiple"
    summary = json.loads(route(hub, expected=3))
    assert summary["actual_model"] == "gpt-6.1-sol, other-model"
    assert summary["actual_effort"] == "low, high"


@pytest.mark.parametrize("vendor", ["codex", "claude"])
@pytest.mark.parametrize("reply,worker_status,status,code", [
    ("STATUS: BLOCKED", "BLOCKED", "blocked", 6),
    ("Details first.\n**status:** needs_context", "NEEDS_CONTEXT", "blocked", 6),
    ("STATUS: DONE_WITH_CONCERNS", "DONE_WITH_CONCERNS", "done", 0),
    ("**STATUS: DONE**\nSTATUS: BLOCKED", "BLOCKED", "blocked", 6),
    ("Finished without a status line", "Unknown", "done", 0),
    ("Inline STATUS: BLOCKED is not a status line", "Unknown", "done", 0),
    ("STATUS: UNRECOGNIZED\nSTATUS: BLOCKED", "BLOCKED", "blocked", 6),
    ("Status: blocked on lint, fixed", "Unknown", "done", 0),
    ("Status: blocked on lint", "Unknown", "done", 0),
    ("STATUS BLOCKED", "Unknown", "done", 0),
    ("STATUS: DONE - files changed: split.py - checks pass - report: R.md", "DONE", "done", 0),
    ("STATUS: BLOCKED - pytest missing - report: R.md", "BLOCKED", "blocked", 6),
    ("**STATUS:** NEEDS_CONTEXT | which branch?", "NEEDS_CONTEXT", "blocked", 6),
    ("Status: blocked-ish, fixed later", "Unknown", "done", 0),
    ("STATUS: BLOCKED\n**STATUS: DONE**\nStatus: blocked on lint", "DONE", "done", 0),
])
def test_worker_status_mapping(hub, vendor, reply, worker_status, status, code):
    fake(hub, vendor)
    hub[1]["FAKE_RESULT"] = reply
    summary = json.loads(route(hub, vendor, expected=code))
    assert summary["worker_status"] == worker_status
    assert summary["status"] == status and summary["exit"] == code
    text = record(hub)
    assert f"| Worker status | {worker_status} |" in text
    assert f"| Status | {status} |" in text
    if code == 6:
        assert "worker reported " + worker_status in text.split("## Blockers", 1)[1]
    elif worker_status == "DONE_WITH_CONCERNS":
        assert "worker reported DONE_WITH_CONCERNS" in text.split("## Progress", 1)[1].split("## Result", 1)[0]
    else:
        assert "worker reported" not in text


@pytest.mark.parametrize("worker_status", ["BLOCKED", "NEEDS_CONTEXT", "DONE_WITH_CONCERNS", "DONE"])
def test_worker_status_does_not_override_route_failure(hub, worker_status):
    fake(hub, "codex")
    hub[1]["FAKE_MODE"] = "mismatch"
    hub[1]["FAKE_RESULT"] = "STATUS: " + worker_status
    summary = json.loads(route(hub, expected=3))
    assert summary["worker_status"] == worker_status
    assert summary["status"] == "failed" and summary["exit"] == 3
    text = record(hub)
    assert f"| Worker status | {worker_status} |" in text
    assert "route mismatch or missing verification evidence" in text
    assert "worker reported" not in text


@pytest.mark.parametrize("earlier_model,mode,expected", [
    ("earlier-model", "success", 0),
    ("gpt-6.1-sol", "mismatch", 3),
    ("gpt-6.1-sol", "no-evidence", 3),
])
def test_resume_verifies_only_new_turns(hub, earlier_model, mode, expected):
    fake(hub, "codex")
    route(hub)
    rollout = next(Path(hub[1]["HUB_CODEX_SESSIONS"]).rglob("rollout-*.jsonl"))
    previous = [{"type": "turn_context", "payload": {
        "model": earlier_model, "effort": "low" if earlier_model == "gpt-6.1-sol" else "high"}}]
    rollout.write_text("\n".join(json.dumps(event) for event in previous) + "\n", encoding="utf-8")
    hub[1]["FAKE_MODE"] = mode
    summary = json.loads(route(hub, extra=("--resume", "coder-1"), expected=expected))
    assert summary["actual_model"] == {"success": "gpt-6.1-sol", "mismatch": "wrong-model",
                                       "no-evidence": "Unverified"}[mode]
    assert summary["actual_effort"] == ("Unverified" if mode == "no-evidence" else "low")
    assert summary["status"] == ("done" if expected == 0 else "failed")


@pytest.mark.parametrize("still_running", [True, False])
def test_kill_failure_preserves_live_pid_and_output(hub, monkeypatch, capsys, still_running):
    root, env, _ = hub
    spec = importlib.util.spec_from_file_location("hub_kill_failure_test", root / "tools/hub.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("HUB_CODEX_SESSIONS", env["HUB_CODEX_SESSIONS"])
    monkeypatch.delenv("HUB_SIMULATE_QUOTA", raising=False)
    monkeypatch.setattr(module.shutil, "which", lambda vendor: "fake-codex")
    partial = b'{"type":"thread.started","thread_id":"simulated-thread"}\n'

    class Process:
        pid = 12345
        returncode = None

        def __init__(self):
            self.calls = []

        def communicate(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            if len(self.calls) == 1 or still_running:
                raise subprocess.TimeoutExpired("fake-codex", kwargs["timeout"], output=partial,
                                                stderr=b"partial diagnostic")
            self.returncode = 9
            return partial.decode(), "partial diagnostic"

        def poll(self):
            return self.returncode

    process = Process()
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: process)
    killed = []

    def denied(pid):
        killed.append(pid)
        raise OSError("simulated kill denial")

    monkeypatch.setattr(module, "kill_tree", denied)
    code = module.main(["delegate", "sample", "--to", "codex", "--role", "coder", "--model", "gpt-6.1-sol",
                        "--effort", "low", "--brief", str(root / "brief.txt"), "--reason", "Test denied termination",
                        "--parent", "owner", "--timeout", "0.01"])
    summary = json.loads(capsys.readouterr().out)
    assert code == 1 and summary["status"] == "failed"
    assert killed == [process.pid] and len(process.calls) == 2
    assert process.calls[1] == ((), {"timeout": 1})
    text = record(hub)
    assert f"| PID | {process.pid if still_running else 'Unknown'} |" in text
    assert "timeout after 0.01 min; process tree termination failed: simulated kill denial" in text
    assert (root / "work/sample/agents/coder-1.events.jsonl").read_bytes() == partial


@pytest.mark.parametrize("vendor,resume_id", [("codex", "thread123"), ("claude", "session-abc")])
@pytest.mark.parametrize("writable", [False, True])
def test_resume_own_session(hub, vendor, resume_id, writable):
    fake(hub, vendor)
    route(hub, vendor)
    assert f"| Resume id | {resume_id} |" in record(hub)
    root, env, _ = hub
    (root / "brief.txt").write_text("Continue with the new assignment.", encoding="utf-8")
    extra = ("--resume", "coder-1", "--cwd", str(root)) + (("--write",) if writable else ())
    summary = json.loads(route(hub, vendor, extra=extra))
    assert summary["id"] == "coder-2" and summary["status"] == "done"
    assert "Resumes coder-1" in record(hub, "coder-2")
    log = json.loads(Path(env["FAKE_LOG"]).read_text())
    assert log["cwd"] == str(root) and log["prompt"].endswith("Continue with the new assignment.")
    argv = log["argv"]
    if vendor == "codex":
        assert argv[:4] == ["exec", "resume", resume_id, "--json"]
        assert "-s" not in argv and "-C" not in argv
        sandbox = "workspace-write" if writable else "read-only"
        assert f'sandbox_mode="{sandbox}"' in argv
        assert "model_reasoning_effort=low" in argv
    else:
        assert argv[argv.index("--resume") + 1] == resume_id


@pytest.mark.parametrize("case", ["vendor", "task", "unknown", "invalid", "missing-id", "legacy"])
def test_resume_refusals(hub, case):
    root, env, call = hub
    fake(hub, "claude")
    if case == "missing-id":
        env["FAKE_MODE"] = "no-id"
    route(hub, "claude")
    source = root / "work/sample/agents/coder-1.md"
    if case == "legacy":
        source.write_text("\n".join(line for line in source.read_text().splitlines()
                                    if not line.startswith("| Resume id |")), encoding="utf-8")
    if case == "task":
        call("task", "new", "other", "--objective", "x", "--scope", "y", "--orchestrator", "claude")
        shutil.copyfile(source, root / "work/other/agents/coder-1.md")
    Path(env["FAKE_LOG"]).unlink()
    task = "other" if case == "task" else "sample"
    output = call("delegate", task, "--to", "codex" if case == "vendor" else "claude",
                  "--role", "coder", "--model", "gpt-6.1-sol" if case == "vendor" else "sonnet",
                  "--effort", "low", "--brief", str(root / "brief.txt"), "--reason", "Continue the assignment",
                  "--parent", "owner", "--resume",
                  "../bad" if case == "invalid" else "absent" if case == "unknown" else "coder-1", expected=2)
    assert output.startswith("REFUSED:") and not Path(env["FAKE_LOG"]).exists()
    assert not (root / f"work/{task}/agents/coder-2.md").exists()


@pytest.mark.parametrize("vendor,expected", [("claude", 0), ("codex", 3)])
def test_absent_resume_id_is_unknown(hub, vendor, expected):
    fake(hub, vendor)
    hub[1]["FAKE_MODE"] = "no-id"
    route(hub, vendor, expected=expected)
    assert "| Resume id | Unknown |" in record(hub)


@pytest.mark.parametrize("minutes", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_timeout_starts_nothing(hub, minutes):
    fake(hub, "codex")
    route(hub, extra=("--timeout", minutes), expected=2)
    assert not Path(hub[1]["FAKE_LOG"]).exists()
    assert not list((hub[0] / "work/sample/agents").iterdir())


def wait_for(predicate):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    pytest.fail("timed out waiting for worker readiness")


def assert_tree_stopped(hub):
    heartbeat = Path(hub[1]["FAKE_LOG"] + ".heartbeat")
    assert heartbeat.exists(), "sleeping child never started"
    time.sleep(0.15)
    value = heartbeat.read_bytes()
    time.sleep(0.2)
    assert heartbeat.read_bytes() == value, "worker child survived tree termination"


@pytest.mark.parametrize("vendor", ["codex", "claude"])
def test_timeout_kills_tree(hub, vendor):
    fake(hub, vendor)
    hub[1]["FAKE_MODE"] = "sleep"
    start = time.monotonic()
    result = json.loads(route(hub, vendor, extra=("--timeout", "0.05"), expected=1))
    assert time.monotonic() - start < 15
    assert result["status"] == "failed"
    assert "timeout after 0.05 min" in record(hub)
    assert "| PID | Unknown |" in record(hub)
    assert_tree_stopped(hub)


@pytest.mark.parametrize("vendor", ["codex", "claude"])
def test_stop_kills_tree_and_preserves_cancelled(hub, vendor):
    fake(hub, vendor)
    root, env, call = hub
    env["FAKE_MODE"] = "sleep"
    args = ["delegate", "sample", "--to", vendor, "--role", "coder", "--model",
            "gpt-6.1-sol" if vendor == "codex" else "sonnet", "--effort", "low", "--brief", str(root / "brief.txt"),
            "--reason", "Test stopping a worker", "--parent", "owner", "--timeout", "0.5"]
    process = subprocess.Popen([sys.executable, "-B", str(root / "tools/hub.py"), *args],
                               cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        wait_for(lambda: Path(env["FAKE_LOG"] + ".heartbeat").exists())
        assert "| Status | running |" in record(hub)
        assert "| PID | Unknown |" not in record(hub)
        call("stop", "sample", "coder-1")
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 1, stdout + stderr
        assert json.loads(stdout)["status"] == "cancelled"
        text = record(hub)
        assert "| Status | cancelled |" in text and "stopped by orchestrator" in text
        assert "| PID | Unknown |" in text and "process exited" not in text
        assert_tree_stopped(hub)
        assert call("stop", "sample", "coder-1", expected=1).startswith("ERROR:")
    finally:
        if process.poll() is None:
            # Best effort only: preserve the original failure if this environment
            # denies process termination. The fake and child both expire on their own.
            subprocess.run([sys.executable, "-B", str(root / "tools/hub.py"), "stop", "sample", "coder-1"],
                           cwd=root, env=env, text=True, capture_output=True)


def test_stop_rejects_missing_or_nonrunning_pid(hub):
    _, _, call = hub
    assert call("stop", "sample", "absent", expected=1).startswith("ERROR:")
    call("agent", "new", "sample", "--role", "coder", "--vendor", "codex", "--model", "gpt-6.1-sol",
         "--effort", "low", "--assignment", "Implement", "--parent", "owner")
    for state in ("planned", "running", "done"):
        call("agent", "update", "sample", "coder-1", "--status", state)
        assert call("stop", "sample", "coder-1", expected=1).startswith("ERROR:")


def test_log_append_show_and_validation(hub):
    root, _, call = hub
    day = datetime.now(timezone.utc).date().isoformat()
    assert call("log", "--show") == ""
    assert call("log", "--show", "2001-01-01") == ""
    for kind in ("outcome", "decision", "feedback", "context"):
        call("log", kind, "--text", "first\nsecond\r\nthird", "--task", "sample")
    call("log", "context", "--text", "No task")
    lines = call("log", "--show", day).splitlines()
    assert len(lines) == 5
    for kind, line in zip(("outcome", "decision", "feedback", "context"), lines):
        assert line.startswith("- ") and line[10:12] == "Z "
        assert f"{kind}: [sample] first second third" in line
    assert lines[-1].endswith("context: No task")
    assert call("log", "--show") == (root / f"work/log/{day}.md").read_text()
    call("log", "--show", "../bad", expected=1)
    call("log", "--text", "missing kind", expected=1)
    call("log", "outcome", expected=1)
    call("log", "outcome", "--text", "x", "--show", expected=1)
    call("log", "other", "--text", "x", expected=2)


@pytest.mark.parametrize("text", [
    "key sk-ant-api03-abcdefghijklmnop0123", "token ghp_abcdefghijklmnopqrstuvwxyz0123", "AKIAABCDEFGHIJKLMNOP leaked",
    "-----BEGIN OPENSSH PRIVATE KEY-----", "password=hunter2", "API_KEY: abc123", "Token = abc",
    "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig", "DB_PASSWORD=abc", "client_secret=abc",
    "password: hunter2", "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345",
])
def test_log_rejects_secret_shapes(hub, text):
    root, _, call = hub
    out = call("log", "context", "--text", text, expected=1)
    assert out.startswith("ERROR:") and text not in out
    assert not (root / "work/log").exists() or not any((root / "work/log").glob("*.md"))


@pytest.mark.parametrize("text", [
    "password=*** rotated by the owner", "token: ***", "Discussed token budgets and the secret of fast reviews",
    "sk-short", "Use the ask-mode", "api key handling reviewed", "secret: see vault", "token: 150k used",
    "token budget: 150k", "token_count=5 tokens", "password: ***",
])
def test_log_allows_redacted_and_prose(hub, text):
    _, _, call = hub
    call("log", "context", "--text", text)
    assert text in call("log", "--show")


def test_concurrent_log_appends(hub):
    messages = [f"unique entry {i}" for i in range(12)]
    parallel(hub, [["log", "outcome", "--text", message, "--task", "sample"] for message in messages])
    lines = hub[2]("log", "--show").splitlines()
    assert len(lines) == len(messages)
    assert {line.split("[sample] ", 1)[1] for line in lines} == set(messages)
    assert not (hub[0] / "work/log/.lock").exists()
