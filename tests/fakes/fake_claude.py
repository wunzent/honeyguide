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
    if scenario == "slow":
        time.sleep(float(os.environ.get("FAKE_SLEEP", "30")))
    session = os.environ.get("FAKE_SESSION_ID", "claude-session")
    tools = ["Read", "Glob", "Grep"]
    servers = []
    if scenario == "extra_tools":
        tools += ["CronCreate", "SendMessage", "mcp__docs__create"]
    if scenario == "extra_mcp":
        servers = [{"name": "docs", "status": "connected"}]
    if scenario != "missing_init":
        print(json.dumps({"type": "system", "subtype": "init", "session_id": session,
                          "tools": tools, "mcp_servers": servers}))
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
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
