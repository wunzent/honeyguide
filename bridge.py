from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

import yaml

from policy import ROLES, PolicyError, check_scope, expand, load_policy, question_class
from approvals import approval_nonces, build_record, check_approval, ensure_not_worker
from hashing import sha256_file
from state_writer import (
    StateStore,
    _section_span,
    atomic_write_text,
    get_approval_block,
    approved_scope,
    plan_hash,
    plan_section,
    read_text_retry,
)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", add_help=False)
    status.add_argument("--project")
    status.add_argument("--task")
    commands.add_parser("pending", add_help=False).add_argument(
        "--brief", action="store_true"
    )
    for name in (
        "show",
        "new-task",
        "set-plan",
        "request-approval",
        "propose-route",
        "ask",
        "approve", "answer", "approve-scope", "pause", "resume", "cancel",
    ):
        command = commands.add_parser(name, add_help=False)
        command.add_argument("project")
        command.add_argument("task")
        if name == "new-task":
            command.add_argument("--title", required=True)
        elif name == "set-plan":
            command.add_argument("--file", type=Path, required=True)
        elif name == "propose-route":
            command.add_argument("--role", choices=sorted(ROLES), required=True)
            command.add_argument("--vendor", choices=["claude", "codex"], required=True)
            for field in ("model", "effort", "reason"):
                command.add_argument("--" + field, required=True)
        elif name == "ask":
            source = command.add_mutually_exclusive_group(required=True)
            source.add_argument("--file", type=Path)
            source.add_argument("--json")
            command.add_argument("--id")
        elif name in {"approve", "answer", "approve-scope", "pause", "resume", "cancel"}:
            command.add_argument("--quote", required=True)
            command.add_argument("--desktop", choices=["claude", "codex"],
                                 required=name != "answer", default="codex")
            if name == "answer":
                command.add_argument("qid")
                command.add_argument("--option", default="")
            if name == "approve-scope":
                command.add_argument("--add", action="append", required=True)
    return parser


def task_snapshots(store: StateStore) -> list[dict]:
    result = []
    for path in sorted((store.root / "projects").glob("*/tasks/*/state.md")):
        project, task = path.parents[2].name, path.parent.name
        result.append(
            {**store.read_state(project, task), "project": project, "task": task}
        )
    return result


def pending_data(store: StateStore, policy) -> dict:
    from scheduler import Scheduler

    schedule = Scheduler(store, policy, lambda: datetime.now(timezone.utc))._read()
    tasks, questions = [], []
    for state in task_snapshots(store):
        project, task = state["project"], state["task"]
        if state["status"] in {"awaiting-approval", "needs-you", "waiting-quota"}:
            due = sorted(
                item.due_at.isoformat()
                for item in schedule
                if (item.project, item.task, item.status) == (project, task, "pending")
            )
            tasks.append(
                {
                    "project": project,
                    "task": task,
                    "status": state["status"],
                    "next_due_at": due[0] if due else None,
                }
            )
        questions.extend(
            {**q, "class": question_class(policy, q["type"]), "project": project, "task": task}
            for q in state.get("questions", [])
            if q.get("status") in {"draft", "open"}
            and q.get("id") not in state.get("answers", {})
        )
    lines = [
        f"{s['project']}/{s['task']}: {s['status']}"
        + (f"; due {s['next_due_at']}" if s["next_due_at"] else "")
        for s in tasks
    ]
    lines += [
        f"{q['project']}/{q['task']} {q['id']}: {q['title']} ({q['class']})"
        for q in questions
    ]
    return {"tasks": tasks, "questions": questions, "summary": "\n".join(lines)}


def _text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value.strip()


