"""Validate and audit exact Desktop delegation routes without substitution."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from adapters.base import Availability, Route
from model_router import RouteError, default_effort, load_catalog, resolve
from policy import load_policy


ROOT = Path(__file__).resolve().parent
ROUTINE_ONLY_MODELS = {"gpt-6-luna", "haiku", "claude-haiku-5-5"}
EFFORTS = ["low", "medium", "high"]


def check(role, tier, vendor, model, effort, reason, escalation=None):
    policy = load_policy(ROOT)
    catalog = load_catalog(ROOT / "config/models.toml")
    requested = Route(vendor, model, effort)
    route, reasons = resolve(
        requested, role, policy=policy, catalog=catalog,
        availability={v: Availability(True, "desktop", True, "") for v in catalog},
        quota_blocked=set(), allow_premium=False,
    )
    if route != requested or reasons:
        raise RouteError("exact route required; substitution or routing reasons refused")
    if len(reason.strip()) < 10:
        raise RouteError("reason must contain at least 10 characters")
    if model in ROUTINE_ONLY_MODELS and tier != "routine":
        raise RouteError("routine-only model requires routine tier")
    d = default_effort(policy, role, tier)
    if effort not in EFFORTS:
        raise RouteError("effort may not exceed high")
    if EFFORTS.index(effort) > EFFORTS.index(d) and len((escalation or "").strip()) < 10:
        raise RouteError("effort above default requires escalation of at least 10 characters")
    if tier == "complex" and EFFORTS.index(effort) < EFFORTS.index(d):
        raise RouteError("complex tier effort may not be below default")
    return dict(role=role, tier=tier, vendor=vendor, model=model, effort=effort,
                default_effort=d, escalation=escalation)


def record(obj, log=None):
    path = Path(log) if log else ROOT / "runtime/desktop-delegations.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({**obj, "at": datetime.now(timezone.utc).isoformat()}) + "\n")


def json_lines(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        for line in stream:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def verify_codex(events, sessions_dir=None):
    thread = next((e.get("thread_id") for e in json_lines(events)
                   if e.get("type") == "thread.started"), None)
    result = dict(thread=thread, actual_model=None, actual_effort=None,
                  total_tokens=None, evidence=None)
    directory = Path(sessions_dir) if sessions_dir else Path.home() / ".codex/sessions"
    if not isinstance(thread, str) or not thread:
        return result
    matches = sorted(p for p in directory.rglob("rollout-*.jsonl")
                     if p.name.endswith(thread + ".jsonl"))
    if not matches:
        return result
    path = matches[-1]
    result["evidence"] = str(path)
    for event in json_lines(path):
        payload = event.get("payload", {})
        if event.get("type") == "turn_context":
            result.update(actual_model=payload.get("model"), actual_effort=payload.get("effort"))
        if payload.get("type") == "token_count":
            result["total_tokens"] = (payload.get("info") or {}).get("total_token_usage", {}).get("total_tokens")
    return result


def verify_claude(transcript):
    return {"actual_models": sorted({e["message"]["model"] for e in json_lines(transcript)
                                    if e.get("type") == "assistant"
                                    and isinstance(e.get("message", {}).get("model"), str)})}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validation = commands.add_parser("check")
    for flag in ("role", "vendor", "model", "effort", "reason"):
        validation.add_argument("--" + flag, required=True)
    validation.add_argument("--tier", choices=["routine", "standard", "complex"], required=True)
    validation.add_argument("--escalation")
    recording = commands.add_parser("record")
    recording.add_argument("--json", required=True)
    recording.add_argument("--log")
    codex = commands.add_parser("verify-codex")
    codex.add_argument("--events", required=True)
    codex.add_argument("--sessions-dir")
    claude = commands.add_parser("verify-claude")
    claude.add_argument("--transcript", required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    if command == "check":
        try:
            result = check(**args)
        except RouteError as exc:
            print(f"REFUSED: {exc}")
            return 2
    elif command == "record":
        record(json.loads(args["json"]), args["log"])
        return 0
    elif command == "verify-codex":
        result = verify_codex(**args)
    else:
        result = verify_claude(**args)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
