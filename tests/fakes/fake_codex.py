"""Offline Codex stream fixture; never launches another executable."""
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
        print("fake-codex 1.0")
        return 0
    if args == ["login", "status"]:
        print("Logged in using fake credentials")
        return 0
    sys.stdin.read()
    scenario = os.environ.get("FAKE_SCENARIO", "ok")
    if scenario == "slow":
        time.sleep(float(os.environ.get("FAKE_SLEEP", "30")))
    print(json.dumps({"type": "thread.started", "thread_id": "codex-thread"}))
    failed = scenario in {"fail", "quota_reset", "quota_noreset", "auth"}
    if failed:
        message = {"fail": "Task failed", "auth": "Not logged in: login required"}.get(scenario, "Usage limit reached")
        event = {"type": "turn.failed", "error": {"message": message}}
        if scenario.startswith("quota"):
            event["rate_limits"] = {"rate_limit_reached_type": "primary", "primary": {"used_percent": 100}}
            if scenario == "quota_reset":
                event["rate_limits"]["primary"]["resets_at"] = 1900000000
        print(json.dumps(event))
        result = message
    else:
        result = "```diff\ndiff --git a/hello.txt b/hello.txt\nnew file mode 100644\n--- /dev/null\n+++ b/hello.txt\n@@ -0,0 +1 @@\n+hello\n```\nRESULT: {}"
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
        print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": result}}))
        print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 8}}))
    if "-o" in args:
        Path(args[args.index("-o") + 1]).write_text(result, encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
