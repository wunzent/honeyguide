from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from dataclasses import replace

import pytest

import delegation
from adapters.base import Route
from model_router import RouteError, default_effort
from test_model_router import engine_env, hub, target, runtime, tier_block, spec


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/Scripts/python.exe"


def request(**changes):
    values = dict(role="coder", tier="routine", vendor="codex", model="gpt-6.1-sol",
                  effort="low", reason="Implement the approved step")
    values.update(changes)
    return values


def cli(*args):
    return subprocess.run([str(PYTHON), "-B", str(ROOT / "delegation.py"), *args],
                          capture_output=True, text=True, cwd=ROOT)


@pytest.mark.parametrize("tier,effort", [("routine", "low"), ("complex", "high")])
def test_valid_routes(tier, effort):
    args = request(tier=tier, effort=effort)
    result = cli("check", *[part for k, v in args.items() for part in ("--" + k, v)])
    assert result.returncode == 0, result.stdout + result.stderr
    route = json.loads(result.stdout)
    assert route["effort"] == route["default_effort"] == effort


@pytest.mark.parametrize("tier", ["routine", "standard", "complex"])
@pytest.mark.parametrize("role", ["coder", "tester", "doc-keeper"])
def test_hub_default_parity(engine_env, tier, role):
    factory, store, *_ = engine_env
    store.write_spec("project", "T-1", spec(tier_block(tier)))
    engine = factory()
    route, _ = engine._route(role, {}, set(), project="project", task="T-1")
    expected = default_effort(engine.policy, role, tier)
    desktop = delegation.check(**request(role=role, tier=tier, effort=expected))
    assert desktop["default_effort"] == route.effort == expected


@pytest.mark.parametrize("changes,match", [
    ({"model": "gpt-6-luna"}, "live-verified"),
    ({"vendor": "claude", "model": "opus"}, "premium"),
    ({"effort": "xhigh"}, "premium"),
    ({"model": "unknown"}, "not allowed"),
    ({"effort": "medium"}, "escalation"),
    ({"effort": "xhigh", "escalation": "Hard debugging requires this"}, "premium"),
    ({"tier": "complex"}, "below default"),
    ({"reason": "short"}, "reason"),
])
def test_refusals(changes, match):
    with pytest.raises(RouteError, match=match):
        delegation.check(**request(**changes))


def test_disallowed_vendor(monkeypatch):
    policy = delegation.load_policy(ROOT)
    roles = {k: dict(v) for k, v in policy.routing_roles.items()}
    roles["coder"]["allowed_vendors"] = ["claude"]
    monkeypatch.setattr(delegation, "load_policy", lambda root: replace(policy, routing_roles=roles))
    with pytest.raises(RouteError, match="not allowed"):
        delegation.check(**request())


def test_routine_only_verified_model(monkeypatch):
    catalog = delegation.load_catalog(ROOT / "config/models.toml")
    catalog["codex"]["unverified_models"] = []
    monkeypatch.setattr(delegation, "load_catalog", lambda path: catalog)
    assert delegation.check(**request(model="gpt-6-luna"))["effort"] == "low"
    with pytest.raises(RouteError, match="routine-only"):
        delegation.check(**request(model="gpt-6-luna", tier="standard", effort="medium"))


def test_escalation_and_no_substitution(monkeypatch):
    assert delegation.check(**request(effort="high", escalation="Complex debugging evidence"))["effort"] == "high"
    for result in [(Route("codex", "gpt-6.1-sol", "medium"), []),
                   (Route("codex", "gpt-6.1-sol", "low"), ["routing reason"])]:
        monkeypatch.setattr(delegation, "resolve", lambda *a, **k: result)
        with pytest.raises(RouteError, match="substitution"):
            delegation.check(**request())


def write_jsonl(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item) + "\n" for item in items), encoding="utf-8")


