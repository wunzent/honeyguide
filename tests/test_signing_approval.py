from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

import owner_console
import signing
import state_writer
from owner_console import (
    ConsoleRequired, compute_manifest, load_questions, main,
    read_console_confirmation, read_console_passphrase,
)
from signing import (
    SigningError, VerificationError, canonical, fingerprint, generate_keypair,
    load_private_key, load_public_key, sha256_file, sha256_text, sign_record, verify_record,
)
from state_writer import StateStore, get_approval_block, plan_hash, plan_section, set_approval_block


PASSPHRASE = "throwaway test passphrase"
MOMENT = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
SPEC = "# Task\n\n## Proposed Plan\n\nImplement the scoped feature.\n\n## Notes\nPreserve this.\n"


def public_bytes(key) -> bytes:
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def fields(key, **changes) -> dict:
    result = {"kind": "approve-plan", "project": "project", "task": "T-1",
              "plan_hash": plan_hash(SPEC), "policy_hash": "", "question_id": "", "answer": "",
              "nonce": "a" * 32, "issued_at": MOMENT.isoformat(),
              "key_fingerprint": fingerprint(public_bytes(key.public_key()))}
    result.update(changes)
    return result


def confirm(prompt: str) -> str:
    return prompt.split("(")[1].split(")")[0]


@pytest.fixture
def keys(tmp_path):
    secret = tmp_path / "secrets"
    pub = tmp_path / "config" / "owner.pub"
    fp = generate_keypair(PASSPHRASE, secret, pub, kdf_n=2**14)
    return secret, pub, fp


@pytest.fixture
def hub(tmp_path, keys):
    secret, pub, _ = keys
    store = StateStore(tmp_path, replace_backoff=0)
    store.write_spec("project", "T-1", SPEC)
    with store.transaction("project", "T-1") as txn:
        updates = {"status": "awaiting-approval"}
        txn.state.update(updates)
        txn.emit("approval.requested", {"set": updates})
    (tmp_path / "config" / "policy.toml").write_text('mode = "manual"\n', encoding="utf-8")

    def invoke(argv, **changes):
        options = {"hub_root": tmp_path, "secret_dir": secret, "pub_path": pub,
                   "passphrase_reader": lambda: PASSPHRASE, "confirm_reader": confirm,
                   "now": lambda: MOMENT}
        options.update(changes)
        return main(argv, **options)

    assert invoke(["sign-policy"]) == 0
    assert invoke(["sign-manifest"]) == 0
    return store, invoke, secret, pub


def test_keygen_encrypted_roundtrip(keys):
    secret, pub, fp = keys
    data = json.loads((secret / "owner.key.enc").read_text(encoding="utf-8"))
    assert {name: data[name] for name in ("version", "kdf", "n", "r", "p", "aead")} == {
        "version": 1, "kdf": "scrypt", "n": 2**14, "r": 8, "p": 1, "aead": "AES-256-GCM"}
    assert len(base64.b64decode(data["salt"])) == 16
    assert len(base64.b64decode(data["nonce"])) == 12
    assert len(base64.b64decode(data["ciphertext"])) == 48
    assert pub.read_bytes().endswith(b"\n")
    public = load_public_key(pub)
    assert fingerprint(public_bytes(public)) == fp == data["fingerprint"]
    private = load_private_key(secret, PASSPHRASE)
    record = sign_record(private, fields(private))
    assert verify_record(public, record, {"kind": "approve-plan", "task": "T-1"}) is None
    assert set(record) == signing.FIELDS | {"signature"}


def test_default_kdf_cost_without_expensive_derivation(tmp_path, monkeypatch):
    derive = signing.hashlib.scrypt
    costs = []

    def fast(password, **kwargs):
        costs.append((kwargs["n"], kwargs["r"], kwargs["p"], kwargs["maxmem"], kwargs["dklen"]))
        return derive(password, **{**kwargs, "n": 2**14})

    monkeypatch.setattr(signing.hashlib, "scrypt", fast)
    generate_keypair(PASSPHRASE, tmp_path / "secret", tmp_path / "owner.pub")
    assert costs == [(2**17, 8, 1, 256 * 1024 * 1024, 32)]


def test_wrong_passphrase_has_no_detail(keys):
    secret, _, _ = keys
    with pytest.raises(SigningError, match="^could not unlock owner key$"):
        load_private_key(secret, "another throwaway passphrase")


