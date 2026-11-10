from __future__ import annotations

import argparse
import ctypes
import getpass
import hashlib
import json
import os
import re
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from signing import (
    canonical,
    fingerprint,
    generate_keypair,
    load_private_key,
    load_public_key,
    sha256_file,
    sign_record,
    verify_record,
)
from state_writer import (
    StateStore,
    atomic_write_text,
    get_approval_block,
    plan_hash,
    plan_section,
    read_text_retry,
    set_approval_block,
)


class ConsoleRequired(RuntimeError):
    pass


def _require_console() -> None:
    if (
        os.name != "nt"
        or not sys.stdin.isatty()
        or not ctypes.windll.kernel32.GetConsoleWindow()
    ):
        raise ConsoleRequired("an owner-opened Windows console is required")


def read_console_passphrase() -> str:
    _require_console()
    return getpass.getpass("Owner passphrase: ")


def read_console_confirmation(prompt: str) -> str:
    _require_console()
    return input(prompt)


def load_questions(path: Path) -> list[dict]:
    text = read_text_retry(path)
    blocks = re.findall(r"^```hub-questions\r?\n(.*?)^```[ \t]*\r?$", text, re.M | re.S)
    if len(blocks) != 1:
        raise ValueError("questions must contain one hub-questions block")
    try:
        questions = yaml.safe_load(blocks[0])
    except yaml.YAMLError:
        raise ValueError("invalid questions YAML") from None
    if not isinstance(questions, list):
        raise ValueError("questions must be a list")
    ids = set()
    for question in questions:
        if (
            not isinstance(question, dict)
            or not isinstance(question.get("id"), str)
            or not question["id"]
            or question["id"] in ids
            or not isinstance(question.get("class"), str)
            or question.get("class") not in {"owner-signed", "relay"}
            or not isinstance(question.get("status"), str)
            or not isinstance(question.get("options"), list)
        ):
            raise ValueError("invalid or duplicate question")
        ids.add(question["id"])
    return questions


def compute_manifest(hub_root: Path) -> dict:
    root = hub_root.resolve()
    excluded = {
        ".venv",
        ".git",
        "tests",
        "runtime",
        "projects",
        "__pycache__",
        ".pytest_cache",
    }
    manifest = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        dirs[:] = sorted(name for name in dirs if name.casefold() not in excluded)
        for name in dirs:
            child = parent / name
            if child.is_symlink() or child.resolve() != child:
                raise ValueError("manifest directory aliases are not allowed")
        for name in sorted(files):
            path = parent / name
            relative = path.relative_to(root)
            key = relative.as_posix()
            include = (
                path.suffix == ".py"
                or (
                    len(relative.parts) == 2
                    and relative.parts[0] == "agents"
                    and path.suffix == ".md"
                )
                or (
                    len(relative.parts) == 2
                    and relative.parts[0] == "config"
                    and path.suffix == ".toml"
                )
                or key
                in {
                    "config/owner.pub",
                    "AGENTS.md",
                    "CLAUDE.md",
                    ".claude/settings.json",
                }
            )
            if include:
                if path.is_symlink() or path.resolve() != path:
                    raise ValueError("manifest file aliases are not allowed")
                manifest[key] = sha256_file(path)
    return dict(sorted(manifest.items()))


def _digest_manifest(manifest: dict) -> str:
    return hashlib.sha256(canonical(manifest)).hexdigest()


def _fingerprint(key: Ed25519PublicKey) -> str:
    return fingerprint(
        key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )


def _policy_hash(root: Path) -> str:
    path = root / "config" / "policy.toml"
    return sha256_file(path) if path.exists() else ""


def _trusted_snapshot(root: Path, pub_path: Path) -> tuple[str, str, str]:
    public_key = load_public_key(pub_path)
    config = root / "config"
    manifest = json.loads(read_text_retry(config / "manifest.json"))
    if not isinstance(manifest, dict) or manifest != compute_manifest(root):
        raise ValueError("source manifest mismatch")
    # The configured verification key must also be the key covered by the manifest.
    if manifest.get("config/owner.pub") != sha256_file(pub_path):
        raise ValueError("configured public key is not in the manifest")
    digest = _digest_manifest(manifest)
    record = json.loads(read_text_retry(config / "manifest.sig"))
    verify_record(public_key, record, {"kind": "sign-manifest", "policy_hash": digest})
    policy_hash = _policy_hash(root)
    if policy_hash:
        record = json.loads(read_text_retry(config / "policy.toml.sig"))
        verify_record(
            public_key, record, {"kind": "sign-policy", "policy_hash": policy_hash}
        )
    return policy_hash, digest, _fingerprint(public_key)