def test_verify_codex(tmp_path):
    events = tmp_path / "step.jsonl"
    sessions = tmp_path / "sessions"
    write_jsonl(events, [{"type": "thread.started", "thread_id": "fixture-thread"},
                        {"type": "thread.started", "thread_id": "ignored"}])
    assert delegation.verify_codex(events, sessions) == dict(thread="fixture-thread", actual_model=None,
        actual_effort=None, total_tokens=None, evidence=None)
    rollout = sessions / "nested/rollout-2026-fixture-thread.jsonl"
    write_jsonl(rollout, [
        {"type": "turn_context", "payload": {"model": "gpt-6.1-sol", "effort": "high"}},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"total_tokens": 20}}}},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"total_tokens": 31}}}},
    ])
    result = cli("verify-codex", "--events", str(events), "--sessions-dir", str(sessions))
    assert result.returncode == 0
    assert json.loads(result.stdout) == dict(thread="fixture-thread", actual_model="gpt-6.1-sol",
        actual_effort="high", total_tokens=31, evidence=str(rollout))
    write_jsonl(events, [])
    assert delegation.verify_codex(events, sessions)["thread"] is None


def test_verify_claude_and_record(tmp_path):
    transcript = tmp_path / "claude.jsonl"
    write_jsonl(transcript, [
        {"type": "assistant", "message": {"model": model}} for model in ["sonnet", "opus", "sonnet"]
    ] + [{"type": "user", "message": {"model": "ignored"}}])
    result = cli("verify-claude", "--transcript", str(transcript))
    assert json.loads(result.stdout) == {"actual_models": ["opus", "sonnet"]}
    log = tmp_path / "logs/delegations.jsonl"
    for n in range(2):
        result = cli("record", "--json", json.dumps({"number": n}), "--log", str(log))
        assert result.returncode == 0
    entries = list(delegation.json_lines(log))
    assert [e["number"] for e in entries] == [0, 1]
    assert all(e["at"].endswith("+00:00") for e in entries)


@pytest.mark.skipif(shutil.which("pwsh") is None or os.name != "nt", reason="requires Windows pwsh and codex.cmd")
@pytest.mark.parametrize("refused", [False, True])
def test_launcher(tmp_path, refused):
    brief = tmp_path / "step.txt"
    brief.write_text("Implement the fixture step.", encoding="utf-8")
    fake = tmp_path / "codex.cmd"
    fake.write_text('@echo off\n"' + str(PYTHON) + '" -B "' + str(ROOT / "tests/fakes/fake_codex.py") + '" %*\n', encoding="utf-8")
    argv_log = tmp_path / "argv.json"
    log = tmp_path / "delegations.jsonl"
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               FAKE_ARGV_LOG=str(argv_log), FAKE_SCENARIO="ok")
    model = "gpt-6-luna" if refused else "gpt-6.1-sol"
    result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(ROOT / "tools/run-codex-step.ps1"),
        "-Brief", str(brief), "-Role", "coder", "-Tier", "routine", "-Model", model,
        "-Effort", "low", "-Reason", "Implement the approved step", "-Repo", str(tmp_path),
        "-OutDir", str(tmp_path), "-SessionsDir", str(tmp_path / "sessions"), "-Log", str(log)],
        env=env, capture_output=True, text=True)
    assert result.returncode == (2 if refused else 3), result.stdout + result.stderr
    if refused:
        assert not argv_log.exists()
        assert not log.exists() or not any(e["type"] == "delegation.start" for e in delegation.json_lines(log))
    else:
        args = json.loads(argv_log.read_text(encoding="utf-8"))
        assert args.count("-m") == 1
        assert args[args.index("-m") + 1] == model
        assert args.count("model_reasoning_effort=low") == 1
        records = list(delegation.json_lines(log))
        assert records[0]["route"]["model"] == model
        assert records[0]["route"]["effort"] == "low"
        assert records[1]["requested_model"] == model
        assert records[1]["requested_effort"] == "low"
        assert records[1]["route_matches"] is False
        assert records[1]["exit_code"] == 0
