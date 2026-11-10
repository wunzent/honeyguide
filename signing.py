from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from state_writer import atomic_write_text, read_text_retry


class SigningError(ValueError):
    pass


class VerificationError(ValueError):
    pass


KINDS = frozenset(
    {"approve-plan", "answer", "resume", "commit", "sign-policy", "sign-manifest"}
)
FIELDS = frozenset(
    {
        "kind",
        "project",
        "task",
        "plan_hash",
        "policy_hash",
        "question_id",
        "answer",
        "nonce",
        "issued_at",
        "key_fingerprint",
    }
)


def canonical(fields: dict) -> bytes:
    return json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def fingerprint(pub_bytes: bytes) -> str:
    return hashlib.sha256(pub_bytes).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public_bytes(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _decode(value: str, size: int) -> bytes:
    decoded = base64.b64decode(value, validate=True)
    if len(decoded) != size:
        raise ValueError("invalid encoded length")
    return decoded


def _derive(passphrase: str, salt: bytes, n: int) -> bytes:
    if type(n) is not int or not 2**14 <= n <= 2**17 or n & (n - 1):
        raise SigningError("unsupported scrypt cost")
    return hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=n,
        r=8,
        p=1,
        maxmem=256 * 1024 * 1024,
        dklen=32,
    )


def generate_keypair(
    passphrase: str, secret_dir: Path, pub_path: Path, kdf_n: int = 2**17
) -> str:
    if len(passphrase) < 16:
        raise SigningError("passphrase must have at least 16 characters")
    key_path = secret_dir / "owner.key.enc"
    if (
        key_path.exists()
        or key_path.is_symlink()
        or pub_path.exists()
        or pub_path.is_symlink()
    ):
        raise SigningError("refusing to overwrite key files")
    key = Ed25519PrivateKey.generate()
    public = _public_bytes(key.public_key())
    raw = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    encrypted = AESGCM(_derive(passphrase, salt, kdf_n)).encrypt(nonce, raw, None)
    document = {
        "version": 1,
        "kdf": "scrypt",
        "n": kdf_n,
        "r": 8,
        "p": 1,
        "salt": _b64(salt),
        "aead": "AES-256-GCM",
        "nonce": _b64(nonce),
        "ciphertext": _b64(encrypted),
        "fingerprint": fingerprint(public),
    }
    created: list[Path] = []
    try:
        # Exclusive reservations prevent concurrent init from replacing an existing key.
        for path in (key_path, pub_path):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8"):
                pass
            created.append(path)
        atomic_write_text(key_path, json.dumps(document) + "\n", 10, 0.05)
        atomic_write_text(pub_path, _b64(public) + "\n", 10, 0.05)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        raise SigningError("could not create key files") from None
    return document["fingerprint"]


def load_private_key(secret_dir: Path, passphrase: str) -> Ed25519PrivateKey:
    try:
        data = json.loads(read_text_retry(secret_dir / "owner.key.enc"))
        if (
            type(data["version"]) is not int
            or data["version"] != 1
            or data["kdf"] != "scrypt"
            or data["aead"] != "AES-256-GCM"
            or type(data["r"]) is not int
            or data["r"] != 8
            or type(data["p"]) is not int
            or data["p"] != 1
        ):
            raise ValueError("invalid key format")
        derived = _derive(passphrase, _decode(data["salt"], 16), data["n"])
        raw = AESGCM(derived).decrypt(
            _decode(data["nonce"], 12), _decode(data["ciphertext"], 48), None
        )
        key = Ed25519PrivateKey.from_private_bytes(raw)
        if fingerprint(_public_bytes(key.public_key())) != data["fingerprint"]:
            raise ValueError("fingerprint mismatch")
        return key
    except Exception:
        raise SigningError("could not unlock owner key") from None


def load_public_key(pub_path: Path) -> Ed25519PublicKey:
    try:
        return Ed25519PublicKey.from_public_bytes(
            _decode(read_text_retry(pub_path).strip(), 32)
        )
    except (OSError, ValueError, TypeError):
        raise SigningError("could not load owner public key") from None


def _validate_fields(fields: dict) -> None:
    if set(fields) != FIELDS or any(
        not isinstance(value, str) for value in fields.values()
    ):
        raise ValueError("record must contain every defined field as text")
    if fields["kind"] not in KINDS or not re.fullmatch(
        r"[0-9a-f]{32}", fields["nonce"]
    ):
        raise ValueError("invalid kind or nonce")
    for name in ("plan_hash", "policy_hash", "key_fingerprint"):
        if not re.fullmatch(r"[0-9a-f]{64}", fields[name]) and (
            name == "key_fingerprint" or fields[name]
        ):
            raise ValueError("invalid hash or fingerprint")
    if datetime.fromisoformat(fields["issued_at"]).utcoffset() is None:
        raise ValueError("issued_at requires an offset")
    if fields["kind"] in {"sign-policy", "sign-manifest"}:
        if any(
            fields[name]
            for name in ("project", "task", "plan_hash", "question_id", "answer")
        ):
            raise ValueError("unused fields must be empty")
        if not fields["policy_hash"]:
            raise ValueError("missing signed content hash")
    else:
        if not fields["project"] or not fields["task"] or not fields["plan_hash"]:
            raise ValueError("missing task binding")
        if fields["kind"] == "answer":
            if not fields["question_id"]:
                raise ValueError("missing question binding")
        elif fields["question_id"] or fields["answer"]:
            raise ValueError("unused fields must be empty")


def sign_record(private_key: Ed25519PrivateKey, fields: dict) -> dict:
    try:
        _validate_fields(fields)
        if fields["key_fingerprint"] != fingerprint(
            _public_bytes(private_key.public_key())
        ):
            raise ValueError("key fingerprint mismatch")
        return {**fields, "signature": _b64(private_key.sign(canonical(fields)))}
    except (ValueError, TypeError):
        raise SigningError("invalid signing record") from None


def verify_record(public_key: Ed25519PublicKey, record: dict, expected: dict) -> None:
    try:
        fields = {name: value for name, value in record.items() if name != "signature"}
        _validate_fields(fields)
        if fields["key_fingerprint"] != fingerprint(_public_bytes(public_key)):
            raise ValueError("fingerprint mismatch")
        public_key.verify(_decode(record["signature"], 64), canonical(fields))
        if any(
            name not in fields or fields[name] != value
            for name, value in expected.items()
        ):
            raise ValueError("expected binding mismatch")
    except (InvalidSignature, ValueError, TypeError, KeyError, AttributeError):
        raise VerificationError("record verification failed") from None