def _record(
    kind: str,
    key_fingerprint: str,
    now: Callable[[], datetime] | datetime | None,
    **bindings: str,
) -> dict:
    moment = now() if callable(now) else now
    if moment is None:
        moment = datetime.now().astimezone()
    fields = dict.fromkeys(
        ("project", "task", "plan_hash", "policy_hash", "question_id", "answer"), ""
    )
    fields.update(bindings)
    fields.update(
        kind=kind,
        nonce=secrets.token_hex(16),
        issued_at=moment.isoformat(),
        key_fingerprint=key_fingerprint,
    )
    return fields


def _confirm(reader: Callable[[str], str], digest: str) -> None:
    if (
        reader(f"Type the first 8 hash characters ({digest[:8]}) to confirm: ")
        != digest[:8]
    ):
        raise ValueError("confirmation refused")


def _sign(
    fields: dict, secret_dir: Path, pub_path: Path, passphrase_reader: Callable[[], str]
) -> dict:
    private = load_private_key(secret_dir, passphrase_reader())
    record = sign_record(private, fields)
    verify_record(load_public_key(pub_path), record, fields)
    return record


def _question(store: StateStore, project: str, task: str, qid: str) -> dict:
    questions = load_questions(store.task_dir(project, task) / "questions.md")
    question = next((item for item in questions if item["id"] == qid), None)
    if (
        question is None
        or question["class"] != "owner-signed"
        or question["status"] != "open"
    ):
        raise ValueError("question must be open and owner-signed")
    return question


def _task_command(
    args,
    root: Path,
    secret_dir: Path,
    pub_path: Path,
    passphrase_reader,
    confirm_reader,
    now,
) -> None:
    store = StateStore(root)
    project, task = args.project, args.task
    spec = store.read_spec(project, task)
    digest = plan_hash(spec)
    trust = _trusted_snapshot(root, pub_path)
    if (
        args.command == "approve"
        and store.read_state(project, task)["status"] != "awaiting-approval"
    ):
        raise ValueError("task is not awaiting approval")
    question = None
    bindings = {
        "project": project,
        "task": task,
        "plan_hash": digest,
        "policy_hash": trust[0],
    }
    if args.command == "answer":
        question = _question(store, project, task, args.qid)
        bindings.update(question_id=args.qid, answer=args.answer)
        print(
            json.dumps(
                {"question": question, "answer": args.answer}, ensure_ascii=False
            )
        )
    print(
        f"{args.command}: {project}/{task}\n"
        + "\n".join(plan_section(spec).splitlines()[:40])
    )
    print(f"Plan hash: {digest}\nPolicy hash: {trust[0]}")
    _confirm(confirm_reader, digest)
    kind = "approve-plan" if args.command == "approve" else args.command
    record = _sign(
        _record(kind, trust[2], now, **bindings),
        secret_dir,
        pub_path,
        passphrase_reader,
    )
    with store.transaction(project, task) as txn:
        current = store.read_spec(project, task)
        if plan_hash(current) != digest or _trusted_snapshot(root, pub_path) != trust:
            raise ValueError("signed content changed during confirmation")
        verify_record(load_public_key(pub_path), record, {"kind": kind, **bindings})
        if any(
            event.data.get("record", {}).get("nonce") == record["nonce"]
            for event in store.read_events(project, task)
        ):
            raise ValueError("nonce already recorded")
        if args.command == "approve":
            if txn.state["status"] != "awaiting-approval":
                raise ValueError("task is not awaiting approval")
            # transaction already holds the writer lock; do not acquire it recursively.
            atomic_write_text(
                store.task_dir(project, task) / "spec.md",
                set_approval_block(current, record),
                store.replace_retries,
                store.replace_backoff,
            )
            updates = {"approval": record, "status": "approved"}
            event = "approval.signed"
        elif args.command == "answer":
            if _question(
                store, project, task, args.qid
            ) != question or args.qid in txn.state.get("answers", {}):
                raise ValueError("question changed or was already answered")
            updates = {"answers": {**txn.state.get("answers", {}), args.qid: record}}
            event = "answer.signed"
        else:
            updates = {args.command: record}
            event = f"{args.command}.signed"
        txn.state.update(updates)
        txn.emit(event, {"record": record, "set": updates})
    print("Signed permission recorded.")


