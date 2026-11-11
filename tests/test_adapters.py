from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from adapters import get_adapter
from adapters.base import Availability, InvalidResumeSession, InvocationSpec, Outcome, Route, scrub
from adapters.codex_cli import read_session_rate_limits
from agent_loader import load_all, render_prompt
import state_writer


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = load_all(ROOT / "agents")


@pytest.fixture(autouse=True)
def isolated_codex_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    monkeypatch.setattr("adapters.codex_cli.host_skills_root", lambda: tmp_path / "host-skills")


def _adapter(vendor):
    return get_adapter(vendor, [sys.executable, str(ROOT / "tests" / "fakes" / f"fake_{vendor}.py")])


def _build(tmp_path, vendor, role="coder", resume=None):
    template = TEMPLATES[role]
    prompt = tmp_path / "prompt.md"
    prompt.write_text(render_prompt(template, dict.fromkeys(template.inputs, "approved evidence")), encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    return _adapter(vendor).build(template, Route(vendor, "test-model", "medium", 0.5),
                                  run_dir, tmp_path, prompt, resume)


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("invalid", ["", "bad id", "short", "unsafe/id", "a" * 129, 42, False, []])
def test_build_refuses_invalid_resume(tmp_path, vendor, invalid):
    with pytest.raises(InvalidResumeSession, match="invalid resume session identifier"):
        _build(tmp_path, vendor, resume=invalid)


@pytest.mark.parametrize("vendor,field", [("claude", "session_id"), ("codex", "thread_id"),
                                         ("codex", "session_id")])
@pytest.mark.parametrize("invalid", [None, "", "bad id", 12, []])
@pytest.mark.parametrize("has_valid", [False, True])
def test_session_selection_keeps_last_valid(vendor, field, invalid, has_valid):
    adapter = _adapter(vendor)
    events = ([{field: "first-session"}, {field: "last-session"}] if has_valid else [])
    events.append({"nested": [{field: invalid}]})
    parsed = [adapter.parse_line(json.dumps(event)) for event in events]
    outcome = adapter.classify(1, parsed, "")
    assert outcome.session_id == ("last-session" if has_valid else None)
    assert outcome.session_invalid


@pytest.mark.parametrize("vendor,field", [("claude", "session_id"), ("codex", "thread_id")])
def test_invalid_marker_cannot_be_overwritten(vendor, field):
    adapter = _adapter(vendor)
    parsed = adapter.parse_line(json.dumps({field: None, "session_invalid": False}))
    assert adapter.classify(1, [parsed], "").session_invalid


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("role", list(TEMPLATES))
@pytest.mark.parametrize("resume", [None, "previous-session"])
def test_build(tmp_path, vendor, role, resume):
    spec = _build(tmp_path, vendor, role, resume)
    assert isinstance(spec, InvocationSpec)
    assert spec.cwd == tmp_path
    assert spec.env == ({"CODEX_HOME": str((tmp_path / "codex-home").resolve())} if vendor == "codex" else {})
    assert spec.argv[:2] == _adapter(vendor).executable
    if vendor == "claude":
        assert spec.argv[2:7] == ["-p", "--output-format", "stream-json", "--verbose", "--model"]
        assert spec.argv[spec.argv.index("--model") + 1] == "test-model"
        assert spec.argv[spec.argv.index("--effort") + 1] == "medium"
        assert spec.argv[spec.argv.index("--allowedTools") + 1].split(",") == ["Read", "Glob", "Grep"]
        deny = spec.argv[spec.argv.index("--disallowedTools") + 1].split(",")
        assert set(deny) == {"Bash", "PowerShell", "Edit", "Write", "NotebookEdit", "Agent", "Task", "WebFetch", "WebSearch"}
        settings = Path(spec.argv[spec.argv.index("--settings") + 1])
        data = json.loads(settings.read_text())
        assert set(data["permissions"]["deny"]) == set(deny)
        assert data["disableAllHooks"] is True and data["enableAllProjectMcpServers"] is False
        from adapters.claude_cli import CLAUDE_DISABLED_BUILTIN_PLUGINS
        disabled_plugins = {
            "cc-plugin-agents-md@builtin": False,
            "cc-plugin-telemetry@builtin": False,
            "cc-plugin-plugin-authoring@builtin": False,
        }
        assert CLAUDE_DISABLED_BUILTIN_PLUGINS == tuple(disabled_plugins)
        assert data == {
            "disableAllHooks": True, "enableAllProjectMcpServers": False,
            "permissions": {"deny": ["Edit", "Write", "Bash", "PowerShell", "NotebookEdit",
                                     "WebFetch", "WebSearch", "Agent", "Task"]},
            "enabledPlugins": disabled_plugins,
        }
        assert settings == tmp_path / "run" / "claude-settings.json"
        from adapters.claude_cli import CLAUDE_SETTING_SOURCES
        assert spec.argv[spec.argv.index("--setting-sources") + 1] == CLAUDE_SETTING_SOURCES == ""
        assert spec.argv[spec.argv.index("--max-budget-usd") + 1] == "0.5"
        assert spec.argv[spec.argv.index("--permission-mode") + 1] == "default"
        assert spec.argv[2:] == [
            "-p", "--output-format", "stream-json", "--verbose",
            "--model", "test-model", "--effort", "medium",
            "--append-system-prompt-file", str(tmp_path / "prompt.md"),
            "--tools", "Read,Glob,Grep", "--strict-mcp-config", "--disable-slash-commands",
            "--allowedTools", "Read,Glob,Grep", "--disallowedTools",
            "Bash,PowerShell,Edit,Write,NotebookEdit,Agent,Task,WebFetch,WebSearch",
            "--permission-mode", "default", "--setting-sources", "", "--settings", str(settings),
            "--max-budget-usd", "0.5",
        ] + (["--resume", resume] if resume else [])
        assert spec.stdin_text == "Follow the system instructions. Work only inside the current directory."
        if resume:
            assert spec.argv[-2:] == ["--resume", resume]
    else:
        assert spec.argv[2:3] == ["exec"]
        if resume:
            assert spec.argv[3:5] == ["resume", resume]
        assert spec.argv[spec.argv.index("-C") + 1] == str(tmp_path)
        assert spec.argv[spec.argv.index("-s") + 1] == ("read-only" if TEMPLATES[role].writes == "none" else "workspace-write")
        assert spec.argv[spec.argv.index("-m") + 1] == "test-model"
        assert ["-c", "features.multi_agent=false"] == spec.argv[-5:-3]
        assert "model_reasoning_effort=medium" in spec.argv
        assert spec.argv[-1] == "-"


@pytest.mark.parametrize("role", list(TEMPLATES))
def test_prompt_parity(tmp_path, role):
    claude = _build(tmp_path, "claude", role)
    codex = _build(tmp_path, "codex", role)
    prompt = Path(claude.argv[claude.argv.index("--append-system-prompt-file") + 1]).read_text(encoding="utf-8")
    assert sha256(prompt.encode()).digest() == sha256(codex.stdin_text.encode()).digest()
    assert prompt.startswith(TEMPLATES[role].body)
    assert sha256(prompt[:len(TEMPLATES[role].body)].encode()).hexdigest() == TEMPLATES[role].body_sha256


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("scenario,status", [
    ("ok", "ok"), ("fail", "failed"), ("quota_reset", "quota_limited"),
    ("quota_noreset", "quota_limited"), ("auth", "auth_error"),
    ("slow", "ok"), ("ask", "ok"),
])
def test_fake_scenarios(tmp_path, vendor, scenario, status):
    adapter = _adapter(vendor)
    spec = _build(tmp_path, vendor)
    log = tmp_path / "argv.json"
    env = os.environ.copy()
    env.update(spec.env | {"FAKE_SCENARIO": scenario, "FAKE_SLEEP": "0.01", "FAKE_ARGV_LOG": str(log)})
    completed = subprocess.run(spec.argv, input=spec.stdin_text, text=True, encoding="utf-8",
                               cwd=spec.cwd, env=env, capture_output=True, timeout=10)
    events = [event for line in completed.stdout.splitlines() if (event := adapter.parse_line(line)) is not None]
    if vendor == 'claude':
        for event in events:
            if event.get('type') == 'result' and event.get('is_error') is True:
                event['error'] = {'message': event['result']}
    outcome = adapter.classify(completed.returncode, events, completed.stderr)
    assert isinstance(outcome, Outcome)
    assert outcome.status == status
    assert outcome.session_id == ("claude-session" if vendor == "claude" else "codex-thread")
    assert outcome.reset_at == (datetime.fromtimestamp(1900000000, timezone.utc) if scenario == "quota_reset" else None)
    assert outcome.reset_source == (f"{vendor}-stream" if scenario == "quota_reset" else None)
    assert json.loads(log.read_text()) == spec.argv[2:]
    assert not (tmp_path / "hello.txt").exists()
    if scenario in {"ok", "slow"}:
        assert "```diff" in outcome.result_text
        assert outcome.usage == {"input_tokens": 12, "output_tokens": 8}
    if scenario == "ask":
        question = json.loads(outcome.result_text.split("RESULT: ", 1)[1])["question_request"]
        assert {"title", "context", "impact", "options", "default", "blocking", "class", "asked_by"} <= question.keys()
        assert 2 <= len(question["options"]) <= 4
    if vendor == "codex":
        assert (tmp_path / "run" / "last.md").is_file()
        if status == "ok":
            assert (tmp_path / "run" / "last.md").read_text() == outcome.result_text


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_parse_and_scrub(vendor):
    adapter = _adapter(vendor)
    for line in ["", "not json", "[]", "null", "42", '{"broken":']:
        assert adapter.parse_line(line) is None
    tokens = ["sk-throwaway-secret", "Bearer throwaway", "a" * 64, "QWxhZGRpbjpvcGVuIHNlc2FtZXRlc3R0b2tlbg=="]
    for token in tokens:
        assert token not in scrub(token)
        assert token not in scrub("token=" + token)
        event = adapter.parse_line(json.dumps({"text": token, "nested": [{"key": token}]}))
        assert token not in json.dumps(event)
        outcome = adapter.classify(0, [{"type": "result", "result": token},
                                      {"type": "item.completed", "item": {"type": "agent_message", "text": token}},
                                      {"type": "turn.completed", "usage": {"secret": token}}], "")
        assert token not in repr(outcome)
    assert scrub("ordinary text Read,Glob,Grep 1900000000") == "ordinary text Read,Glob,Grep 1900000000"


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("logged_in", [True, False])
def test_availability(vendor, logged_in):
    adapter = _adapter(vendor)
    calls = []

    def run(argv):
        calls.append(argv)
        if argv[-1] == "--version":
            return 0, "fake-version\n"
        if vendor == "claude":
            return 0, json.dumps({"loggedIn": logged_in})
        return (0, "Logged in with test account") if logged_in else (1, "Not logged in")

    result = adapter.availability(run)
    assert isinstance(result, Availability)
    assert result.ok is logged_in and result.logged_in is logged_in
    assert result.version == "fake-version"
    assert calls == [adapter.executable + ["--version"], adapter.executable + (["auth", "status"] if vendor == "claude" else ["login", "status"])]


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_availability_failure(vendor):
    adapter = _adapter(vendor)
    assert not adapter.availability(lambda _: (1, "missing sk-throwaway")).ok
    assert "sk-throwaway" not in adapter.availability(lambda _: (1, "missing sk-throwaway")).reason

    def denied(argv):
        raise PermissionError("denied")

    assert not adapter.availability(denied).ok
    if vendor == "claude":
        responses = iter([(0, "version"), (0, "not json")])
        assert not adapter.availability(lambda _: next(responses)).ok
    else:
        responses = iter([(0, "version"), (0, "Not logged in")])
        assert not adapter.availability(lambda _: next(responses)).ok


def test_read_sessions(tmp_path, monkeypatch):
    assert read_session_rate_limits(tmp_path) is None
    nested = tmp_path / "2026" / "11"
    nested.mkdir(parents=True)
    old = tmp_path / "old.jsonl"
    old.write_text(json.dumps({"rate_limits": {"primary": {"resets_at": 1}}}), encoding="utf-8")
    newest = nested / "new.jsonl"
    limits = {"primary": {"used_percent": 100, "resets_at": 1900000000}}
    newest.write_text('\n'.join([json.dumps({"rate_limits": {"primary": {"resets_at": 2}}}),
                                   json.dumps({"payload": {"rate_limits": limits}}), "broken rate_limits", '{}']), encoding="utf-8")
    os.utime(old, ns=(1, 1))
    before = newest.read_bytes()
    assert read_session_rate_limits(tmp_path) == limits
    assert newest.read_bytes() == before
    newest.write_text("no limits\n", encoding="utf-8")
    assert read_session_rate_limits(tmp_path) is None

    def denied(path):
        raise PermissionError("denied")

    monkeypatch.setattr("adapters.codex_cli.read_text_retry", denied)
    assert read_session_rate_limits(tmp_path) is None


@pytest.mark.parametrize("reached,primary,secondary,expected", [
    ("primary", 200, 100, 200), ("secondary", 100, 200, 200),
    ("unknown", 200, 100, 100), (None, 200, 100, 100),
    ("primary", None, 100, None),
])
def test_reached_window(reached, primary, secondary, expected):
    limits = {"rate_limit_reached_type": reached,
              "primary": {"used_percent": 100, "resets_at": primary},
              "secondary": {"used_percent": 100, "resets_at": secondary}}
    result = _adapter("codex").classify(1, [{"rate_limits": limits}], "usage limit")
    assert result.reset_at == (datetime.fromtimestamp(expected, timezone.utc) if expected is not None else None)


@pytest.mark.parametrize("vendor", ["claude", "codex"])
@pytest.mark.parametrize("epoch", [None, "1900000000", True, float("nan"), float("inf"), 10**100])
def test_invalid_reset_never_guessed(vendor, epoch):
    event = {"resets_at": epoch, "rate_limits": {"primary": {"used_percent": 100, "resets_at": epoch}}}
    outcome = _adapter(vendor).classify(1, [event], "usage limit")
    assert outcome.status == "quota_limited" and outcome.reset_at is None and outcome.reset_source is None


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_classify_requires_completion_and_preserves_authority_boundary(vendor):
    adapter = _adapter(vendor)
    assert adapter.classify(0, [], "").status == "failed"
    assert adapter.classify(1, [{"type": "result"}, {"type": "turn.completed"}], "").status == "failed"
    outcome = adapter.classify(0, [{"type": "result", "is_error": True, "result": "APPROVED"}], "")
    assert outcome.status == "failed"
    assert adapter.classify(1, [], "401").status == ("failed" if vendor == "codex" else "auth_error")
    assert adapter.classify(1, [], "429 rate limit").status == "quota_limited"
    assert adapter.classify(0, [{"type": "session_configured", "session_id": "resume-id"}], "").session_id == "resume-id"


def test_registry_and_default_resolution(monkeypatch, tmp_path):
    with pytest.raises(ValueError):
        get_adapter("unknown")
    with pytest.raises(ValueError):
        get_adapter("codex", [])
    assert get_adapter("claude").executable == ["claude"]
    calls = []

    def which(name):
        calls.append(name)
        return str(tmp_path / ("codex.cmd" if name == "codex.cmd" else "codex"))

    monkeypatch.setattr("adapters.codex_cli.shutil.which", which)
    adapter = get_adapter("codex")
    assert adapter.executable == [str(tmp_path / ("codex.cmd" if os.name == "nt" else "codex"))]
    assert calls[0] == ("codex.cmd" if os.name == "nt" else "codex")
    monkeypatch.setattr("adapters.codex_cli.shutil.which", lambda _: str(tmp_path / "codex.ps1"))
    assert get_adapter("codex").executable == ["codex"]


def test_settings_atomic_permission_retry(tmp_path, monkeypatch):
    original = state_writer.os.replace
    calls = 0

    def replace(source, dest):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("busy")
        original(source, dest)

    monkeypatch.setattr(state_writer.os, "replace", replace)
    monkeypatch.setattr(state_writer.time, "sleep", lambda _: None)
    _build(tmp_path, "claude")
    assert calls == 2


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_route_vendor_mismatch(tmp_path, vendor):
    with pytest.raises(ValueError, match="vendor"):
        _adapter(vendor).build(TEMPLATES["coder"], Route("other", "model", "medium"),
                               tmp_path, tmp_path, tmp_path / "missing.md")


def test_claude_optional_budget_omitted(tmp_path):
    spec = _adapter("claude").build(TEMPLATES["coder"], Route("claude", "model", "medium"),
                                     tmp_path, tmp_path, tmp_path / "prompt.md")
    assert "--max-budget-usd" not in spec.argv and "--resume" not in spec.argv


def test_codex_unknown_window_requires_exhaustion():
    limits = {"rate_limit_reached_type": "unknown", "primary": {"used_percent": 99, "resets_at": 100},
              "secondary": {"used_percent": 100, "resets_at": 200}}
    outcome = _adapter("codex").classify(1, [{"rate_limits": limits}], "")
    assert outcome.status == "quota_limited"
    assert outcome.reset_at == datetime.fromtimestamp(200, timezone.utc)


def test_claude_snake_case_nested_reset():
    outcome = _adapter("claude").classify(1, [{"type": "result", "is_error": True,
                                              "error": {"message": "quota", "resets_at": 200}}], "")
    assert outcome.reset_at == datetime.fromtimestamp(200, timezone.utc)
    assert outcome.reset_source == "claude-stream"


@pytest.mark.parametrize("vendor", ["codex", "claude"])
@pytest.mark.parametrize("text", ["Added login form validation", "Reviewed the authentication module: PASS",
                                  "quota 401 429 usage limit rate limit", "14012 4290"])
def test_transcript_text_is_not_provider_error(vendor, text):
    events = [{"type": "item.completed", "item": {"type": "agent_message", "text": text}},
              {"type": "item.completed", "item": {"type": "command_execution", "aggregated_output": text}},
              {"type": "turn.completed", "usage": {"input_tokens": 14012, "output_tokens": 4290}},
              {"type": "result", "is_error": False, "result": text,
               "usage": {"input_tokens": 14012, "output_tokens": 4290}}]
    assert _adapter(vendor).classify(0, events, "").status == "ok"


@pytest.mark.parametrize("vendor", ["codex", "claude"])
def test_error_numbers_are_word_bounded(vendor):
    events = [{"type": "turn.completed"}, {"type": "result", "is_error": False}]
    assert _adapter(vendor).classify(0, events, "usage 14012 4290").status == "ok"


@pytest.mark.parametrize("events,expected", [
    ([{"type": "error", "status": 401, "message": "authentication required"}], "auth_error"),
    ([{"type": "turn.failed", "error": {"message": "429 rate limit"}}], "quota_limited"),
])
def test_codex_structured_errors(events, expected):
    assert _adapter("codex").classify(1, events, "").status == expected


@pytest.mark.parametrize("error,expected", [("authentication_error", "auth_error"),
                                           ("rate_limit_error", "quota_limited")])
def test_claude_final_error_fields(error, expected):
    event = {"type": "result", "is_error": True, "subtype": error, "result": "untrusted prose"}
    assert _adapter("claude").classify(1, [event], "").status == expected


@pytest.mark.parametrize("limited,reset", [(False, 300), (True, 90), (True, 250)])
def test_claude_reset_only_reached_future_window(limited, reset):
    event = {"type": "rate_limit_event", "timestamp": 100,
             "windows": [{"is_limited": False, "resetsAt": 110},
                         {"is_limited": True, "resetsAt": 80},
                         {"is_limited": limited, "resetsAt": reset}]}
    outcome = _adapter("claude").classify(1, [event], "quota")
    assert outcome.reset_at == (datetime.fromtimestamp(reset, timezone.utc) if limited and reset >= 100 else None)


def test_claude_success_reset_and_error_result_prose_ignored():
    outcome = _adapter("claude").classify(1, [{"type": "result", "is_error": True,
        "result": "quota 401", "resetsAt": 500}], "")
    assert outcome.status == "failed" and outcome.reset_at is None


@pytest.mark.parametrize('warning', [
    'login shell not detected', 'line 401 of file', 'deprecated --login flag',
    'authentication module loaded', '4012 Unauthorized', 'not logged inside'])
def test_codex_auth_warning_is_not_auth_error(warning):
    adapter = _adapter('codex')
    assert adapter.classify(0, [{'type': 'turn.completed'}], warning).status == 'ok'
    assert adapter.classify(1, [{'type': 'error', 'message': warning}], '').status == 'failed'


@pytest.mark.parametrize('event', [
    {'type': 'error', 'status': 401},
    {'type': 'turn.failed', 'error': {'status_code': 401}},
    {'type': 'error', 'error': {'code': 'invalid_api_key'}},
    {'type': 'error', 'error': {'type': 'auth'}},
    {'type': 'error', 'code': 'unauthorized'},
    {'type': 'error', 'error': {'http_status': 401}},
])
def test_codex_structured_auth_fields(event):
    assert _adapter('codex').classify(1, [event], '').status == 'auth_error'


@pytest.mark.parametrize('message', [
    'Not logged in. Please run codex login', 'please run `codex login`',
    'run codex login', '401 Unauthorized', 'Authentication failed',
    'Invalid api key', 'Token expired'])
def test_codex_specific_auth_signatures(message):
    assert _adapter('codex').classify(1, [], message).status == 'auth_error'


def test_codex_exit_code_alone_is_not_auth():
    assert _adapter('codex').classify(401, [], '').status == 'failed'


@pytest.mark.parametrize("platform", ["nt", "posix"])
@pytest.mark.parametrize("resume", [None, "previous-session"])
def test_codex_full_isolated_argv(tmp_path, monkeypatch, platform, resume):
    from types import SimpleNamespace
    from adapters import codex_cli
    monkeypatch.setattr(codex_cli, "os", SimpleNamespace(name=platform, environ=os.environ))
    spec = _build(tmp_path, "codex", resume=resume)
    features = ("apps", "plugins", "remote_plugin", "hooks", "memories", "goals", "multi_agent",
                "browser_use", "browser_use_external", "in_app_browser", "computer_use",
                "skill_mcp_dependency_install")
    assert codex_cli.CODEX_DISABLED_FEATURES == features
    expected = ["exec"] + (["resume", resume] if resume else [])
    expected += ["--json", "-C", str(tmp_path), "-s", "workspace-write",
                 "--ignore-user-config", "--ignore-rules"]
    if platform == "nt":
        expected += ["-c", 'windows.sandbox="elevated"']
    expected += ["-c", "mcp_servers={}"]
    for feature in features:
        expected += ["--disable", feature]
    expected += ["-c", "skills.config=[]", "-m", "test-model", "-c", "model_reasoning_effort=medium",
                 "-c", "features.multi_agent=false", "-o", str(tmp_path / "run" / "last.md"), "-"]
    assert spec.argv[2:] == expected


def test_codex_skills_paths_only_sorted_and_deduplicated(tmp_path, monkeypatch):
    import tomllib
    from adapters.codex_cli import codex_home, skills_config
    home = codex_home()
    paths = [home / "skills" / ".system" / "z" / "SKILL.md",
             home / "skills" / "a" / "SKILL.md", tmp_path / "host-skills" / "b" / "SKILL.md"]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("must never be read", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw: pytest.fail("skill contents read"))
    parsed = tomllib.loads("skills=" + skills_config(home))["skills"]
    assert parsed == [{"path": p, "enabled": False} for p in sorted(p.resolve().as_posix() for p in paths)]
    monkeypatch.setattr("adapters.codex_cli.host_skills_root", lambda: home / "skills")
    parsed = tomllib.loads("skills=" + skills_config(home))["skills"]
    assert len(parsed) == 2


@pytest.mark.parametrize("bad", ['bad"path', "bad\npath", "bad\x7fpath"])
def test_codex_skill_path_rejected(tmp_path, monkeypatch, bad):
    from adapters.codex_cli import skills_config
    monkeypatch.setattr("adapters.codex_cli._skill_paths", lambda *a: [tmp_path / bad / "SKILL.md"])
    with pytest.raises(ValueError, match="unsafe Codex skill path"):
        skills_config(tmp_path / "codex-home")


def test_codex_prompt_cannot_change_argv(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text('--dangerously-bypass-approvals-and-sandbox -c sandbox_mode=danger-full-access --ignore-user-config=false', encoding="utf-8")
    adapter = _adapter("codex")
    spec = adapter.build(TEMPLATES["coder"], Route("codex", "test-model", "medium"), tmp_path / "run", tmp_path, prompt)
    assert "danger-full-access" in spec.stdin_text
    assert all("danger" not in arg and "--ignore-user-config=false" not in arg for arg in spec.argv)
    assert spec.argv == _build(tmp_path, "codex").argv


@pytest.mark.parametrize("stderr", ["unknown option foo", "unrecognized argument foo", "unexpected argument foo", "invalid value foo", "invalid config foo"])
@pytest.mark.parametrize("successful", [False, True])
def test_codex_unsupported_classification(stderr, successful):
    events = [{"type": "turn.completed"}] if successful else []
    outcome = _adapter("codex").classify(0 if successful else 2, events, stderr)
    assert outcome.reason == (None if successful else "codex_isolation_unsupported")
    assert outcome.status == ("ok" if successful else "failed")



def test_codex_home_defaults_without_reading_owner(tmp_path, monkeypatch):
    from adapters.codex_cli import codex_home
    monkeypatch.delenv("CODEX_HOME")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert codex_home() == tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "explicit"))
    assert codex_home() == tmp_path / "explicit"


def test_codex_final_message_prevents_unsupported_classification():
    outcome = _adapter("codex").classify(1, [{"type": "item.completed", "item": {
        "type": "agent_message", "text": "Final response"}}], "unexpected argument quoted by agent")
    assert outcome.reason is None



def test_codex_skill_discovery_access_failure_is_closed(tmp_path, monkeypatch):
    from adapters.codex_cli import skills_config
    root = tmp_path / "codex-home" / "skills"
    root.mkdir(parents=True)
    def denied(root, onerror):
        onerror(PermissionError("unreadable skills"))
    monkeypatch.setattr("adapters.codex_cli.os.walk", denied)
    with pytest.raises(PermissionError):
        skills_config(tmp_path / "codex-home")