@pytest.mark.parametrize("damage", ["ciphertext", "fingerprint", "n", "r", "version"])
def test_malformed_encrypted_key(keys, damage):
    secret, _, _ = keys
    path = secret / "owner.key.enc"
    data = json.loads(path.read_text(encoding="utf-8"))
    data[damage] = "invalid"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SigningError, match="^could not unlock owner key$"):
        load_private_key(secret, PASSPHRASE)


@pytest.mark.parametrize("passphrase", ["", "x" * 15])
def test_short_passphrase(tmp_path, passphrase):
    with pytest.raises(SigningError):
        generate_keypair(passphrase, tmp_path / "secret", tmp_path / "pub", kdf_n=2**14)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("existing", ["private", "public", "both"])
def test_no_overwrite(tmp_path, existing):
    secret, pub = tmp_path / "secret", tmp_path / "owner.pub"
    secret.mkdir()
    if existing in {"private", "both"}:
        (secret / "owner.key.enc").write_bytes(b"preserve private placeholder")
    if existing in {"public", "both"}:
        pub.write_bytes(b"preserve public placeholder")
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(SigningError):
        generate_keypair(PASSPHRASE, secret, pub, kdf_n=2**14)
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_canonical_and_hashes(tmp_path):
    assert canonical({"z": "ไทย", "a": 1}) == '{"a":1,"z":"ไทย"}'.encode()
    assert sha256_text("a\r\nb") == sha256_text("a\nb")
    path = tmp_path / "binary"
    path.write_bytes(b"a\r\nb\x00")
    assert sha256_file(path) == hashlib.sha256(b"a\r\nb\x00").hexdigest()


@pytest.mark.parametrize("change", [
    {"task": "T-2"}, {"plan_hash": "b" * 64}, {"policy_hash": "b" * 64},
    {"kind": "commit"}, {"nonce": "b" * 32}, {"issued_at": "2026-11-09T13:00:00+00:00"},
    {"signature": "invalid"}, {"key_fingerprint": "b" * 64},
])
def test_tampered_record(change):
    key = Ed25519PrivateKey.generate()
    record = sign_record(key, fields(key))
    with pytest.raises(VerificationError):
        verify_record(key.public_key(), {**record, **change}, {})


def test_other_key_signature_and_wrong_fingerprint():
    key, other = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    record = sign_record(other, fields(other))
    with pytest.raises(VerificationError):
        verify_record(key.public_key(), record, {})
    wrong = fields(key, key_fingerprint="b" * 64)
    forged = {**wrong, "signature": base64.b64encode(key.sign(canonical(wrong))).decode()}
    with pytest.raises(VerificationError):
        verify_record(key.public_key(), forged, {})
    with pytest.raises(SigningError):
        sign_record(key, wrong)


@pytest.mark.parametrize("change", [
    {"nonce": "bad"}, {"issued_at": "2026-11-09T12:00:00"}, {"kind": "auto-approve"},
    {"answer": "APPROVED"}, {"project": ""}, {"plan_hash": ""}, {"extra": "bad"},
])
def test_invalid_record_schema(change):
    key = Ed25519PrivateKey.generate()
    invalid = fields(key, **change)
    with pytest.raises(SigningError):
        sign_record(key, invalid)
    invalid["signature"] = base64.b64encode(key.sign(canonical(invalid))).decode()
    with pytest.raises(VerificationError):
        verify_record(key.public_key(), invalid, {})


def test_missing_field_and_expected_mismatch():
    key = Ed25519PrivateKey.generate()
    record = sign_record(key, fields(key))
    for expected in ({"plan_hash": plan_hash(SPEC.replace("feature", "revision"))},
                     {"project": "other"}, {"kind": "commit"}, {"missing": ""}):
        with pytest.raises(VerificationError):
            verify_record(key.public_key(), record, expected)
    record.pop("answer")
    with pytest.raises(VerificationError):
        verify_record(key.public_key(), record, {})


def test_answer_replay_for_other_question_fails():
    key = Ed25519PrivateKey.generate()
    record = sign_record(key, fields(key, kind="answer", question_id="q1", answer="yes"))
    assert verify_record(key.public_key(), record, {"kind": "answer", "question_id": "q1"}) is None
    with pytest.raises(VerificationError):
        verify_record(key.public_key(), record, {"kind": "answer", "question_id": "q2"})