def _sign_config(
    command: str,
    root: Path,
    secret_dir: Path,
    pub_path: Path,
    passphrase_reader,
    confirm_reader,
    now,
) -> None:
    public_key = load_public_key(pub_path)
    manifest = compute_manifest(root) if command == "sign-manifest" else None
    digest = (
        _digest_manifest(manifest)
        if manifest is not None
        else sha256_file(root / "config" / "policy.toml")
    )
    print(f"{command}: {digest}")
    if manifest is not None:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(read_text_retry(root / "config" / "policy.toml"))
    _confirm(confirm_reader, digest)
    record = _sign(
        _record(command, _fingerprint(public_key), now, policy_hash=digest),
        secret_dir,
        pub_path,
        passphrase_reader,
    )
    store = StateStore(root)
    with store._writer_lock():
        current = (
            _digest_manifest(compute_manifest(root))
            if manifest is not None
            else _policy_hash(root)
        )
        if current != digest:
            raise ValueError("configuration changed during confirmation")
        verify_record(
            load_public_key(pub_path), record, {"kind": command, "policy_hash": digest}
        )
        if manifest is not None:
            atomic_write_text(
                root / "config" / "manifest.json",
                json.dumps(manifest, indent=2) + "\n",
                10,
                0.05,
            )
        name = "manifest.sig" if manifest is not None else "policy.toml.sig"
        atomic_write_text(
            root / "config" / name, json.dumps(record, indent=2) + "\n", 10, 0.05
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Owner-only signed permissions")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "sign-policy", "sign-manifest"):
        commands.add_parser(name)
    for name in ("approve", "answer", "resume", "commit", "verify"):
        command = commands.add_parser(name)
        command.add_argument("project")
        command.add_argument("task")
        if name == "answer":
            command.add_argument("qid")
            command.add_argument("--answer", required=True)
    return parser


def main(
    argv: list[str] | None,
    *,
    hub_root: Path,
    secret_dir: Path,
    pub_path: Path,
    passphrase_reader: Callable[[], str] | None = None,
    confirm_reader: Callable[[str], str] | None = None,
    now: Callable[[], datetime] | datetime | None = None,
) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    root = Path(hub_root)
    secret_dir, pub_path = Path(secret_dir), Path(pub_path)
    passphrase_reader = (
        passphrase_reader if passphrase_reader is not None else read_console_passphrase
    )
    confirm_reader = (
        confirm_reader if confirm_reader is not None else read_console_confirmation
    )
    try:
        if args.command == "verify":
            spec = StateStore(root).read_spec(args.project, args.task)
            trust = _trusted_snapshot(root, pub_path)
            record = get_approval_block(spec)
            verify_record(
                load_public_key(pub_path),
                record,
                {
                    "kind": "approve-plan",
                    "project": args.project,
                    "task": args.task,
                    "plan_hash": plan_hash(spec),
                    "policy_hash": trust[0],
                },
            )
            print(json.dumps({"approval_valid": True, "reason": "verified"}))
        elif args.command == "init":
            print("Creating the owner signing key.")
            print(
                "Owner fingerprint: "
                + generate_keypair(passphrase_reader(), secret_dir, pub_path)
            )
        elif args.command in {"sign-policy", "sign-manifest"}:
            _sign_config(
                args.command,
                root,
                secret_dir,
                pub_path,
                passphrase_reader,
                confirm_reader,
                now,
            )
        else:
            _task_command(
                args, root, secret_dir, pub_path, passphrase_reader, confirm_reader, now
            )
        return 0
    except ConsoleRequired:
        print("An owner-opened Windows console is required.", file=sys.stderr)
        return 3
    except (OSError, ValueError, TypeError, KeyError, AttributeError, EOFError):
        if args.command == "verify":
            print(
                json.dumps(
                    {
                        "approval_valid": False,
                        "reason": "missing, invalid, or stale signed content",
                    }
                )
            )
        else:
            print(
                "Refused: invalid input, failed verification, or content changed.",
                file=sys.stderr,
            )
        return 2


if __name__ == "__main__":
    hub = Path(__file__).resolve().parent
    raise SystemExit(
        main(
            sys.argv[1:],
            hub_root=hub,
            secret_dir=Path.home() / ".mah-v2-owner",
            pub_path=hub / "config" / "owner.pub",
        )
    )