def _validate_question(raw, policy) -> dict:
    if not isinstance(raw, dict) or "class" in raw:
        raise ValueError("question must be an object; class is computed by policy")
    question = {
        name: _text(raw.get(name), name)
        for name in ("title", "context", "impact", "type", "default")
    }
    if type(raw.get("blocking")) is not bool:
        raise ValueError("blocking must be a boolean")
    options = raw.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 4:
        raise ValueError("options must contain 2–4 choices")
    if any(not isinstance(option, dict) for option in options):
        raise ValueError("each option requires label and consequence")
    question["options"] = [
        {name: _text(option.get(name), name) for name in ("label", "consequence")}
        for option in options
    ]
    labels = [option["label"] for option in question["options"]]
    if len(set(labels)) != len(labels) or question["default"] not in [*labels, "none"]:
        raise ValueError("duplicate labels or invalid default")
    question.update(
        blocking=raw["blocking"],
        asked_by="orchestrator",
        status="open",
        **{"class": question_class(policy, question["type"])},
    )
    return question


def _mirror(store: StateStore, project: str, task: str) -> None:
    with store._writer_lock():
        questions = store.read_state(project, task).get("questions", [])
        text = (
            "# Questions\n\n```hub-questions\n"
            + yaml.safe_dump(questions, sort_keys=False, allow_unicode=True)
            + "```\n"
        )
        atomic_write_text(
            store.task_dir(project, task) / "questions.md",
            text,
            store.replace_retries,
            store.replace_backoff,
        )


def _record(args, policy, spec: str, clock: Callable, kind: str, **extra) -> dict:
    return build_record(kind, project=args.project, task=args.task,
                        plan_hash=plan_hash(spec),
                        policy_hash=sha256_file(policy.hub_root / "config" / "policy.toml"),
                        quote=args.quote, desktop=args.desktop, now=clock(), **extra)


def _stored_question(state: dict, qid: str) -> dict:
    questions = state.get("questions", [])
    if not isinstance(questions, list) or any(
        not isinstance(q, dict) or not isinstance(q.get("id"), str) or not q["id"]
        for q in questions
    ):
        raise ValueError("invalid stored questions")
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("duplicate question IDs")
    question = next((q for q in questions if q["id"] == qid), None)
    if question is None:
        raise ValueError("unknown question")
    options = question.get("options")
    if not isinstance(options, list) or any(
        not isinstance(option, dict) or not isinstance(option.get("label"), str)
        or not option["label"].strip() for option in options
    ):
        raise ValueError("invalid stored question options")
    return question


