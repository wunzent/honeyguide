from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import re
import secrets
from typing import Mapping, Iterable


class ApprovalError(ValueError):
    pass


class WorkerContextError(ValueError):
    pass


KINDS = frozenset({"approve-plan", "answer", "approve-scope", "pause", "resume", "cancel"})


def _validate(record: dict) -> None:
    try:
        if record["kind"] not in KINDS or record["recorded_by"] != "orchestrator":
            raise ValueError("invalid record origin or kind")
        if record["desktop"] not in {"claude", "codex"}:
            raise ValueError("invalid desktop")
        quote = record["quote"]
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 2000:
            raise ValueError("quote must contain owner words and be at most 2000 characters")
        if not re.fullmatch(r"[0-9a-f]{32}", record["nonce"]):
            raise ValueError("invalid nonce")
        if datetime.fromisoformat(record["at"]).utcoffset() is None:
            raise ValueError("record time requires an offset")
        for name in ("project", "task", "plan_hash", "policy_hash"):
            if not isinstance(record[name], str) or not record[name]:
                raise ValueError(f"missing {name}")
        for name in ("question_id", "answer"):
            if not isinstance(record[name], str):
                raise ValueError(f"invalid {name}")
        if record["kind"] == "answer" and not record["question_id"]:
            raise ValueError("answer requires a question")
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ApprovalError(f"invalid conversational record: {exc}") from None


def build_record(kind: str, *, project: str, task: str, plan_hash: str,
                 policy_hash: str, quote: str, desktop: str, question_id: str = "",
                 answer: str = "", extra: dict | None = None, now: datetime) -> dict:
    record = dict(kind=kind, project=project, task=task, plan_hash=plan_hash,
                  policy_hash=policy_hash, quote=quote, desktop=desktop,
                  question_id=question_id, answer=answer, nonce=secrets.token_hex(16),
                  recorded_by="orchestrator", at=now.isoformat())
    if extra is not None:
        if not isinstance(extra, dict):
            raise ApprovalError("extra must be a mapping")
        record["extra"] = dict(extra)
    _validate(record)
    return record


def check_record(record: dict, *, kind: str, project: str, task: str,
                 plan_hash: str, policy_hash: str, used_nonces: Iterable[str],
                 question_id: str = "") -> None:
    _validate(record)
    expected = dict(kind=kind, project=project, task=task, plan_hash=plan_hash,
                    policy_hash=policy_hash, question_id=question_id)
    if any(record.get(key) != value for key, value in expected.items()):
        raise ApprovalError("record binding mismatch")
    if record["nonce"] in used_nonces:
        raise ApprovalError("record nonce already consumed or duplicated")


def check_approval(record: dict, *, project: str, task: str, plan_hash: str,
                   policy_hash: str, used_nonces: Iterable[str]) -> None:
    check_record(record, kind="approve-plan", project=project, task=task,
                 plan_hash=plan_hash, policy_hash=policy_hash, used_nonces=used_nonces)


def approval_nonces(state: dict) -> set[str]:
    """The current approval may occur once in history and cover many runs."""
    current = state.get("approval") or {}
    counts = Counter(record["nonce"] for record in state.get("approval_history", []))
    return set(state.get("used_nonces", [])) | {
        nonce for nonce, count in counts.items()
        if count > 1 or nonce != current.get("nonce")
    }


def ensure_not_worker(env: Mapping[str, str], cwd: Path, data_root: Path) -> None:
    """Deterrence/workflow control, not a security boundary."""
    if env.get("HUB_WORKER") == "1" or "HUB_RUN_TOKEN" in env:
        raise WorkerContextError("bridge refused in worker environment")
    if Path(cwd).resolve().is_relative_to(Path(data_root).resolve()):
        raise WorkerContextError("bridge refused from inside data root")
