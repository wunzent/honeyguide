from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from adapters.base import Outcome, _dicts, _epoch
from policy import Policy, load_policy
from state_writer import StateStore, atomic_write_text


@dataclass(frozen=True)
class Item:
    id: str
    due_at: datetime
    action: str
    project: str
    task: str
    reason: str
    attempt: int
    max: int
    status: str = "pending"


@dataclass(frozen=True)
class NeedsOwner:
    reason: str


_COLUMNS = "| id | due_at | action | project | task | reason | attempt | max | status |"


def _time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("schedule times must include a timezone")
    return value.astimezone(timezone.utc)


class Scheduler:
    def __init__(
        self,
        store: StateStore,
        policy: Policy,
        clock: Callable[[], datetime],
        *,
        rng: Callable[[int, int], int] = random.randint,
        sessions_reader: Callable[[], dict | None] | None = None,
    ) -> None:
        self.store, self.policy, self.clock, self.rng = store, policy, clock, rng
        self.sessions_reader = sessions_reader

    def _read(self) -> list[Item]:
        try:
            text = self.store.read_runtime_file("schedule.md")
        except FileNotFoundError:
            return []
        lines = text.splitlines()
        if len(lines) < 4 or lines[2] != _COLUMNS or lines[3] != "|" + " --- |" * 9:
            raise ValueError("invalid schedule table")
        items = []
        for line in lines[4:]:
            if not line.strip():
                continue
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) != 9:
                raise ValueError("invalid schedule row")
            ident, due, action, project, task, reason, attempt, maximum, status = cells
            self.store.task_dir(project, task)
            if status not in {"pending", "done", "cancelled"} or action != "resume":
                raise ValueError("invalid schedule action or status")
            item = Item(
                ident,
                _time(datetime.fromisoformat(due)),
                action,
                project,
                task,
                json.loads(reason),
                int(attempt),
                int(maximum),
                status,
            )
            if (
                not isinstance(item.reason, str)
                or item.attempt < 0
                or item.max < 1
                or any(old.id == ident for old in items)
            ):
                raise ValueError("invalid schedule item")
            items.append(item)
        return items

    def _write(self, items: list[Item]) -> None:
        rows = ["# Scheduled actions", "", _COLUMNS, "|" + " --- |" * 9]
        for item in items:
            reason = json.dumps(item.reason, ensure_ascii=True).replace("|", "\\u007c")
            cells = (
                item.id,
                item.due_at.isoformat(),
                item.action,
                item.project,
                item.task,
                reason,
                str(item.attempt),
                str(item.max),
                item.status,
            )
            rows.append("| " + " | ".join(cells) + " |")
        # The runtime path helper validates the name. The caller holds the writer
        # lock over read/modify/replace; write_runtime_file would acquire it twice.
        atomic_write_text(
            self.store._runtime_path("schedule.md"),
            "\n".join(rows) + "\n",
            self.store.replace_retries,
            self.store.replace_backoff,
        )

    def add(
        self,
        action: str,
        project: str,
        task: str,
        due_at: datetime,
        reason: str,
        attempt: int,
        max: int,
    ) -> str:
        self.store.task_dir(project, task)
        due_at = _time(due_at)
        if (
            action != "resume"
            or type(attempt) is not int
            or attempt < 0
            or type(max) is not int
            or max < 1
            or not isinstance(reason, str)
        ):
            raise ValueError("invalid scheduled action")
        with self.store._writer_lock():
            items = self._read()
            for item in items:
                if item.status == "pending" and (
                    item.action,
                    item.project,
                    item.task,
                    item.attempt,
                ) == (action, project, task, attempt):
                    return item.id
            item = Item(
                "S-" + uuid4().hex, due_at, action, project, task, reason, attempt, max
            )
            self._write([*items, item])
            return item.id

    def due(self, now: datetime) -> list[Item]:
        return sorted(
            (
                item
                for item in self._read()
                if item.status == "pending" and item.due_at <= _time(now)
            ),
            key=lambda item: (item.due_at, item.id),
        )

    def mark(self, id: str, status: str) -> None:
        if status not in {"pending", "done", "cancelled"}:
            raise ValueError("invalid schedule status")
        with self.store._writer_lock():
            items = self._read()
            if not any(item.id == id for item in items):
                raise KeyError(id)
            self._write(
                [
                    replace(item, status=status) if item.id == id else item
                    for item in items
                ]
            )

    def plan_quota_retry(
        self,
        outcome: Outcome,
        project: str,
        task: str,
        state: dict,
        adapter_vendor: str,
        sessions_reader: Callable[[], dict | None] | None = None,
    ) -> Item | NeedsOwner:
        now = _time(self.clock())
        if outcome.status != "quota_limited" or adapter_vendor not in {
            "claude",
            "codex",
        }:
            raise ValueError("quota outcome and supported vendor required")
        sessions_reader = sessions_reader or self.sessions_reader
        quota = state.get("quota", {})
        attempt = quota.get("attempt", 0)
        episodes = (
            quota.get("episodes_today", 0)
            if quota.get("day") == now.date().isoformat()
            else 0
        )
        if (
            type(attempt) is not int
            or attempt < 0
            or type(episodes) is not int
            or episodes < 0
        ):
            raise ValueError("invalid quota counters")
        if attempt >= min(
            self.policy.max_attempts_per_episode, len(self.policy.backoff_minutes)
        ):
            return NeedsOwner("quota attempts exhausted")
        if episodes >= self.policy.max_episodes_per_task_per_day and not quota.get(
            "active"
        ):
            return NeedsOwner("daily quota episode cap reached")
        reset = outcome.reset_at
        source = f"{adapter_vendor}-stream" if reset else "backoff"
        if reset is None and adapter_vendor == "codex" and sessions_reader is not None:
            try:
                limits = sessions_reader()
            except OSError:
                limits = None
            resets = []
            for node in _dicts(limits):
                used = node.get("used_percent")
                if type(used) in (int, float) and used >= 100:
                    candidate = _epoch(node.get("resets_at"))
                    if candidate is not None:
                        resets.append(candidate)
            if resets:
                reset, source = min(resets), "codex-sessions"
        if reset is not None:
            due = _time(reset) + timedelta(
                minutes=self.policy.verified_reset_grace_minutes
            )
        else:
            due = now + timedelta(
                minutes=self.policy.backoff_minutes[attempt], seconds=self.rng(0, 120)
            )
        ident = self.add(
            "resume",
            project,
            task,
            due,
            f"quota; reset_source={source}",
            attempt,
            self.policy.max_attempts_per_episode,
        )
        return next(item for item in self._read() if item.id == ident)

    def run_due(self, now: datetime) -> None:
        """Only enqueue readiness. Dispatch must independently verify owner authority."""
        for item in self.due(now):
            with self.store.transaction(item.project, item.task) as txn:
                # Event precedes schedule completion so a crash can safely replay
                # the enqueue, without granting approval or changing task status.
                if (
                    txn.state.get("resume_schedule_id") != item.id
                    and txn.state.get("status") == "waiting-quota"
                ):
                    updates = {"resume_ready": True, "resume_schedule_id": item.id}
                    txn.state.update(updates)
                    txn.emit("schedule.ready", {"schedule": item.id, "set": updates})
            self.mark(item.id, "done")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub-root", type=Path, default=Path("."))
    parser.add_argument("--once", action="store_true", required=True)
    args = parser.parse_args(argv)
    policy = load_policy(args.hub_root)
    scheduler = Scheduler(
        StateStore(args.hub_root), policy, lambda: datetime.now(timezone.utc)
    )
    scheduler.run_due(scheduler.clock())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