def test_spec_helpers_and_approval_roundtrip(tmp_path):
    store = StateStore(tmp_path)
    store.write_spec("project", "T-1", SPEC)
    assert store.read_spec("project", "T-1") == SPEC
    assert plan_section(SPEC) == "Implement the scoped feature."
    assert plan_hash(SPEC) == sha256_text(plan_section(SPEC))
    assert plan_hash(SPEC) != plan_hash(SPEC.replace("feature", "revision"))
    assert plan_hash(SPEC) == plan_hash(SPEC.replace("\n", "\r\n"))
    assert get_approval_block(SPEC) is None
    record = {"example": "data only", "answer": "```\n## Heading"}
    updated = set_approval_block(SPEC, record)
    assert get_approval_block(updated) == record
    assert plan_hash(updated) == plan_hash(SPEC)
    assert get_approval_block(set_approval_block(updated, {"replacement": True})) == {"replacement": True}
    assert set_approval_block(updated, record).count("## Approval\n") == 1
    assert "## Notes\nPreserve this." in updated
    middle = "## Approval\n\nold\n\n" + SPEC
    assert SPEC[SPEC.index("## Proposed Plan"):] in set_approval_block(middle, record)
    assert get_approval_block(set_approval_block(middle, record)) == record


def test_plan_headings_inside_fences_are_content():
    text = "## Proposed Plan\n```md\n## Nested example\n```\nPlan continues.\n## Other\nEnd"
    assert plan_section(text) == "```md\n## Nested example\n```\nPlan continues."


@pytest.mark.parametrize("text", ["none", "## Proposed Plan\n\n", "## Proposed Plan\nA\n## Proposed Plan\nB",
                                  "## Proposed Plan\nUnclosed example\n```md\n## Approval\n"])
def test_invalid_plan(text):
    with pytest.raises(ValueError):
        plan_hash(text)


@pytest.mark.parametrize("body", ["APPROVED", "```hub-approval\n[]\n```", "```hub-approval\ninvalid\n```",
                                   "```hub-approval\n{}\n```\n```hub-approval\n{}\n```"])
def test_invalid_approval_blocks(body):
    with pytest.raises(ValueError):
        get_approval_block("## Approval\n" + body)


def test_duplicate_approval_sections_fail_closed():
    text = "## Approval\nA\n## Approval\nB"
    with pytest.raises(ValueError):
        get_approval_block(text)
    with pytest.raises(ValueError):
        set_approval_block(text, {})


def test_spec_atomic_permission_retry(tmp_path, monkeypatch):
    store = StateStore(tmp_path, replace_backoff=0)
    replace = state_writer.os.replace
    calls = []

    def flaky(source, target):
        calls.append(target)
        if len(calls) == 1:
            raise PermissionError("sharing violation")
        replace(source, target)

    monkeypatch.setattr(state_writer.os, "replace", flaky)
    store.write_spec("project", "T-1", SPEC)
    assert len(calls) == 2
    assert store.read_spec("project", "T-1") == SPEC


@pytest.mark.parametrize("isatty,window", [(False, 1), (True, 0), (False, 0)])
def test_console_required_when_piped_or_no_window(monkeypatch, isatty, window):
    monkeypatch.setattr(owner_console.sys, "stdin", SimpleNamespace(isatty=lambda: isatty))
    monkeypatch.setattr(owner_console.ctypes, "windll", SimpleNamespace(
        kernel32=SimpleNamespace(GetConsoleWindow=lambda: window)), raising=False)
    monkeypatch.setattr(owner_console.getpass, "getpass", lambda _: pytest.fail("must not prompt"))
    for reader, args in ((read_console_passphrase, ()), (read_console_confirmation, ("confirm",))):
        with pytest.raises(ConsoleRequired):
            reader(*args)


