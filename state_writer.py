from __future__ import annotations

import errno
import json
import os
import re
import time
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

import yaml

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class StateWriteError(OSError):
    pass


def _section_span(text: str, title: str) -> tuple[int, int, int] | None:
    headings = []
    offset = 0
    fence = ""
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = ""
        elif marker:
            fence = marker[1]
        elif line.startswith("## "):
            headings.append((line[3:].strip(), offset, offset + len(line)))
        offset += len(line)
    if fence:
        raise ValueError("unterminated Markdown fence")
    matches = [
        (index, heading)
        for index, heading in enumerate(headings)
        if heading[0] == title
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate {title} section")
    if not matches:
        return None
    index, (_, start, body) = matches[0]
    end = headings[index + 1][1] if index + 1 < len(headings) else len(text)
    return start, body, end


def plan_section(spec_text: str) -> str:
    span = _section_span(spec_text, "Proposed Plan")
    return spec_text[span[1] : span[2]].strip() if span else ""


def plan_hash(spec_text: str) -> str:
    from hashing import sha256_text

    section = plan_section(spec_text)
    if not section:
        raise ValueError("Proposed Plan section is missing or empty")
    return sha256_text(section)


def approved_scope(spec_text: str) -> list[str]:
    blocks = re.findall(r"^```hub-scope\r?\n(.*?)^```[ \t]*$", plan_section(spec_text), re.M | re.S)
    if not blocks:
        return []
    if len(blocks) != 1:
        raise ValueError("plan requires at most one hub-scope block")
    paths = yaml.safe_load(blocks[0])
    if not isinstance(paths, list) or any(not isinstance(p, str) or not p.strip() for p in paths):
        raise ValueError("hub-scope must be a YAML list of globs")
    return paths


def set_approval_block(spec_text: str, record: dict) -> str:
    block = (
        "## Approval\n\n```hub-approval\n"
        + json.dumps(record, ensure_ascii=False, indent=2)
        + "\n```\n\n"
    )
    span = _section_span(spec_text, "Approval")
    if span:
        return spec_text[: span[0]] + block + spec_text[span[2] :]
    return spec_text.rstrip() + "\n\n" + block


def get_approval_block(spec_text: str) -> dict | None:
    span = _section_span(spec_text, "Approval")
    if not span:
        return None
    body = spec_text[span[1] : span[2]].strip()
    match = re.fullmatch(r"```hub-approval\r?\n(.*?)\r?\n```", body, re.S)
    if not match:
        raise ValueError("Approval must contain exactly one hub-approval JSON block")
    record = json.loads(match[1])
    if not isinstance(record, dict):
        raise ValueError("Approval must be a JSON object")
    return record


def read_text_retry(path: Path) -> str:
    for attempt in range(11):
        try:
            return path.read_text(encoding="utf-8")
        except PermissionError:
            if attempt == 10:
                raise
            time.sleep(0.05 * (attempt + 1))


def atomic_write_text(path: Path, text: str, retries: int, backoff: float) -> None:
    """Caller serializes writers; retries counts attempts after the first replace."""
    _atomic_write_text(path, text, retries, backoff, None)


def _atomic_write_text(
    path: Path,
    text: str,
    retries: int,
    backoff: float,
    fault_hook: Callable[[str], None] | None,
) -> None:
    if retries < 0 or backoff < 0:
        raise ValueError("retries and backoff must be nonnegative")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    if fault_hook is not None:
        fault_hook("before_replace")
    for attempt in range(retries + 1):
        try:
            os.replace(temporary, path)
            return
        except PermissionError as exc:
            if attempt == retries:
                raise StateWriteError("atomic replacement exhausted retries") from exc
            time.sleep(backoff * (attempt + 1))


@dataclass(frozen=True)
class Event:
    seq: int
    ts: str
    kind: str
    task: str
    data: dict


def apply_event(state: dict, event: Event) -> dict:
    """Replay a shallow 'set' merge; other payloads are data, never commands/approvals."""
    result = deepcopy(state)
    updates = event.data.get("set", {})
    if not isinstance(updates, dict):
        raise ValueError("event set must be a mapping")
    result.update(deepcopy(updates))
    result["last_event_seq"] = event.seq
    return result


class Txn:
    """Mutable snapshot; mirror changes in emitted 'set' data for crash replay."""

    def __init__(self, state: dict, task: str) -> None:
        self.state = state
        self._task = task
        self._seq = state["last_event_seq"]
        self._events: list[Event] = []

    def emit(self, kind: str, data: dict) -> int:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", kind):
            raise ValueError("invalid event kind")
        if not isinstance(data, dict):
            raise ValueError("event data must be a mapping")
        # Snapshot JSON data now so caller mutations cannot change a queued event.
        payload = json.loads(json.dumps(data, ensure_ascii=False, allow_nan=False))
        apply_event({}, Event(0, "", kind, self._task, payload))
        self._seq += 1
        self._events.append(
            Event(
                self._seq,
                datetime.now().astimezone().isoformat(),
                kind,
                self._task,
                payload,
            )
        )
        self.state["last_event_seq"] = self._seq
        return self._seq

    def write_spec(self, text: str) -> None:
        """Journal the spec with its approval so recovery completes both writes."""
        self.emit("spec.updated", {"spec_text": text})


class StateStore:
    def __init__(
        self,
        root: Path,
        lock_timeout: float = 10.0,
        replace_retries: int = 10,
        replace_backoff: float = 0.05,
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        if lock_timeout < 0 or replace_retries < 0 or replace_backoff < 0:
            raise ValueError("timeouts, retries and backoff must be nonnegative")
        self.root = Path(root)
        self.lock_timeout = lock_timeout
        self.replace_retries = replace_retries
        self.replace_backoff = replace_backoff
        self._fault_hook = fault_hook

    def task_dir(self, project: str, task: str) -> Path:
        for value in (project, task):
            if not re.fullmatch(r"[A-Za-z0-9-]{1,32}", value):
                raise ValueError("invalid project or task ID")
        return self.root / "projects" / project / "tasks" / task

    @contextmanager
    def _writer_lock(self) -> Iterator[None]:
        path = self.root / "runtime" / "locks" / "writer.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as stream:
            if path.stat().st_size == 0:
                stream.write(b"\0")
                stream.flush()
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    stream.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("global writer lock timed out") from exc
                    time.sleep(min(0.01, remaining))
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read_state(self, project: str, task: str) -> dict:
        path = self.task_dir(project, task) / "state.md"
        try:
            text = read_text_retry(path)
        except FileNotFoundError:
            return {
                "task": task,
                "status": "draft",
                "round": 0,
                "active_run": None,
                "last_event_seq": 0,
                "route": None,
                "worktree": None,
            }
        blocks = re.findall(r"^```hub-state\n(.*?)^```[ \t]*$", text, re.M | re.S)
        if len(blocks) != 1:
            raise StateWriteError("state must contain exactly one hub-state block")
        state = yaml.safe_load(blocks[0])
        if not isinstance(state, dict) or type(state.get("last_event_seq")) is not int:
            raise StateWriteError("invalid state mapping or last_event_seq")
        if state["last_event_seq"] < 0:
            raise StateWriteError("negative last_event_seq")
        return state

    def read_spec(self, project: str, task: str) -> str:
        return read_text_retry(self.task_dir(project, task) / "spec.md")

    def write_spec(self, project: str, task: str, text: str) -> None:
        path = self.task_dir(project, task) / "spec.md"
        with self._writer_lock():
            atomic_write_text(path, text, self.replace_retries, self.replace_backoff)

    def read_events(self, project: str, task: str) -> list[Event]:
        path = self.task_dir(project, task) / "events.md"
        try:
            text = read_text_retry(path)
        except FileNotFoundError:
            return []
        events = []
        for line in text.removesuffix("\n").split("\n") if text else []:
            seq, ts, kind, event_task, payload = line.removeprefix("- ").split(" | ", 4)
            event = Event(int(seq), ts, kind, event_task, json.loads(payload))
            if event.seq != len(events) + 1 or event.task != task:
                raise StateWriteError("invalid event sequence or task")
            if not isinstance(event.data, dict):
                raise StateWriteError("invalid event data")
            events.append(event)
        return events

    def _save_state(self, directory: Path, state: dict) -> None:
        body = yaml.safe_dump(state, sort_keys=False, allow_unicode=True)
        text = (
            f"# Task state\n\nLast event: {state['last_event_seq']}\n\n"
            f"```hub-state\n{body}```\n"
        )
        _atomic_write_text(
            directory / "state.md",
            text,
            self.replace_retries,
            self.replace_backoff,
            self._fault_hook,
        )

    def _recover_locked(self, project: str, task: str, save: bool = True) -> dict:
        directory = self.task_dir(project, task)
        for temporary in directory.glob("*.tmp-*"):
            temporary.unlink(missing_ok=True)
        state = self.read_state(project, task)
        events = self.read_events(project, task)
        if state["last_event_seq"] > len(events):
            raise StateWriteError("state is ahead of the event journal")
        pending = events[state["last_event_seq"] :]
        for event in pending:
            if event.kind == "spec.updated":
                atomic_write_text(directory / "spec.md", event.data["spec_text"],
                                  self.replace_retries, self.replace_backoff)
            state = apply_event(state, event)
        if pending and save:
            self._save_state(directory, state)
        return state

    def recover(self, project: str, task: str) -> None:
        self.task_dir(project, task)
        with self._writer_lock():
            self._recover_locked(project, task)

    @contextmanager
    def transaction(self, project: str, task: str) -> Iterator[Txn]:
        directory = self.task_dir(project, task)
        with self._writer_lock():
            txn = Txn(self._recover_locked(project, task, save=False), task)
            yield txn
            txn.state["last_event_seq"] = txn._seq
            # Serialize both files before writing either, including invalid YAML values.
            yaml.safe_dump(txn.state)
            lines = "".join(
                f"- {event.seq:06d} | {event.ts} | {event.kind} | {event.task} | "
                f"{json.dumps(event.data, ensure_ascii=False, separators=(',', ':'))}\n"
                for event in txn._events
            )
            directory.mkdir(parents=True, exist_ok=True)
            if lines:
                with (directory / "events.md").open(
                    "a", encoding="utf-8", newline="\n"
                ) as stream:
                    stream.write(lines)
                    stream.flush()
                    os.fsync(stream.fileno())
                if self._fault_hook is not None:
                    self._fault_hook("after_event_append")
            for event in txn._events:
                if event.kind == "spec.updated":
                    atomic_write_text(directory / "spec.md", event.data["spec_text"],
                                      self.replace_retries, self.replace_backoff)
            self._save_state(directory, txn.state)

    def _runtime_path(self, name: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}\.md", name):
            raise ValueError("invalid runtime Markdown filename")
        return self.root / "runtime" / name

    def write_runtime_file(self, name: str, text: str) -> None:
        path = self._runtime_path(name)
        with self._writer_lock():
            atomic_write_text(path, text, self.replace_retries, self.replace_backoff)

    def read_runtime_file(self, name: str) -> str:
        return read_text_retry(self._runtime_path(name))
