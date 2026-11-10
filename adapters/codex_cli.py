from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
import re
import shutil
from typing import Callable

from agent_loader import AgentTemplate
from adapters.base import (Availability, InvocationSpec, Outcome, Route,
                           _clean, _dicts, _epoch, _parse_line, scrub)
from state_writer import read_text_retry


def read_session_rate_limits(sessions_dir: Path) -> dict | None:
    try:
        paths = sorted(sessions_dir.rglob("*.jsonl"),
                       key=lambda path: (path.stat().st_mtime_ns, str(path)), reverse=True)
        if not paths:
            return None
        for line in reversed(read_text_retry(paths[0]).splitlines()):
            event = _parse_line(line)
            if event is not None:
                for node in _dicts(event):
                    if isinstance(node.get("rate_limits"), dict):
                        return node["rate_limits"]
    except (OSError, UnicodeError):
        return None
    return None


def _reset(limits: dict) -> datetime | None:
    reached = limits.get("rate_limit_reached_type")
    if reached in ("primary", "secondary"):
        window = limits.get(reached)
        return _epoch(window.get("resets_at")) if isinstance(window, dict) else None
    resets = []
    for window in limits.values():
        if not isinstance(window, dict):
            continue
        used = window.get("used_percent")
        if isinstance(used, (int, float)) and not isinstance(used, bool) and used >= 100:
            reset = _epoch(window.get("resets_at"))
            if reset is not None:
                resets.append(reset)
    return min(resets) if resets else None


class CodexAdapter:
    vendor = "codex"

    def __init__(self, executable: list[str] | None = None) -> None:
        self.launcher_note = None
        if executable is None:
            command = (shutil.which("codex.cmd") if os.name == "nt" else None) or shutil.which("codex")
            if command and Path(command).suffix.lower() == ".ps1":
                command = None
            self.executable = [command or "codex"]
            if command and Path(command).suffix.lower() == ".cmd":
                script = Path(command).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
                try:
                    wrapper = read_text_retry(Path(command)).replace("\\", "/").lower()
                    node = shutil.which("node")
                    if "node_modules/@openai/codex/bin/codex.js" in wrapper and script.is_file() and node:
                        self.executable = [str(Path(node).resolve()), str(script.resolve())]
                    else:
                        self.launcher_note = "codex.cmd fallback: Node or codex.js target unresolved"
                except (OSError, UnicodeError):
                    self.launcher_note = "codex.cmd fallback: launcher could not be read"
        else:
            self.executable = list(executable)

    def build(self, template: AgentTemplate, route: Route, run_dir: Path,
              worktree: Path, prompt_path: Path,
              resume_session: str | None = None) -> InvocationSpec:
        if route.vendor != self.vendor:
            raise ValueError("Route vendor mismatch")
        argv = self.executable + ["exec"]
        if resume_session is not None:
            argv += ["resume", resume_session]
        argv += ["--json", "-C", str(worktree), "-s",
                 "read-only" if template.writes == "none" else "workspace-write",
                 "-m", route.model, "-c", f"model_reasoning_effort={route.effort}",
                 "-c", "features.multi_agent=false", "-o", str(run_dir / "last.md"), "-"]
        return InvocationSpec(argv, worktree, read_text_retry(prompt_path), {}, launcher_note=self.launcher_note)

    def parse_line(self, line: str) -> dict | None:
        return _parse_line(line)

    def classify(self, exit_code: int, events: list[dict], stderr_tail: str) -> Outcome:
        events = _clean(events)
        nodes = list(_dicts(events))
        session = next((node[key] for node in reversed(nodes) for key in ("thread_id", "session_id")
                        if key in node), None)
        # Item payloads contain arbitrary agent prose and command output.
        protocol = [event for event in events if event.get("type") not in
                    {"item.started", "item.updated", "item.completed", "agent_message", "command_execution"}]
        limits = [event["rate_limits"] for event in protocol if isinstance(event.get("rate_limits"), dict)]
        errors = [{key: event[key] for key in ("message", "error", "code", "status", "status_code", "http_status") if key in event}
                  for event in events if event.get("type") in {"error", "turn.failed"}]
        text = scrub(json.dumps(errors) + "\n" + stderr_tail)
        auth_codes = {"unauthorized", "auth", "auth_error", "authentication_error", "invalid_api_key"}
        structured_auth = any(
            (key in {"code", "type"} and isinstance(value, str) and value.lower() in auth_codes)
            or (key in {"code", "status", "status_code", "http_status"}
                and type(value) is int and value == 401)
            for node in _dicts(errors) for key, value in node.items()
        )
        quota = any(limit.get("rate_limit_reached_type") is not None for limit in limits)
        if structured_auth or re.search(
            r"\b(?:not logged in|(?:please )?run `?codex login`?|401 Unauthorized|authentication failed|invalid api key|token expired)\b",
            text, re.I,
        ):
            status = "auth_error"
        elif exit_code == 429 or quota or re.search(r"\b(?:usage limit|rate limit|quota|429)\b", text.replace("_", " "), re.I):
            status = "quota_limited"
        else:
            completed = any(event.get("type") in ("turn.completed", "turn_completed") for event in events)
            status = "ok" if exit_code == 0 and completed else "failed"
        resets = [reset for limit in limits if (reset := _reset(limit)) is not None]
        reset = min(resets) if status == "quota_limited" and resets else None
        messages = [node["text"] for node in nodes
                    if node.get("type") == "agent_message" and isinstance(node.get("text"), str)]
        usage = next((node["usage"] for node in reversed(nodes) if isinstance(node.get("usage"), dict)), {})
        return Outcome(status, session, reset, "codex-stream" if reset else None,
                       scrub("\n".join(messages)), usage,
                       session_invalid=any(node.get("session_invalid") is True for node in nodes))

    def availability(self, run: Callable[[list[str]], tuple[int, str]]) -> Availability:
        try:
            code, version = run(self.executable + ["--version"])
            if code:
                return Availability(False, None, None, scrub(version))
            code, output = run(self.executable + ["login", "status"])
            logged_in = (code == 0 and "logged in" in output.lower()
                         and "not logged in" not in output.lower())
            return Availability(logged_in, scrub(version.strip()), logged_in,
                                "" if logged_in else "Authentication unavailable")
        except OSError as exc:
            return Availability(False, None, None, scrub(str(exc)))