def _execute(args, store: StateStore, policy, clock: Callable) -> dict:
    ensure_not_worker(os.environ, Path.cwd(), expand(policy.data_root))
    command = args.command
    if command == "status":
        if args.project:
            store.task_dir(args.project, args.task or "check")
        elif args.task:
            store.task_dir("check", args.task)
        return {
            "tasks": [
                s
                for s in task_snapshots(store)
                if (not args.project or s["project"] == args.project)
                and (not args.task or s["task"] == args.task)
            ]
        }
    if command == "pending":
        data = pending_data(store, policy)
        return {"summary": data["summary"]} if args.brief else data
    project, task = args.project, args.task
    directory = store.task_dir(project, task)
    if command == "show":
        if not (directory / "state.md").exists():
            raise ValueError("task does not exist")
        return {
            "state": store.read_state(project, task),
            "spec": store.read_spec(project, task),
        }
    result = {}
    with store.transaction(project, task) as txn:
        exists = (directory / "state.md").exists()
        if command != "new-task" and not exists:
            raise ValueError("task does not exist")
        if command == "new-task":
            if exists or (directory / "spec.md").exists():
                raise ValueError("task already exists")
            title = _text(args.title, "title")
            if "\n" in title or "\r" in title:
                raise ValueError("title must be one line")
            atomic_write_text(
                directory / "spec.md",
                f"# {title}\n",
                store.replace_retries,
                store.replace_backoff,
            )
            updates, kind = (
                {"project": project, "task": task, "title": title, "status": "draft"},
                "task.created",
            )
        elif command == "set-plan":
            body = _text(read_text_retry(args.file), "plan")
            old = store.read_spec(project, task)
            span = _section_span(old, "Proposed Plan")
            block = "## Proposed Plan\n\n" + body + "\n\n"
            new = (
                old[: span[0]] + block + old[span[2] :]
                if span
                else old.rstrip() + "\n\n" + block
            )
            if plan_section(new) != body or get_approval_block(
                new
            ) != get_approval_block(old):
                raise ValueError(
                    "plan must stay inside Proposed Plan; use ### for subheadings"
                )
            digest = plan_hash(new)
            revised = bool(txn.state.get("approval")) and digest != plan_hash(old)
            updates = {"plan_hash": digest}
            if revised or not txn.state.get("approval"):
                updates["status"] = "awaiting-approval"
            if revised and txn.state.get("status") in {"coding", "testing", "reviewing", "waiting-quota", "ready_to_commit"}:
                updates["resume_stage"] = txn.state.get("resume_stage") or txn.state["status"]
            kind = "plan.revised" if revised else "plan.proposed"
            txn.write_spec(new)
            result["plan_hash"] = digest
        elif command == "request-approval":
            if txn.state.get("status") not in {
                "draft",
                "awaiting-approval",
                "needs-you",
            }:
                raise ValueError(
                    "request-approval requires draft, awaiting-approval or needs-you"
                )
            digest = plan_hash(store.read_spec(project, task))
            updates, kind = {"status": "awaiting-approval"}, "approval.requested"
            result.update(
                plan_hash=digest,
                plan_summary=plan_section(store.read_spec(project, task)),
                message="ask the owner in this conversation, then run bridge.py approve with their exact words",
            )
        elif command == "propose-route":
            proposal = {
                key: _text(getattr(args, key), key)
                for key in ("role", "vendor", "model", "effort", "reason")
            }
            updates, kind = {"route_proposal": proposal}, "route.proposed"
            result["proposal"] = proposal
        elif command == "ask":
            raw = (
                yaml.safe_load(read_text_retry(args.file))
                if args.file
                else json.loads(args.json)
            )
            question = _validate_question(raw, policy)
            questions = list(txn.state.get("questions", []))
            previous = (
                next((q for q in questions if q["id"] == args.id), None)
                if args.id
                else None
            )
            if args.id and (
                previous is None
                or previous.get("status") != "draft"
                or args.id in txn.state.get("answers", {})
            ):
                raise ValueError("--id must refer to an unanswered engine draft")
            question["id"] = args.id or "q-" + uuid4().hex
            if previous:
                if (
                    question_class(policy, previous["type"]) == "owner-decision"
                    and question["class"] == "clarify"
                ):
                    raise ValueError("cannot downgrade an owner-decision draft")
                question = {
                    **previous,
                    **question,
                    "draft": previous,
                    "type": previous["type"],
                    "class": question_class(policy, previous["type"]),
                }
                questions = [question if q["id"] == args.id else q for q in questions]
            else:
                questions.append(question)
            updates, kind = {"questions": questions}, "question.opened"
            if question["blocking"]:
                from runner import is_same_process

                live = any(
                    run.get("status") == "intent"
                    or run.get("status") == "running"
                    and is_same_process(run.get("pid"), run.get("create_time"))
                    for run in txn.state.get("runs", {}).values()
                )
                if live or txn.state.get("status") in {
                    "ready_to_commit",
                    "committed",
                    "delivered",
                }:
                    raise ValueError("blocking ask requires an idle, unfinished task")
                updates["status"] = "needs-you"
            result["question"] = question
        elif command in {"approve", "approve-scope"}:
            current = txn.state.get("status")
            if command == "approve" and not (
                current in {"awaiting-approval", "draft-with-plan"}
                or current == "draft" and plan_section(store.read_spec(project, task))
                or current == "needs-you" and txn.state.get("approval_reason") == "plan or policy changed"
            ):
                raise ValueError("approve requires a proposed plan awaiting approval or plan/policy changed")
            if command == "approve-scope" and current in {"committed", "delivered", "cancelled"}:
                raise ValueError("cannot widen a finished task")
            spec = store.read_spec(project, task)
            # Validate the quote before staging any scope change.
            record = _record(args, policy, spec, clock, "approve-plan")
            if command == "approve-scope":
                paths = approved_scope(spec)
                for path in args.add:
                    _text(path, "scope glob")
                    if check_scope([path], ["*"]) or ".git" in path.replace("\\", "/").lower().split("/"):
                        raise ValueError("scope globs must be relative task paths")
                    if path not in paths:
                        paths.append(path)
                section = plan_section(spec)
                section = re.sub(r"^```hub-scope\r?\n.*?^```[ \t]*$", "", section, flags=re.M | re.S).rstrip()
                section += "\n\n```hub-scope\n" + yaml.safe_dump(paths, sort_keys=False) + "```\n\n"
                span = _section_span(spec, "Proposed Plan")
                spec = spec[:span[1]] + "\n" + section + spec[span[2]:]
                scope_record = _record(args, policy, spec, clock, "approve-scope", extra={"add": args.add})
                record = _record(args, policy, spec, clock, "approve-plan")
                txn.write_spec(spec)
                txn.emit("scope.approved", {"record": scope_record})
            stage = txn.state.get("resume_stage")
            questions = [dict(q, status="answered") if q.get("type") == "plan-policy-changed"
                         and q.get("asked_by") == "engine" else q
                         for q in txn.state.get("questions", [])]
            updates = {"approval": record,
                       "approval_history": [*txn.state.get("approval_history", []), record],
                       "plan_hash": record["plan_hash"]}
            if command == "approve" or (
                current == "needs-you"
                and txn.state.get("approval_reason") == "plan or policy changed"
            ):
                updates.update(questions=questions, status=stage or "approved",
                               resume_stage=None, approval_reason=None, needs_run=True)
            kind = "approval.recorded"
            check_approval(record, project=project, task=task, plan_hash=record["plan_hash"],
                           policy_hash=record["policy_hash"],
                           used_nonces=approval_nonces({**txn.state, **updates}))
            result["record"] = record
        elif command in {"pause", "resume", "cancel"}:
            current = txn.state.get("status")
            if current in {"committed", "delivered", "cancelled"}:
                raise ValueError("control requires an unfinished task")
            record = _record(args, policy, store.read_spec(project, task), clock, command)
            if command == "resume":
                if current != "paused":
                    raise ValueError("resume requires a paused task")
                updates = {"status": txn.state.get("paused_stage") or "approved", "paused_stage": None}
            elif command == "pause":
                if current == "paused":
                    raise ValueError("task already paused")
                updates = {"status": "paused", "paused_stage": current}
            else:
                updates = {"status": "cancelled", "needs_run": False}
            updates["control_history"] = [*txn.state.get("control_history", []), record]
            kind = "control.recorded"
            result["record"] = record
        elif command == "answer":
            question = _stored_question(txn.state, args.qid)
            if question.get("status") not in {"open", "draft"} or args.qid in txn.state.get("answers", {}):
                raise ValueError("question is not open or already answered")
            if args.option and args.option not in [o["label"] for o in question["options"]]:
                raise ValueError("option must match a question option")
            record = _record(args, policy, store.read_spec(project, task), clock, "answer",
                             question_id=args.qid, answer=args.option or args.quote)
            updates = {"answers": {**txn.state.get("answers", {}), args.qid: record}}
            kind = "answer.recorded"
            result["answer"] = record
        txn.state.update(updates)
        txn.emit(kind, {"set": updates, **({"record": record} if command in {"approve", "approve-scope", "answer", "pause", "resume", "cancel"} else {})})
    if command in {"ask", "answer", "approve", "approve-scope"}:
        _mirror(store, project, task)
    return result


def main(
    argv: list[str] | None = None,
    *,
    hub_root: Path | None = None,
    clock: Callable = lambda: datetime.now(timezone.utc),
) -> int:
    try:
        ensure_not_worker(os.environ, Path.cwd(), Path(hub_root or Path(__file__).resolve().parent) / "projects")
        args = _parser().parse_args(argv)
        root = Path(hub_root or Path(__file__).resolve().parent).resolve()
        policy = load_policy(root)
        ensure_not_worker(os.environ, Path.cwd(), expand(policy.data_root))
        result = _execute(args, StateStore(root), policy, clock)
        print(json.dumps({"ok": True, **result}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, PolicyError, yaml.YAMLError):
        message = str(sys.exc_info()[1])
        print(json.dumps({"ok": False, "error": message}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
