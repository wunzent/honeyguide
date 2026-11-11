from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

import yaml

from adapters.base import (
    Adapter,
    Availability,
    InvocationSpec,
    Outcome,
    Route,
    get_adapter,
    scrub,
    validate_session_id,
)
from agent_loader import AgentTemplate, load_template
from approvals import ApprovalError, approval_nonces, check_approval, check_record
from model_router import RouteError, load_catalog, resolve
from policy import (
    PolicyError,
    load_policy,
    may_spawn,
    question_class,
    team_active_seconds,
)
from runner import Runner, is_same_process
from scheduler import NeedsOwner, Scheduler
from state_writer import (
    StateStore,
    approved_scope,
    atomic_write_text,
    plan_hash,
    plan_section,
    plan_tier,
    read_text_retry,
)
from worktree_manager import WorktreeManager

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class EngineAlreadyRunning(RuntimeError):
    pass


class EngineStartupError(RuntimeError):
    pass


class _ResumeAdapter:
    """Supply the existing adapter's resume input without changing Runner's API."""

    def __init__(self, adapter: Adapter, session: str) -> None:
        self.adapter, self.session = adapter, session

    def build(
        self,
        template: AgentTemplate,
        route: Route,
        run_dir: Path,
        worktree: Path,
        prompt_path: Path,
        resume_session: str | None = None,
    ) -> InvocationSpec:
        return self.adapter.build(
            template, route, run_dir, worktree, prompt_path, resume_session=self.session
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.adapter, name)