def test_real_console_readers_delegate_only_after_gate(monkeypatch):
    monkeypatch.setattr(owner_console.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(owner_console.ctypes, "windll", SimpleNamespace(
        kernel32=SimpleNamespace(GetConsoleWindow=lambda: 1)), raising=False)
    monkeypatch.setattr(owner_console.getpass, "getpass", lambda _: "injected")
    monkeypatch.setattr("builtins.input", lambda _: "confirmed")
    if owner_console.os.name == "nt":
        assert read_console_passphrase() == "injected"
        assert read_console_confirmation("prompt") == "confirmed"


def test_approve_writes_verified_block_and_replayable_event(hub, capsys):
    store, invoke, _, pub = hub
    capsys.readouterr()
    assert invoke(["approve", "project", "T-1"]) == 0
    output = capsys.readouterr().out
    assert plan_section(SPEC) in output and plan_hash(SPEC) in output
    assert PASSPHRASE not in output
    record = get_approval_block(store.read_spec("project", "T-1"))
    verify_record(load_public_key(pub), record, {"kind": "approve-plan", "plan_hash": plan_hash(SPEC)})
    state = store.read_state("project", "T-1")
    assert state["status"] == "approved" and state["approval"] == record
    assert record["issued_at"] == MOMENT.isoformat()
    event = store.read_events("project", "T-1")[-1]
    assert event.kind == "approval.signed" and event.data["record"] == record
    assert state_writer.apply_event({}, event)["approval"] == record
    assert invoke(["verify", "project", "T-1"]) == 0
    assert json.loads(capsys.readouterr().out)["approval_valid"] is True


@pytest.mark.parametrize("status", ["draft", "approved", "running", "done"])
def test_approve_refuses_other_status(hub, status):
    store, invoke, _, _ = hub
    with store.transaction("project", "T-1") as txn:
        txn.state["status"] = status
        txn.emit("status.updated", {"set": {"status": status}})
    before = store.read_events("project", "T-1")
    assert invoke(["approve", "project", "T-1"],
                  passphrase_reader=lambda: pytest.fail("must refuse before unlocking")) == 2
    assert store.read_events("project", "T-1") == before
    assert get_approval_block(store.read_spec("project", "T-1")) is None


@pytest.mark.parametrize("forgery", ["result", "handwritten", "other-key", "old-plan"])
def test_verify_rejects_untrusted_approval(hub, capsys, forgery):
    store, invoke, _, _ = hub
    if forgery == "result":
        (store.task_dir("project", "T-1") / "result.md").write_text("APPROVED", encoding="utf-8")
    elif forgery == "handwritten":
        store.write_spec("project", "T-1", set_approval_block(SPEC, {"status": "APPROVED"}))
    elif forgery == "other-key":
        key = Ed25519PrivateKey.generate()
        store.write_spec("project", "T-1", set_approval_block(SPEC, sign_record(key, fields(key))))
    else:
        assert invoke(["approve", "project", "T-1"]) == 0
        store.write_spec("project", "T-1", store.read_spec("project", "T-1").replace("feature", "revision"))
    capsys.readouterr()
    assert invoke(["verify", "project", "T-1"]) == 2
    assert json.loads(capsys.readouterr().out)["approval_valid"] is False


@pytest.mark.parametrize("change", ["plan", "policy", "public-key", "source", "status"])
def test_change_during_confirmation_refused(hub, change):
    store, invoke, _, pub = hub

    def edit(prompt):
        if change == "plan":
            store.write_spec("project", "T-1", SPEC.replace("feature", "revision"))
        elif change == "policy":
            (store.root / "config" / "policy.toml").write_text('mode = "changed"', encoding="utf-8")
        elif change == "public-key":
            pub.write_bytes(base64.b64encode(public_bytes(Ed25519PrivateKey.generate().public_key())) + b"\n")
        elif change == "source":
            (store.root / "changed.py").write_text("# changed", encoding="utf-8")
        else:
            with store.transaction("project", "T-1") as txn:
                txn.state["status"] = "running"
                txn.emit("status.updated", {"set": {"status": "running"}})
        return confirm(prompt)

    assert invoke(["approve", "project", "T-1"], confirm_reader=edit) == 2
    assert get_approval_block(store.read_spec("project", "T-1")) is None
    assert not any(event.kind == "approval.signed" for event in store.read_events("project", "T-1"))


def write_questions(store, body=None):
    if body is None:
        body = ('- id: q1\n  class: owner-signed\n  status: open\n  options: [yes, no]\n'
                '- id: q2\n  class: relay\n  status: open\n  options: []\n')
    path = store.task_dir("project", "T-1") / "questions.md"
    path.write_text("# Questions\n\n```hub-questions\n" + body + "```\n", encoding="utf-8")
    return path


def test_answer_owner_signed_only_and_recorded_in_state(hub):
    store, invoke, _, pub = hub
    path = write_questions(store)
    original = path.read_bytes()
    assert len(load_questions(path)) == 2
    assert invoke(["answer", "project", "T-1", "q2", "--answer", "yes"]) == 2
    assert invoke(["answer", "project", "T-1", "missing", "--answer", "yes"]) == 2
    assert invoke(["answer", "project", "T-1", "q1", "--answer", "ไทย"]) == 0
    record = store.read_state("project", "T-1")["answers"]["q1"]
    verify_record(load_public_key(pub), record, {"kind": "answer", "question_id": "q1", "answer": "ไทย"})
    event = store.read_events("project", "T-1")[-1]
    assert event.kind == "answer.signed" and event.data["record"] == record
    assert state_writer.apply_event({}, event)["answers"]["q1"] == record
    assert path.read_bytes() == original
    assert invoke(["answer", "project", "T-1", "q1", "--answer", "again"]) == 2


@pytest.mark.parametrize("body", ["{}\n", "- id: q1\n", "- [bad]\n", "[\n",
                                  '- {id: q1, class: relay, status: open, options: []}\n' * 2])
def test_invalid_questions_fail_closed(tmp_path, body):
    store = StateStore(tmp_path)
    store.task_dir("project", "T-1").mkdir(parents=True)
    with pytest.raises(ValueError):
        load_questions(write_questions(store, body))


def test_answer_refuses_changed_or_closed_question(hub):
    store, invoke, _, _ = hub
    path = write_questions(store)

    def edit(prompt):
        path.write_text(path.read_text(encoding="utf-8").replace("status: open", "status: answered"), encoding="utf-8")
        return confirm(prompt)

    assert invoke(["answer", "project", "T-1", "q1", "--answer", "yes"], confirm_reader=edit) == 2
    assert invoke(["answer", "project", "T-1", "q1", "--answer", "yes"]) == 2
    assert "answers" not in store.read_state("project", "T-1")


@pytest.mark.parametrize("command", ["resume", "commit"])
def test_resume_commit_only_record_permission(hub, command):
    store, invoke, _, pub = hub
    assert invoke([command, "project", "T-1"]) == 0
    state = store.read_state("project", "T-1")
    verify_record(load_public_key(pub), state[command], {"kind": command, "plan_hash": plan_hash(SPEC)})
    assert state["status"] == "awaiting-approval"
    assert store.read_events("project", "T-1")[-1].kind == command + ".signed"
    assert not (store.root / ".git").exists()


def test_manifest_inclusions_and_exclusions(tmp_path):
    included = ["main.py", "nested/module.py", "hooks/check.py", "agents/coder.md", "config/policy.toml",
                "config/owner.pub", "AGENTS.md", "CLAUDE.md", ".claude/settings.json"]
    excluded = [".venv/pkg.py", "tests/test_x.py", "runtime/run.py", "projects/project/source.py",
                "config/manifest.json", "config/manifest.sig", "agents/readme.txt", "docs/README.md"]
    for relative in included + excluded:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    manifest = compute_manifest(tmp_path)
    assert set(manifest) == set(included)
    assert all(manifest[name] == sha256_file(tmp_path / name) for name in included)
    assert list(manifest) == sorted(manifest)


def test_sign_policy_and_manifest_bind_exact_bytes(hub):
    store, _, _, pub = hub
    public = load_public_key(pub)
    config = store.root / "config"
    policy_record = json.loads((config / "policy.toml.sig").read_text(encoding="utf-8"))
    verify_record(public, policy_record, {"kind": "sign-policy", "policy_hash": sha256_file(config / "policy.toml")})
    manifest = json.loads((config / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == compute_manifest(store.root)
    record = json.loads((config / "manifest.sig").read_text(encoding="utf-8"))
    verify_record(public, record, {"kind": "sign-manifest", "policy_hash": hashlib.sha256(canonical(manifest)).hexdigest()})
    assert all(record[name] == "" for name in ("project", "task", "plan_hash", "question_id", "answer"))


@pytest.mark.parametrize("tamper", ["source", "manifest", "manifest-signature", "policy", "policy-signature", "key"])
def test_trust_tampering_refuses_task_signing(hub, tamper):
    store, invoke, _, pub = hub
    config = store.root / "config"
    if tamper == "source":
        (store.root / "new.py").write_text("# unsigned", encoding="utf-8")
    elif tamper == "key":
        pub.write_text("invalid public key", encoding="utf-8")
    else:
        name = {"manifest": "manifest.json", "manifest-signature": "manifest.sig", "policy": "policy.toml",
                "policy-signature": "policy.toml.sig"}[tamper]
        (config / name).write_text("{}", encoding="utf-8")
    assert invoke(["approve", "project", "T-1"],
                  passphrase_reader=lambda: pytest.fail("must refuse before unlocking")) == 2
    assert get_approval_block(store.read_spec("project", "T-1")) is None


def test_missing_manifest_refused_and_missing_policy_supported(hub):
    store, invoke, _, _ = hub
    (store.root / "config" / "manifest.sig").unlink()
    assert invoke(["approve", "project", "T-1"]) == 2
    (store.root / "config" / "policy.toml").unlink()
    assert invoke(["sign-manifest"]) == 0
    assert invoke(["approve", "project", "T-1"]) == 0
    assert store.read_state("project", "T-1")["approval"]["policy_hash"] == ""


def test_confirmation_mismatch_and_console_exit_codes(hub, monkeypatch):
    store, invoke, _, _ = hub
    assert invoke(["approve", "project", "T-1"], confirm_reader=lambda _: "wrong") == 2
    monkeypatch.setattr(owner_console.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert invoke(["approve", "project", "T-1"], confirm_reader=None) == 3
    assert invoke(["approve", "project", "T-1"], passphrase_reader=None) == 3
    assert get_approval_block(store.read_spec("project", "T-1")) is None


def test_init_and_argument_errors(tmp_path, monkeypatch):
    original = owner_console.generate_keypair

    def fast(passphrase, secret_dir, pub_path):
        return original(passphrase, secret_dir, pub_path, kdf_n=2**14)

    monkeypatch.setattr(owner_console, "generate_keypair", fast)
    options = {"hub_root": tmp_path, "secret_dir": tmp_path / "secret", "pub_path": tmp_path / "config" / "owner.pub",
               "passphrase_reader": lambda: PASSPHRASE}
    assert main(["init"], **options) == 0
    assert main(["init"], **options) == 2
    assert main(["invalid"], **options) == 2
    assert main(["answer", "project", "T-1", "q1"], **options) == 2


def test_nonce_reuse_refused(hub, monkeypatch):
    store, invoke, _, _ = hub
    monkeypatch.setattr(owner_console.secrets, "token_hex", lambda _: "c" * 32)
    assert invoke(["resume", "project", "T-1"]) == 0
    assert invoke(["commit", "project", "T-1"]) == 2
    assert "commit" not in store.read_state("project", "T-1")


@pytest.mark.parametrize("command", ["sign-policy", "sign-manifest"])
def test_configuration_changed_during_confirmation_refused(hub, command):
    store, invoke, _, _ = hub
    config = store.root / "config"
    signature = config / ("policy.toml.sig" if command == "sign-policy" else "manifest.sig")
    before = signature.read_bytes()

    def edit(prompt):
        (config / "policy.toml").write_text('mode = "revised"', encoding="utf-8")
        return confirm(prompt)

    assert invoke([command], confirm_reader=edit) == 2
    assert signature.read_bytes() == before


def test_wrong_passphrase_never_publishes_record(hub, capsys):
    store, invoke, _, _ = hub
    capsys.readouterr()
    assert invoke(["approve", "project", "T-1"],
                  passphrase_reader=lambda: "wrong throwaway passphrase") == 2
    output = capsys.readouterr()
    assert not any(value in output.out + output.err for value in (PASSPHRASE, "wrong throwaway passphrase"))
    assert get_approval_block(store.read_spec("project", "T-1")) is None
    assert store.read_state("project", "T-1")["status"] == "awaiting-approval"


def test_invalid_public_key(tmp_path):
    path = tmp_path / "owner.pub"
    for data in ("not base64", base64.b64encode(b"short").decode()):
        path.write_text(data, encoding="utf-8")
        with pytest.raises(SigningError):
            load_public_key(path)
