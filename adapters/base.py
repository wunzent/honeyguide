from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterator, Literal, Protocol

from agent_loader import AgentTemplate


@dataclass
class Route:
    vendor: str
    model: str
    effort: str
    max_budget_usd: float | None = None


@dataclass
class InvocationSpec:
    argv: list[str]
    cwd: Path
    stdin_text: str | None
    env: dict[str, str]
    allowed_tools: tuple[str, ...] | None = None
    launcher_note: str | None = None


@dataclass
class Outcome:
    status: Literal["ok", "failed", "quota_limited", "auth_error"]
    session_id: str | None
    reset_at: datetime | None
    reset_source: str | None
    result_text: str
    usage: dict
    reason: str | None = None
    session_invalid: bool = False


@dataclass
class Availability:
    ok: bool
    version: str | None
    logged_in: bool | None
    reason: str


class Adapter(Protocol):
    vendor: str

    def build(self, template: AgentTemplate, route: Route, run_dir: Path,
              worktree: Path, prompt_path: Path,
              resume_session: str | None = None) -> InvocationSpec: ...

    def parse_line(self, line: str) -> dict | None: ...

    def classify(self, exit_code: int, events: list[dict], stderr_tail: str) -> Outcome: ...

    def availability(self, run: Callable[[list[str]], tuple[int, str]]) -> Availability: ...


def scrub(text: str) -> str:
    text = re.sub(r"(?i)\bBearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", text)
    return re.sub(r"(?<![A-Za-z0-9_+/-])[A-Za-z0-9_+/-]{32,}={0,2}(?![A-Za-z0-9_+/=-])",
                  "[REDACTED]", text)


def validate_session_id(value: object) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{8,128}", value) else None


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            if key in {"session_id", "thread_id"}:
                cleaned[key] = validate_session_id(child)
                if child is not None and cleaned[key] is None:
                    cleaned["session_invalid"] = True
            else:
                cleaned[scrub(str(key))] = _clean(child)
        return cleaned
    if isinstance(value, list):
        return [_clean(child) for child in value]
    return value


def _parse_line(line: str) -> dict | None:
    try:
        event = json.loads(line)
    except (ValueError, TypeError):
        return None
    return _clean(event) if isinstance(event, dict) else None


def _dicts(value: object) -> Iterator[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _dicts(child)


def _epoch(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def get_adapter(vendor: str, executable: list[str] | None = None) -> Adapter:
    from adapters.claude_cli import ClaudeAdapter
    from adapters.codex_cli import CodexAdapter

    registry = {"claude": ClaudeAdapter, "codex": CodexAdapter}
    if vendor not in registry:
        raise ValueError(f"Unsupported vendor: {vendor}")
    if executable is not None and (not executable or any(not part for part in executable)):
        raise ValueError("Executable must be a non-empty argv prefix")
    return registry[vendor](executable)