class Engine:
    def __init__(
        self,
        hub_root: Path,
        *,
        store: StateStore,
        policy_loader: Callable,
        adapters: dict[str, Adapter],
        runner: Runner,
        worktrees: WorktreeManager,
        scheduler: Scheduler | None,
        notifier: Callable | None = None,
        clock: Callable[[], datetime],
        availability_probe: Callable[[str], Availability],
    ) -> None:
        self.root = Path(hub_root).resolve()
        if store.root.resolve() != self.root:
            raise ValueError("store must belong to the configured hub")
        self.store, self.runner, self.worktrees = store, runner, worktrees
        self.adapters, self.clock, self.availability_probe = (
            adapters,
            clock,
            availability_probe,
        )
        self.runner.availability_probe = self.availability_probe
        self.notifier = notifier
        self._lock = None
        self._acquire()
        try:
            self.policy = policy_loader(self.root)
            if self.policy != load_policy(self.root):
                raise PolicyError("loaded policy differs from current policy")
            self.catalog = load_catalog(self.root / "config" / "models.toml")
            self.scheduler = scheduler or Scheduler(store, self.policy, clock)
            # The engine always uses the freshly loaded execution policy.
            self.scheduler.policy = self.policy
            for project, task, _ in self._tasks():
                store.recover(project, task)
                self._mirror_questions(project, task)
            self.reconcile()
        except Exception as exc:
            self.close()
            raise EngineStartupError(
                f"engine refused startup: {scrub(str(exc))}"
            ) from exc

    def _acquire(self) -> None:
        path = self.root / "runtime" / "locks" / "engine.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = path.open("a+b")
        try:
            if path.stat().st_size == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise EngineAlreadyRunning(
                    "another engine holds runtime/locks/engine.lock"
                ) from exc
            raise
        self._lock = stream

    def close(self) -> None:
        """Release the engine lease; agents keep running for restart reconciliation."""
        stream = getattr(self, "_lock", None)
        if stream is not None:
            self._lock = None
            stream.close()

    def __del__(self) -> None:
        self.close()

    def _tasks(self) -> Iterator[tuple[str, str, dict]]:
        for path in sorted((self.root / "projects").glob("*/tasks/*")):
            if not path.is_dir() or not any(
                (path / name).exists() for name in ("state.md", "events.md")
            ):
                continue
            project, task = path.parents[1].name, path.name
            yield project, task, self.store.read_state(project, task)

    def _update(
        self, project: str, task: str, kind: str, updates: dict, **data
    ) -> None:
        with self.store.transaction(project, task) as txn:
            txn.state.update(updates)
            txn.emit(kind, {**data, "set": updates})

    def _run_update(
        self, project: str, task: str, run_id: str, kind: str, changes: dict, **updates
    ) -> None:
        with self.store.transaction(project, task) as txn:
            runs = dict(txn.state.get("runs", {}))
            if kind == "run.lost" and runs[run_id].get("status") == "running":
                updates["team_active_seconds"] = team_active_seconds(
                    {
                        "team_active_seconds": txn.state.get("team_active_seconds", 0),
                        "runs": {run_id: runs[run_id]},
                    },
                    self.clock(),
                )
                changes = {**changes, "finished_at": self.clock().isoformat()}
            runs[run_id] = {**runs[run_id], **changes}
            updates = {**updates, "runs": runs}
            txn.state.update(updates)
            txn.emit(kind, {"run": run_id, "set": updates})

    def _mirror_questions(self, project: str, task: str) -> None:
        with self.store._writer_lock():
            questions = self.store.read_state(project, task).get("questions", [])
            if not questions:
                return
            text = (
                "# Questions\n\n```hub-questions\n"
                + yaml.safe_dump(questions, sort_keys=False)
                + "```\n"
            )
            for q in questions:
                text += (
                    f"\n## {q['id']}: {q['title']}\n\n{q['context']}\n\n"
                    f"Impact: {q['impact']}\n\nClass: {q['class']} · Status: {q['status']}\n\n"
                    + yaml.safe_dump(
                        {"options": q["options"], "default": q["default"]},
                        sort_keys=False,
                    )
                )
            atomic_write_text(
                self.store.task_dir(project, task) / "questions.md",
                text,
                self.store.replace_retries,
                self.store.replace_backoff,
            )

    def _question(self, project: str, task: str, request: dict, run: dict) -> None:
        with self.store.transaction(project, task) as txn:
            questions = list(txn.state.get("questions", []))
            if any(q.get("source_run") == run["run"] for q in questions):
                return
            qtype = str(request.get("type", "security"))
            question = {
                "id": f"q{len(questions) + 1}",
                "title": request.get("title", "Agent needs input"),
                "context": request.get("context", f"See run {run['run']}"),
                "impact": request.get("impact", "Task is blocked"),
                "options": request.get("options", []),
                "default": request.get("default", "none"),
                "blocking": True,
                "type": qtype,
                "class": question_class(self.policy, qtype),
                "status": "draft",
                "asked_by": run["role"],
                "source_run": run["run"],
                "draft_text": scrub(json.dumps(request, ensure_ascii=False)),
            }
            updates = {
                "questions": [*questions, question],
                "status": "needs-you",
                "resume_stage": txn.state.get("resume_stage") or txn.state["status"],
            }
            txn.state.update(updates)
            txn.emit("question.draft", {"set": updates})
        self._mirror_questions(project, task)
        if self.notifier is not None:
            self.notifier(project, task, question)

    def _resume_questions(self, project: str, task: str, state: dict) -> dict:
        if state.get("status") != "needs-you" or not state.get("questions"):
            return state
        with self.store.transaction(project, task) as txn:
            state = txn.state
            stage = state.get("resume_stage")
            if not stage:
                # Bridge questions can arrive between ticks. Recover the stage
                # immediately before question.opened from the durable event log.
                previous = None
                for event in self.store.read_events(project, task):
                    status = event.data.get("set", {}).get("status", previous)
                    if status == "needs-you" and previous != "needs-you":
                        stage = previous if event.kind == "question.opened" else None
                    previous = status
            questions, context = [], []
            for question in state["questions"]:
                q = dict(question)
                classification = question_class(self.policy, q["type"])
                q["class"] = classification
                answer = state.get("answers", {}).get(q["id"])
                valid = False
                if q["id"] in state.get("answers", {}):
                    try:
                        check_record(
                            answer,
                            kind="answer",
                            project=project,
                            task=task,
                            question_id=q["id"],
                            plan_hash=plan_hash(self.store.read_spec(project, task)),
                            policy_hash=self.policy.policy_hash,
                            used_nonces=[],
                        )
                        if (
                            answer["answer"] not in [o["label"] for o in q["options"]]
                            and answer["answer"] != answer["quote"]
                        ):
                            raise ApprovalError("invalid answer option")
                        text = {"quote": answer["quote"], "option": answer["answer"]}
                        context.append(
                            {
                                "question_id": q["id"],
                                "question": q["title"],
                                "options": q["options"],
                                "class": classification,
                                "answer": text,
                            }
                        )
                        valid = True
                    except (ApprovalError, KeyError, TypeError):
                        txn.emit(
                            "answer.rejected",
                            {
                                "question_id": q["id"],
                                "reason": "answer verification failed",
                            },
                        )
                if (
                    q.get("type") == "plan-policy-changed"
                    and q.get("asked_by") == "engine"
                    and state.get("approval_reason") is None
                ):
                    valid = True
                if valid:
                    q["status"] = "answered"
                elif q.get("status") == "answered":
                    q["status"] = "open"
                questions.append(q)
            updates = {
                "questions": questions,
                "resume_stage": stage,
                "answer_context": context,
            }
            if stage in {
                "approved",
                "coding",
                "testing",
                "reviewing",
                "waiting-quota",
            } and not any(
                q.get("blocking") and q["status"] != "answered" for q in questions
            ):
                updates.update(status=stage, resume_stage=None, needs_run=True)
                kind = "questions.resumed"
            else:
                kind = "questions.updated"
            if any(state.get(key) != value for key, value in updates.items()):
                state.update(updates)
                txn.emit(kind, {"set": updates})
            result = dict(state)
        self._mirror_questions(project, task)
        return result

    def _project(self, project: str) -> dict:
        text = read_text_retry(self.root / "projects" / project / "project.md")
        blocks = re.findall(r"^```hub-project\s*\n(.*?)^```[ \t]*$", text, re.M | re.S)
        if len(blocks) != 1:
            raise ValueError("project.md requires one hub-project YAML block")
        config = yaml.safe_load(blocks[0])
        if (
            not isinstance(config, dict)
            or not all(
                isinstance(config.get(k), str) and config[k]
                for k in ("repo", "base_ref")
            )
            or not all(
                isinstance(config.get(k), list)
                and config[k]
                and all(isinstance(v, str) and v for v in config[k])
                for k in ("allowed_paths", "test_command")
            )
            or type(config.get("test_timeout_s")) not in (int, float)
            or config["test_timeout_s"] <= 0
        ):
            raise ValueError("invalid hub-project configuration")
        return config

    def _poll(self, project: str, task: str, run_id: str) -> Outcome | None:
        run = self.store.read_state(project, task)["runs"][run_id]
        # After reattachment there is no Popen exit code. Only a terminal provider
        # protocol event can establish completion; result prose is never authority.
        if (
            run.get("status") == "running"
            and not is_same_process(run.get("pid"), run.get("create_time"))
            and (project, task, run_id) not in self.runner._processes
        ):
            path = self.store.task_dir(project, task) / "runs" / run_id / "output.jsonl"
            adapter = self.adapters[run["route"]["vendor"]]
            events = [
                event
                for line in read_text_retry(path).splitlines()
                if (event := adapter.parse_line(line)) is not None
            ]
            terminal = events[-1] if events else {}
            success = (
                terminal.get("type") in {"turn.completed", "turn_completed"}
                or terminal.get("type") == "result"
                and terminal.get("is_error") is False
            )
            if success:
                self._run_update(
                    project, task, run_id, "run.terminal", {"exit_code": 0}
                )
        return self.runner.poll(project, task, run_id)

    def reconcile(self) -> None:
        now = self.clock()
        for project, task, state in self._tasks():
            if not self._check_task_approval(project, task, state) or state.get(
                "status"
            ) in {"paused", "cancelled"}:
                continue
            for run_id, run in state.get("runs", {}).items():
                if run.get("status") not in {"intent", "running"}:
                    continue
                if is_same_process(run.get("pid"), run.get("create_time")):
                    continue
                if run["status"] == "intent":
                    age = (
                        now - datetime.fromisoformat(run["intent_at"])
                    ).total_seconds()
                    if age <= 60:
                        continue
                    try:
                        if self.runner.adopt_intent(project, task, run_id):
                            continue
                    except PolicyError:
                        self._run_update(
                            project,
                            task,
                            run_id,
                            "spawn.inspection-failed",
                            {"status": "inspection-failed"},
                            status="needs-you",
                            needs_run=False,
                        )
                        continue
                    count = state.get("spawned_keys", {}).get(run["idem_key"], 0)
                    allowed = count <= min(1, self.policy.respawn_per_key)
                    self._run_update(
                        project,
                        task,
                        run_id,
                        "spawn.abandoned",
                        {"status": "abandoned"},
                        status=("coding" if run["role"] == "coder" else "reviewing")
                        if allowed
                        else "needs-you",
                        needs_run=allowed,
                        retry_key=run["idem_key"],
                    )
                    continue
                directory = self.store.task_dir(project, task) / "runs" / run_id
                output = directory / "output.jsonl"
                if (
                    (directory / "result.md").exists()
                    or output.exists()
                    and output.stat().st_size
                    or (directory / "stderr.txt").exists()
                    and (directory / "stderr.txt").stat().st_size
                ):
                    outcome = self._poll(project, task, run_id)
                    if outcome is not None:
                        self._handle(project, task, run_id, outcome)
                else:
                    session = run.get("session_id") or state.get("checkpoint", {}).get(
                        "session_id"
                    )
                    self._run_update(
                        project,
                        task,
                        run_id,
                        "run.lost",
                        {"status": "lost"},
                        status="waiting-quota" if session else "needs-you",
                        checkpoint={
                            "session_id": session,
                            "run": run_id,
                            "round": state.get("round", 1),
                            "role": run["role"],
                            "idem_key": run["idem_key"],
                        },
                    )
                    if session:
                        self.scheduler.add(
                            "resume",
                            project,
                            task,
                            now,
                            "run.lost; vendor session available",
                            0,
                            1,
                        )

    def _result(self, text: str) -> dict:
        matches = re.findall(r"^RESULT:\s*(\{.*\})\s*$", text, re.M)
        candidate = matches[-1] if matches else text.strip()
        try:
            result = json.loads(candidate)
            return result if isinstance(result, dict) else {}
        except ValueError:
            return {}

    def _handle(self, project: str, task: str, run_id: str, outcome: Outcome) -> None:
        state = self.store.read_state(project, task)
        run = state["runs"][run_id]
        if run.get("handled"):
            return
        self._process_outcome(project, task, run_id, outcome, state, run)
        self._run_update(
            project, task, run_id, "run.handled", {"handled": True}, active_run=None
        )

    def _process_outcome(
        self,
        project: str,
        task: str,
        run_id: str,
        outcome: Outcome,
        state: dict,
        run: dict,
    ) -> None:
        if team_active_seconds(state, self.clock()) >= self.policy.team_minutes * 60:
            self._update(
                project,
                task,
                "team.exhausted",
                {
                    "status": "needs-you",
                    "needs_run": False,
                },
            )
            return
        if state.get("last_coder_run") == run_id:
            return
        if (
            outcome.status == "quota_limited"
            and state.get("checkpoint", {}).get("run") == run_id
            and state.get("status") in {"waiting-quota", "needs-you"}
        ):
            return
        result = self._result(outcome.result_text)
        if isinstance(result.get("question_request"), dict):
            self._question(
                project, task, result["question_request"], {**run, "run": run_id}
            )
            return
        if outcome.status == "quota_limited":
            self._quota(project, task, state, run_id, run, outcome)
        elif outcome.status == "ok" and run["role"] == "coder":
            try:
                config = self._project(project)
                worktree = Path(run["worktree"])
                patches = re.findall(
                    r"^```diff\s*\n(.*?)^```[ \t]*$", outcome.result_text, re.M | re.S
                )
                if run["route"]["vendor"] == "claude" and patches:
                    self.worktrees.apply_patch(
                        worktree,
                        "\n".join(patches),
                        (
                            config["allowed_paths"]
                            + approved_scope(self.store.read_spec(project, task))
                        ),
                    )
                if self.runner.scope_check(
                    project,
                    task,
                    worktree,
                    (
                        config["allowed_paths"]
                        + approved_scope(self.store.read_spec(project, task))
                    ),
                ):
                    return
                self._update(
                    project,
                    task,
                    "coding.finished",
                    {
                        "status": "testing",
                        "worktree": str(worktree),
                        "coder_vendor": run["route"]["vendor"],
                        "last_coder_run": run_id,
                    },
                )
            except (OSError, ValueError, PolicyError) as exc:
                self._update(
                    project,
                    task,
                    "coding.rejected",
                    {"status": "needs-you"},
                    reason=scrub(str(exc)),
                )
        elif outcome.status == "ok" and run["role"] == "reviewer":
            if result.get("verdict") == "PASS":
                quota = {**state.get("quota", {}), "active": False, "attempt": 0}
                self._update(
                    project,
                    task,
                    "review.passed",
                    {
                        "status": "ready_to_commit",
                        "needs_run": False,
                        "quota": quota,
                        "quota_blocked": [],
                        "review": {
                            "verdict": "PASS",
                            "round": state.get("round", 1),
                            "run": run_id,
                            "test_run": state.get("last_test_run"),
                        },
                    },
                )
            elif state.get("review_fix_cycles", 0) < min(
                1, self.policy.review_fix_cycles
            ):
                self._next_round(project, task, state, review=True)
            else:
                self._update(project, task, "review.exhausted", {"status": "needs-you"})
        else:
            self._update(
                project,
                task,
                "run.blocked",
                {"status": "needs-you"},
                reason=outcome.reason or outcome.status,
            )

    def _quota(
        self,
        project: str,
        task: str,
        state: dict,
        run_id: str,
        run: dict,
        outcome: Outcome,
    ) -> None:
        base_key = state.get("checkpoint", {}).get("base_key", run["idem_key"])
        checkpoint = {
            "session_id": (
                validate_session_id(outcome.session_id)
                or validate_session_id(run.get("session_id"))
                or validate_session_id(state.get("checkpoint", {}).get("session_id"))
            ),
            "run": run_id,
            "round": state.get("round", 1),
            "role": run["role"],
            "idem_key": run["idem_key"],
            "route": run["route"],
            "base_key": base_key,
            "resume_key": f"{base_key}:q{state.get('quota', {}).get('attempt', 0) + 1}",
        }
        self._update(project, task, "quota.checkpoint", {"checkpoint": checkpoint})
        try:
            blocked = set(state.get("quota_blocked", [])) | {run["route"]["vendor"]}
            route, reasons = self._route(
                run["role"],
                state,
                blocked,
                Route(**run["route"]),
                project=project,
                task=task,
            )
        except RouteError:
            route = None
        if route is not None:
            self._update(
                project,
                task,
                "route.fallback",
                {
                    "route": asdict(route),
                    "needs_run": True,
                    f"{run['role']}_route": asdict(route),
                    "status": "coding" if run["role"] == "coder" else "reviewing",
                    "retry_key": run["idem_key"] + ".fb",
                    "checkpoint": {},
                    "quota_blocked": sorted(blocked),
                },
                reasons=reasons,
            )
            return
        item = self.scheduler.plan_quota_retry(
            outcome, project, task, state, run["route"]["vendor"]
        )
        if isinstance(item, NeedsOwner):
            self._update(
                project,
                task,
                "quota.exhausted",
                {"status": "needs-you"},
                reason=item.reason,
            )
            return
        today = self.clock().date().isoformat()
        quota = dict(state.get("quota", {}))
        episodes = quota.get("episodes_today", 0) if quota.get("day") == today else 0
        # One episode spans consecutive quota failures until a successful result.
        quota.update(
            day=today,
            attempt=item.attempt + 1,
            episodes_today=episodes + (0 if quota.get("active") else 1),
            active=True,
        )
        self._update(
            project,
            task,
            "quota.waiting",
            {
                "status": "waiting-quota",
                "quota": quota,
                "resume_ready": False,
                "needs_run": False,
            },
        )

    def _next_round(
        self, project: str, task: str, state: dict, *, review: bool = False
    ) -> None:
        round_no = state.get("round", 1) + 1
        updates = {
            "status": "coding"
            if round_no <= min(3, self.policy.coder_tester_rounds)
            else "needs-you",
            "round": round_no,
            "needs_run": True,
            "retry_key": None,
            "checkpoint": {},
            "route": state.get("coder_route") or state.get("route"),
        }
        if review:
            updates["review_fix_cycles"] = state.get("review_fix_cycles", 0) + 1
        self._update(project, task, "round.next", updates)

    def _route(
        self,
        role: str,
        state: dict,
        blocked: set[str],
        proposal: Route | None = None,
        *,
        project: str,
        task: str,
    ) -> tuple[Route, list[str]]:
        tier = plan_tier(self.store.read_spec(project, task))
        availability = {
            vendor: self.availability_probe(vendor) for vendor in self.adapters
        }
        latest = state.get("route_proposals", {}).get(role)
        legacy = state.get("route_proposal", {})
        if latest is None and legacy.get("role") == role:
            latest = legacy
        rejected_vendor = None
        if latest is not None:
            try:
                proposed = Route(
                    **{
                        key: value
                        for key, value in latest.items()
                        if key not in {"role", "reason"}
                    }
                )
                return resolve(
                    proposed,
                    role,
                    policy=self.policy,
                    catalog=self.catalog,
                    availability=availability,
                    quota_blocked=blocked,
                    coder_vendor=state.get("coder_vendor"),
                    allow_premium=tier["premium"],
                )
            except (RouteError, TypeError, AttributeError) as exc:
                rejected_vendor = (
                    latest.get("vendor") if isinstance(latest, dict) else None
                )
                reason = scrub(str(exc))
                canonical = json.dumps(
                    latest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                )
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                rejection_key = json.dumps(
                    [role, digest, reason], separators=(",", ":")
                )
                with self.store.transaction(project, task) as txn:
                    keys = list(txn.state.get("route_rejected_keys", []))
                    if rejection_key not in keys:
                        keys.append(rejection_key)
                        changes = {"route_rejected_keys": keys}
                        txn.state.update(changes)
                        txn.emit(
                            "route.rejected",
                            {"role": role, "reason": reason, "set": changes},
                        )
                if reason.startswith(
                    (
                        "needs owner: premium route",
                        "needs owner: model not live-verified",
                    )
                ):
                    raise
                proposal = None
        if proposal is None:
            configured = (
                state.get("review_route")
                if role == "reviewer"
                else state.get("coder_route") or state.get("route")
            )
            if latest is not None:
                configured = None
            if configured:
                proposal = Route(**configured)
            else:
                options = [
                    value
                    for value in self.policy.routing_roles[role]["fallback"]
                    if value.split(":", 1)[1]
                    not in (
                        self.catalog.get(value.split(":", 1)[0], {}).get(
                            "premium_models", []
                        )
                        + self.catalog.get(value.split(":", 1)[0], {}).get(
                            "unverified_models", []
                        )
                    )
                ]
                if not options:
                    raise RouteError("no verified non-premium default model")
                vendor, model = options[0].split(":", 1)
                # Start cross-vendor review directly; choosing the reviewer is
                # distinct from automatically changing a running vendor.
                if role == "reviewer" and vendor == state.get("coder_vendor"):
                    alternate = next(
                        (
                            value
                            for value in options
                            if not value.startswith(vendor + ":")
                        ),
                        None,
                    )
                    if (
                        alternate
                        and alternate.split(":", 1)[0] not in blocked
                        and availability.get(
                            alternate.split(":", 1)[0],
                            Availability(False, None, None, ""),
                        ).ok
                    ):
                        vendor, model = alternate.split(":", 1)
                efforts = ["low", "medium", "high"]
                effort = self.policy.raw["routing"]["tiers"][tier["tier"]]
                cap = self.policy.routing_roles[role].get("max_default_effort", "high")
                effort = efforts[min(efforts.index(effort), efforts.index(cap))]
                if effort in self.catalog.get(vendor, {}).get(
                    "premium_efforts", ["xhigh", "max"]
                ):
                    raise RouteError("default effort must be non-premium")
                proposal = Route(vendor, model, effort)
        if (
            rejected_vendor
            and proposal.vendor != rejected_vendor
            and not self.policy.routing_roles[role].get("auto_fallback", False)
        ):
            raise RouteError(
                f"needs owner: vendor change {rejected_vendor} -> {proposal.vendor}"
            )
        return resolve(
            proposal,
            role,
            policy=self.policy,
            catalog=self.catalog,
            availability=availability,
            quota_blocked=blocked,
            coder_vendor=state.get("coder_vendor"),
            allow_premium=tier["premium"],
        )

    def _check_task_approval(self, project: str, task: str, state: dict) -> bool:
        if state.get("status") in {
            "draft",
            "draft-with-plan",
            "awaiting-approval",
            "committed",
            "delivered",
            "cancelled",
            "paused",
        }:
            return True
        if not state.get("approval"):
            return True  # The spawn gate reports missing approvals.
        try:
            check_approval(
                state["approval"],
                project=project,
                task=task,
                plan_hash=plan_hash(self.store.read_spec(project, task)),
                policy_hash=load_policy(self.root).policy_hash,
                used_nonces=approval_nonces(state),
            )
            return True
        except (ApprovalError, PolicyError, ValueError, OSError, KeyError, TypeError):
            if state.get("approval_reason") != "plan or policy changed":
                questions = list(state.get("questions", []))
                questions.append(
                    {
                        "id": "q-plan-" + str(len(questions) + 1),
                        "title": "Plan/policy changed — approve again?",
                        "context": "The current plan or policy no longer matches the recorded owner approval.",
                        "impact": "Task execution and local commit wait for renewed approval.",
                        "options": [
                            {
                                "label": "approve",
                                "consequence": "Approve the revised plan and policy",
                            },
                            {
                                "label": "revise",
                                "consequence": "Keep the task blocked while revising",
                            },
                        ],
                        "default": "none",
                        "blocking": True,
                        "type": "plan-policy-changed",
                        "class": "owner-decision",
                        "status": "open",
                        "asked_by": "engine",
                    }
                )
                self._update(
                    project,
                    task,
                    "approval.invalidated",
                    {
                        "status": "needs-you",
                        "needs_run": False,
                        "resume_stage": state.get("resume_stage") or state["status"],
                        "approval_reason": "plan or policy changed",
                        "questions": questions,
                    },
                )
                self._mirror_questions(project, task)
            return False

    def tick(self, now: datetime) -> None:
        if self._lock is None:
            raise RuntimeError("engine is closed")
        try:
            self.policy = load_policy(self.root)
            self.scheduler.policy = self.policy
        except PolicyError:
            pass  # Each task's approval check records the policy problem below.
        self.scheduler.run_due(now)
        ready = {
            (project, task)
            for project, task, state in self._tasks()
            if state.get("status") == "ready_to_commit"
        }
        self.reconcile()
        for project, task, state in self._tasks():
            if not self._check_task_approval(project, task, state) or state.get(
                "status"
            ) in {"paused", "cancelled"}:
                if state.get("status") == "cancelled":
                    for run in self.runner.live_runs():
                        if (run["project"], run["task"]) == (project, task):
                            self.runner.stop(run["pid"], run["create_time"])
                continue
            for run_id, run in state.get("runs", {}).items():
                if (
                    run.get("status") == "intent"
                    or run.get("kind") == "tests"
                    or run.get("handled")
                ):
                    continue
                if run.get("status") in {
                    "running",
                    "ok",
                    "failed",
                    "quota_limited",
                    "auth_error",
                }:
                    outcome = self._poll(project, task, run_id)
                    if outcome is not None:
                        self._handle(project, task, run_id, outcome)
        for project, task, state in self._tasks():
            if not self._check_task_approval(project, task, state) or state.get(
                "status"
            ) in {"paused", "cancelled"}:
                continue
            if state.get("status") == "ready_to_commit":
                if (project, task) not in ready:
                    continue
                try:
                    self.runner.commit_task(project, task)
                except (OSError, ValueError, PolicyError) as exc:
                    self._update(
                        project,
                        task,
                        "commit.blocked",
                        {"status": "needs-you"},
                        reason=scrub(str(exc)),
                    )
                continue
            state = self._resume_questions(project, task, state)
            if team_active_seconds(state, now) >= self.policy.team_minutes * 60:
                if state.get("status") in {
                    "approved",
                    "coding",
                    "testing",
                    "reviewing",
                    "waiting-quota",
                }:
                    updates = {"status": "needs-you", "needs_run": False}
                    self._update(project, task, "team.elapsed", updates)
                    state = {**state, **updates}
            if state.get("status") == "testing":
                if len(self.runner.live_runs()) < self.policy.max_processes:
                    try:
                        config = self._project(project)
                        result = self.runner.run_tests(
                            project,
                            task,
                            Path(state["worktree"]),
                            config["test_command"],
                            config["test_timeout_s"],
                        )
                        if result["passed"]:
                            quota = {
                                **state.get("quota", {}),
                                "active": False,
                                "attempt": 0,
                            }
                            self._update(
                                project,
                                task,
                                "testing.passed",
                                {
                                    "status": "reviewing",
                                    "needs_run": True,
                                    "retry_key": None,
                                    "checkpoint": {},
                                    "quota": quota,
                                    "quota_blocked": [],
                                },
                            )
                        else:
                            self._next_round(project, task, state)
                    except (OSError, ValueError, PolicyError) as exc:
                        self._update(
                            project,
                            task,
                            "testing.blocked",
                            {"status": "needs-you"},
                            reason=scrub(str(exc)),
                        )
                continue
            resume = state.get("status") == "waiting-quota" and state.get(
                "resume_ready"
            )
            if not resume and state.get("status") not in {
                "approved",
                "coding",
                "reviewing",
            }:
                continue
            if state.get("needs_run") is False and not resume:
                continue
            if any(
                run.get("status") in {"intent", "running"}
                for run in state.get("runs", {}).values()
            ):
                continue
            live = self.runner.live_runs()
            reservations = [
                run
                for _, _, snapshot in self._tasks()
                for run in snapshot.get("runs", {}).values()
                if run.get("status") == "intent"
            ]
            live += reservations
            dynamic = bool(state.get("dynamic"))
            if (
                len(live) >= self.policy.max_processes
                or dynamic
                and sum(bool(r.get("dynamic")) for r in live) >= self.policy.max_dynamic
            ):
                continue
            role = (
                state.get("checkpoint", {}).get("role", "coder")
                if resume
                else ("reviewer" if state["status"] == "reviewing" else "coder")
            )
            checkpoint = state.get("checkpoint", {})
            key = (
                (checkpoint.get("resume_key") or checkpoint.get("idem_key"))
                if resume
                else state.get("retry_key")
            ) or (f"{task}:{role}:{max(1, state.get('round', 1))}")
            # Persist only the dispatch state expected by the existing policy;
            # this is readiness, never an approval. Both gates verify the spec.
            dispatch_status = "approved" if role == "coder" else "reviewing"
            candidate = {**state, "status": dispatch_status}
            decision = may_spawn(
                policy=self.policy,
                spec_text=self.store.read_spec(project, task),
                state=candidate,
                live_runs=live,
                role=role,
                idem_key=key,
                dynamic=dynamic,
                now=self.clock(),
            )
            if not decision.ok:
                self._update(
                    project,
                    task,
                    "spawn.denied",
                    {"status": "needs-you"},
                    reason=decision.reason,
                )
                continue
            try:
                resume_route = state.get("checkpoint", {}).get("route") or state.get(
                    "route"
                )
                proposal = Route(**resume_route) if resume and resume_route else None
                route, reasons = self._route(
                    role,
                    state,
                    set() if resume else set(state.get("quota_blocked", [])),
                    proposal,
                    project=project,
                    task=task,
                )
                if (
                    resume
                    and resume_route
                    and any(
                        resume_route.get(key) != getattr(route, key)
                        for key in ("vendor", "model")
                    )
                ):
                    self._question(
                        project,
                        task,
                        {
                            "title": "Resume cannot keep the original vendor/model — approve a fresh session?",
                            "context": (
                                f"The checkpoint uses {resume_route.get('vendor')}:{resume_route.get('model')}; "
                                f"routing selected {route.vendor}:{route.model}."
                            ),
                            "impact": "No worker starts until the owner decides whether to lose session continuity.",
                            "options": [
                                {
                                    "label": "approve",
                                    "consequence": "Allow a fresh session on the selected route",
                                },
                                {
                                    "label": "keep-original",
                                    "consequence": "Wait for the original vendor/model",
                                },
                            ],
                            "default": "none",
                            "type": "resume-route-changed",
                        },
                        {"run": key, "role": "engine"},
                    )
                    self._update(
                        project,
                        task,
                        "session.resume_refused",
                        {
                            "status": "needs-you",
                            "needs_run": False,
                            "resume_ready": False,
                        },
                        reason="resume route changed",
                    )
                    continue
                config = self._project(project)
                worktree = self.worktrees.create(
                    self.policy, project, task, Path(config["repo"]), config["base_ref"]
                )
                self._update(
                    project,
                    task,
                    "dispatch.ready",
                    {
                        "status": dispatch_status,
                        "round": max(1, state.get("round", 1)),
                        "worktree": str(worktree),
                        "route": asdict(route),
                        f"{role}_route": asdict(route),
                    },
                    reasons=reasons,
                )
                session = (
                    state.get("checkpoint", {}).get("session_id") if resume else None
                )
                original = self.runner.adapters[route.vendor]
                if session is not None:
                    self.runner.adapters[route.vendor] = _ResumeAdapter(
                        original, session
                    )
                try:
                    answers = (
                        "\n\nQuestion answers (data):\n"
                        + json.dumps(state["answer_context"], ensure_ascii=False)
                        if state.get("answer_context")
                        else ""
                    )
                    self.runner.availability_probe = self.availability_probe
                    self.runner.start(
                        project,
                        task,
                        role,
                        route,
                        load_template(self.root / "agents" / f"{role}.md"),
                        worktree,
                        key,
                        {
                            "approved_plan": plan_section(
                                self.store.read_spec(project, task)
                            ),
                            "repository_context": str(worktree) + answers,
                            "diff": "Review the current worktree diff." + answers,
                        },
                        dynamic=dynamic,
                    )
                finally:
                    self.runner.adapters[route.vendor] = original
                self._update(
                    project,
                    task,
                    "dispatch.started",
                    {
                        "status": "coding" if role == "coder" else "reviewing",
                        "needs_run": False,
                        "resume_ready": False,
                        "retry_key": None,
                    },
                )
            except (OSError, ValueError, PolicyError) as exc:
                self._update(
                    project,
                    task,
                    "dispatch.blocked",
                    {"status": "needs-you"},
                    reason=scrub(str(exc)),
                )

    def run_forever(self, interval_s: float = 30) -> None:
        if interval_s <= 0:
            raise ValueError("interval must be positive")
        while True:
            self.tick(self.clock())
            time.sleep(interval_s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub-root", type=Path, default=Path("."))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    root = args.hub_root.resolve()
    store, worktrees = StateStore(root), WorktreeManager()
    adapters = {vendor: get_adapter(vendor) for vendor in ("claude", "codex")}
    clock = lambda: datetime.now(timezone.utc)

    def probe(vendor: str) -> Availability:
        def run(command: list[str]) -> tuple[int, str]:
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            return result.returncode, result.stdout + result.stderr

        return adapters[vendor].availability(run)

    try:
        engine = Engine(
            root,
            store=store,
            policy_loader=load_policy,
            adapters=adapters,
            runner=Runner(store, adapters, worktrees, root, clock),
            worktrees=worktrees,
            scheduler=None,
            clock=clock,
            availability_probe=probe,
        )
    except (EngineStartupError, EngineAlreadyRunning) as exc:
        parser.exit(1, f"{exc}\n")
    try:
        if args.once:
            engine.tick(clock())
        else:
            engine.run_forever()
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
