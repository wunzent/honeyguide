from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re
from typing import Callable

from agent_loader import AgentTemplate
from adapters.base import (Availability, InvocationSpec, Outcome, Route,
                           _clean, _dicts, _epoch, _parse_line, scrub)
from state_writer import atomic_write_text


def _limited(node: dict) -> bool:
    return (any(node.get(key) is True for key in ("is_limited", "is_rate_limited", "limited", "reached"))
            or node.get("status") in {"rejected", "limited", "reached", "rate_limited"})


def _event_reset(event: dict, exhausted: bool) -> list[datetime]:
    stamp = event.get("timestamp", event.get("time"))
    event_time = _epoch(stamp)
    if event_time is None and isinstance(stamp, str):
        try:
            event_time = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if event_time.tzinfo is None:
                event_time = None
        except ValueError:
            pass
    resets = []
    def visit(node: dict, reached: bool) -> None:
        # A child's explicit window status takes precedence over its parent.
        marked = any(key in node for key in ("is_limited", "is_rate_limited", "limited", "reached", "status"))
        active = _limited(node) if marked else reached
        if active:
            for key in ("resetsAt", "resets_at"):
                reset = _epoch(node.get(key))
                if reset is not None and (event_time is None or reset >= event_time):
                    resets.append(reset)
        for key, value in node.items():
            if key in {"result", "usage", "message", "content"}:
                continue
            if isinstance(value, dict):
                visit(value, active if key == "error" else False)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, dict):
                        visit(child, False)
    visit(event, exhausted)
    return resets


class ClaudeAdapter:
    vendor = "claude"

    def __init__(self, executable: list[str] | None = None) -> None:
        self.executable = list(executable) if executable is not None else ["claude"]

    def build(self, template: AgentTemplate, route: Route, run_dir: Path,
              worktree: Path, prompt_path: Path,
              resume_session: str | None = None) -> InvocationSpec:
        if route.vendor != self.vendor:
            raise ValueError("Route vendor mismatch")
        settings = run_dir / "claude-settings.json"
        atomic_write_text(settings, json.dumps({"permissions": {
            "deny": ["Edit", "Write", "Bash", "PowerShell"]}}), retries=10, backoff=0.01)
        tools = tuple(tool for capability, names in (("read", ("Read",)), ("search", ("Glob", "Grep")))
                      if capability in template.capabilities for tool in names)
        if not tools:
            raise ValueError("Claude worker requires read or search capabilities")
        argv = self.executable + [
            "-p", "--output-format", "stream-json", "--verbose",
            "--model", route.model, "--effort", route.effort,
            "--append-system-prompt-file", str(prompt_path),
            "--tools", ",".join(tools), "--strict-mcp-config", "--disable-slash-commands",
            "--allowedTools", ",".join(tools), "--disallowedTools",
            "Bash,PowerShell,Edit,Write,NotebookEdit,Agent,Task,WebFetch,WebSearch",
            "--permission-mode", "default", "--settings", str(settings),
        ]
        if route.max_budget_usd is not None:
            argv += ["--max-budget-usd", str(route.max_budget_usd)]
        if resume_session is not None:
            argv += ["--resume", resume_session]
        return InvocationSpec(argv, worktree,
                              "Follow the system instructions. Work only inside the current directory.", {}, tools)

    def parse_line(self, line: str) -> dict | None:
        return _parse_line(line)

    def classify(self, exit_code: int, events: list[dict], stderr_tail: str) -> Outcome:
        events = _clean(events)
        nodes = list(_dicts(events))
        results = [event for event in events if event.get("type") == "result"]
        final = results[-1] if results else {}
        session = next((node["session_id"] for node in reversed(nodes) if "session_id" in node), None)
        errors = {key: final[key] for key in ("error", "errors", "subtype", "error_type")
                  if final.get("is_error") is True and key in final}
        rate_events = [event for event in events if event.get("type") in {"rate_limit_event", "rate_limit"}]
        limited = [event for event in rate_events if any(_limited(node) for node in _dicts(event))]
        text = scrub(json.dumps(errors) + "\n" + stderr_tail).replace("_", " ")
        # PENDING VERIFICATION (LIVE-A/LIVE-E): provider error wording and reset fields.
        if exit_code == 401 or re.search(r"\b(?:not logged in|login|authentication|401|invalid api key)\b", text, re.I):
            status = "auth_error"
        elif exit_code == 429 or limited or re.search(r"\b(?:usage limit|rate limit|429|quota)\b", text, re.I):
            status = "quota_limited"
        else:
            status = "ok" if exit_code == 0 and final and not final.get("is_error") else "failed"
        final_quota = (final.get("is_error") is True and bool(re.search(
            r"\b(?:usage limit|rate limit|429|quota)\b", json.dumps(errors).replace("_", " "), re.I)))
        resets = [reset for event in limited for reset in _event_reset(event, False)]
        if final_quota:
            resets += _event_reset(final, True)
        reset = min(resets) if status == "quota_limited" and resets else None
        result = final.get("result", "")
        usage = final.get("usage", {})
        return Outcome(status, session, reset, "claude-stream" if reset else None,
                       scrub(result) if isinstance(result, str) else "",
                       usage if isinstance(usage, dict) else {},
                       session_invalid=any(node.get("session_invalid") is True for node in nodes))

    def availability(self, run: Callable[[list[str]], tuple[int, str]]) -> Availability:
        try:
            code, version = run(self.executable + ["--version"])
            if code:
                return Availability(False, None, None, scrub(version))
            code, output = run(self.executable + ["auth", "status"])
            data = json.loads(output)
            logged_in = data.get("loggedIn") if isinstance(data, dict) else None
            logged_in = logged_in if isinstance(logged_in, bool) else None
            return Availability(code == 0 and logged_in is True, scrub(version.strip()),
                                logged_in, "" if code == 0 and logged_in else "Authentication unavailable")
        except (OSError, ValueError) as exc:
            return Availability(False, None, None, scrub(str(exc)))
