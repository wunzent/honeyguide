"""Offline Claude stream fixture; never launches another executable."""
import json
import os
from pathlib import Path
import sys
import time


def main() -> int:
    args = sys.argv[1:]
    if os.environ.get("FAKE_ARGV_LOG"):
        Path(os.environ["FAKE_ARGV_LOG"]).write_text(json.dumps(args), encoding="utf-8")
    if args == ["--version"]:
        print("fake-claude 1.0")
        return 0
    if args == ["auth", "status"]:
        print(json.dumps({"loggedIn": True}))
        return 0
    sys.stdin.read()
    scenario = os.environ.get("FAKE_SCENARIO", "ok")
    if scenario in {"unknown_option", "invalid_value", "invalid_argument"}:
        message = {
            "unknown_option": "unknown option '--setting-sources'",
            "invalid_value": "invalid value '' for '--setting-sources'",
            "invalid_argument": "error: option '--setting-sources <sources>' argument '' is invalid",
        }[scenario]
        print(message, file=sys.stderr)
        return 2
    if scenario == "slow":
        time.sleep(float(os.environ.get("FAKE_SLEEP", "30")))
    session = os.environ.get("FAKE_SESSION_ID", "claude-session")
    tools = ["Read", "Glob", "Grep"]
    servers = []
    if scenario == "extra_tools":
        tools += ["CronCreate", "SendMessage", "mcp__docs__create"]
    if scenario == "extra_mcp":
        servers = [{"name": "docs", "status": "connected"}]
    init = {"type": "system", "subtype": "init", "cwd": ".", "session_id": session,
            "tools": tools, "mcp_servers": servers, "model": "fake-model", "permissionMode": "default",
            "slash_commands": [], "terminal_slash_commands": [], "apiKeySource": "none",
            "claude_code_version": "2.1.312", "output_style": "default", "agents": ["fixture-agent"],
            "skills": [], "plugins": [], "capabilities": {}}
    for field in ("slash_commands", "terminal_slash_commands", "skills", "plugins"):
        if scenario == "extra_" + field:
            init[field] = [{"name": "fixture", "path": "./fixture"}] if field == "plugins" else ["fixture"]
    if scenario == "missing_key":
        del init["skills"]
    if scenario.startswith("missing_terminal"):
        del init["terminal_slash_commands"]
        if scenario == "missing_terminal_slash":
            init["slash_commands"] = ["fixture"]
        if scenario == "missing_terminal_skills":
            init["skills"] = ["fixture"]
    if scenario != "missing_init":
        print(json.dumps(init))
    if scenario in {"hook_started", "hook_response"}:
        print(json.dumps({"type": "system", "subtype": scenario,
                          "hook_name": "fixture-private-hook", "command": "fixture-private-command"}))
    failed = scenario in {"fail", "quota_reset", "quota_noreset", "auth"}
    result = {
        "fail": "Task failed", "quota_reset": "Usage limit reached",
        "quota_noreset": "Usage limit reached", "auth": "Not logged in: authentication required",
    }.get(scenario, "```diff\ndiff --git a/hello.txt b/hello.txt\nnew file mode 100644\n--- /dev/null\n+++ b/hello.txt\n@@ -0,0 +1 @@\n+hello\n```\nRESULT: {}")
    if scenario == "ask":
        question = {
            "title": "Choose greeting", "context": "The approved plan permits two greetings; see spec.md.",
            "impact": "Implementation waits; either choice has equal cost.",
            "options": [{"id": "a", "label": "Hello", "consequence": "Use hello"},
                        {"id": "b", "label": "Hi", "consequence": "Use hi"}],
            "default": "a", "blocking": True, "class": "relay", "type": "clarification",
            "asked_by": "coder",
        }
        result = "RESULT: " + json.dumps({"question_request": question})
    event = {"type": "result", "is_error": failed, "result": result,
             "session_id": session, "usage": {"input_tokens": 12, "output_tokens": 8}}
    if scenario == "quota_reset":
        event["resetsAt"] = 1900000000
    print(json.dumps(event))
    if scenario == "trailing_null_session":
        print(json.dumps({"type": "system", "subtype": "status", "session_id": None}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
