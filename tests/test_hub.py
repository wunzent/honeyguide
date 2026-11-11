"""Focused CLI acceptance tests; all mutable data lives under tmp_path."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

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
import json, os, pathlib, sys
argv = sys.argv[1:]
prompt = sys.stdin.read()
pathlib.Path(os.environ['FAKE_LOG']).write_text(json.dumps({'argv': argv, 'prompt': prompt, 'cwd': os.getcwd()}))
mode = os.environ['FAKE_MODE']
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
        (directory / 'rollout-test-thread123.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
    pathlib.Path(argv[argv.index('-o') + 1]).write_text('Codex finished with evidence')
    print(json.dumps({'type': 'thread.started', 'thread_id': 'thread123'}))
else:
    model = 'claude-' + argv[argv.index('--model') + 1] + '-5-5'
    print(json.dumps({'type': 'system', 'subtype': 'init', 'model': model, 'session_id': 'session-abc'}))
    print(json.dumps({'type': 'assistant', 'message': {'model': model}}))
    print(json.dumps({'type': 'result', 'result': 'Claude finished with evidence'}))
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
    ("codex", "gpt-6-luna", "low", "A valid route reason", ("--premium", "Owner authorized this")),
    ("claude", "haiku", "low", "A valid route reason", ()),
    ("claude", "opus", "low", "A valid route reason", ()),
    ("codex", "gpt-6.1-sol", "xhigh", "A valid route reason", ()),
    ("codex", "gpt-6.1-sol", "low", "short", ()),
])
def test_refusals_start_nothing(hub, vendor, model, effort, reason, extra):
    fake(hub, vendor)
    assert route(hub, vendor, model, effort, reason, extra, expected=2).startswith("REFUSED:")
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
    route(hub, "claude", model="opus", effort="xhigh", extra=("--premium", "Owner approved premium", "--write", "--allow-shell"))
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
