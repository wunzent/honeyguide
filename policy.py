from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fnmatch
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import tomllib
from typing import Callable, Iterable, Literal

from approvals import check_approval, approval_nonces
from hashing import sha256_file
from state_writer import plan_hash, read_text_retry



class PolicyError(Exception):
    pass


ROLES = frozenset({"planner", "coder", "tester", "reviewer", "doc-keeper"})
RELAY_TYPES = frozenset({"clarify", "naming", "choose-approach"})
ROLE_STATUSES = {
    "planner": {"approved"},
    "coder": {"approved", "running"},
    "tester": {"running", "testing"},
    "reviewer": {"reviewing"},
    "doc-keeper": {"reviewing"},
}


@dataclass(frozen=True)
class Policy:
    hub_root: Path
    max_processes: int
    max_dynamic: int
    security_gate: str
    mode: str
    data_root: str
    owner_secret_dir: str
    deny: list[str]
    max_path_len: int
    coder_tester_rounds: int
    review_fix_cycles: int
    respawn_per_key: int
    team_minutes: int
    backoff_minutes: list[int]
    max_attempts_per_episode: int
    max_episodes_per_task_per_day: int
    verified_reset_grace_minutes: int
    relay_types: list[str]
    routing_roles: dict
    policy_hash: str
    raw: dict
    ignored_artifact_globs: list[str]


def _parse_policy(root: Path, raw: dict, digest: str) -> Policy:
    try:
        hub, paths, caps = (raw[name] for name in ("hub", "paths", "caps"))
        quota, questions = raw["quota"], raw["questions"]
        roles = raw["routing"]["roles"]
        positive = ((hub, "max_processes"), (paths, "max_path_len"),
                    (caps, "coder_tester_rounds"), (caps, "team_minutes"),
                    (quota, "max_attempts_per_episode"), (quota, "max_episodes_per_task_per_day"))
        nonnegative = ((hub, "max_dynamic"), (caps, "review_fix_cycles"),
                       (caps, "respawn_per_key"), (quota, "verified_reset_grace_minutes"))
        for entries, minimum in ((positive, 1), (nonnegative, 0)):
            for table, name in entries:
                if type(table[name]) is not int or table[name] < minimum:
                    raise ValueError(f"invalid {name}")
        if hub["max_dynamic"] > hub["max_processes"]:
            raise ValueError("dynamic cap exceeds process cap")
        if hub["mode"] != "manual-trusted-approval" or hub["security_gate"] != "NOT PASS":
            raise ValueError("unsupported operating mode or security gate")
        for name in ("data_root", "owner_secret_dir"):
            if not isinstance(paths[name], str) or not paths[name].strip():
                raise ValueError(f"invalid {name}")
        artifacts = raw.get("scope", {}).get("ignored_artifact_globs", [])
        for values in (paths["deny"], questions["relay_types"], artifacts):
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                raise ValueError("invalid path or question list")
        if not set(questions["relay_types"]) <= RELAY_TYPES:
            raise ValueError("authority questions cannot be relayed")
        backoff = quota["backoff_minutes"]
        if (not isinstance(backoff, list) or not backoff
                or any(type(n) is not int or n < 1 for n in backoff)
                or backoff != sorted(backoff)
                or quota["max_attempts_per_episode"] > len(backoff)):
            raise ValueError("invalid bounded quota backoff")
        if set(roles) != ROLES:
            raise ValueError("routing requires all five roles")
        for role, settings in roles.items():
            vendors, fallback = settings["allowed_vendors"], settings["fallback"]
            if (not isinstance(vendors, list) or not vendors
                    or any(v not in {"claude", "codex"} for v in vendors)
                    or not isinstance(fallback, list)
                    or any(not isinstance(v, str) or ":" not in v
                           or v.split(":", 1)[0] not in vendors or not v.split(":", 1)[1]
                           for v in fallback)
                    or type(settings.get("auto_fallback", False)) is not bool):
                raise ValueError(f"invalid routing for {role}")
        if roles["reviewer"].get("reviewer_must_differ") is not True:
            raise ValueError("reviewer must differ from coder")
        return Policy(root, hub["max_processes"], hub["max_dynamic"], hub["security_gate"], hub["mode"],
                      paths["data_root"], paths["owner_secret_dir"], paths["deny"], paths["max_path_len"],
                      caps["coder_tester_rounds"], caps["review_fix_cycles"], caps["respawn_per_key"],
                      caps["team_minutes"], backoff, quota["max_attempts_per_episode"],
                      quota["max_episodes_per_task_per_day"], quota["verified_reset_grace_minutes"],
                      questions["relay_types"],
                      {role: {**settings, "auto_fallback": settings.get("auto_fallback", False)}
                       for role, settings in roles.items()}, digest, raw, artifacts)
    except (KeyError, TypeError, ValueError) as exc:
        raise PolicyError(f"invalid policy: {exc}") from None


def load_policy(hub_root: Path) -> Policy:
    try:
        root = Path(hub_root).resolve()
        path = root / "config" / "policy.toml"
        digest = sha256_file(path)
        raw = tomllib.loads(read_text_retry(path))
        if sha256_file(path) != digest:
            raise PolicyError("policy changed while reading")
        return _parse_policy(root, raw, digest)
    except (OSError, ValueError) as exc:
        raise PolicyError(f"could not read policy: {exc}") from None


load_policy_unverified = load_policy


def _expanded_text(path_str: str) -> str:
    text = re.sub(r"%([^%]+)%", lambda match: os.environ.get(match[1], match[0]), path_str)
    text = os.path.expanduser(os.path.expandvars(text))
    if not text or re.search(r"%[^%]+%|\$\{?\w+", text) or text.startswith("~"):
        raise PolicyError("empty path or unresolved environment variable")
    return text


def expand(path_str: str) -> Path:
    try:
        return Path(_expanded_text(path_str)).resolve(strict=False)
    except (OSError, ValueError, RuntimeError) as exc:
        raise PolicyError(f"could not resolve path: {exc}") from None


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child_name = os.path.normcase(str(Path(child).resolve(strict=False)))
        parent_name = os.path.normcase(str(Path(parent).resolve(strict=False)))
        return os.path.commonpath((child_name, parent_name)) == parent_name
    except ValueError:  # Different Windows drives cannot contain each other.
        return False
    except (OSError, RuntimeError) as exc:
        raise PolicyError(f"could not compare paths: {exc}") from None


def inside_git_repo(path: Path, git: Callable = subprocess.run) -> bool:
    try:
        current = Path(path).resolve(strict=False)
        for ancestor in (current, *current.parents):
            if not ancestor.is_dir():
                continue
            if (ancestor / ".git").exists():
                return True
            result = git(["git", "-C", str(ancestor), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=False, timeout=10)
            if result.returncode == 0:
                return True
        return False
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise PolicyError(f"could not check git ancestry: {exc}") from None


def _deny_paths(policy: Policy, hub_root: Path) -> list[Path]:
    root = Path(hub_root).resolve()
    return [root, root.parent / "multi-agent-hub", root.parent / "worktrees",
            *(expand(path) for path in policy.deny)]


def check_data_root(policy: Policy, hub_root: Path, registered_repos: Iterable[Path] = (),
                    *, git: Callable = subprocess.run) -> Path:
    root = expand(policy.data_root)
    for denied in (*_deny_paths(policy, hub_root), *registered_repos):
        if is_inside(root, denied):
            raise PolicyError(f"data root is inside a forbidden path: {denied}")
    if inside_git_repo(root, git=git):
        raise PolicyError("data root is inside a git repo")
    return root


def worktree_path(policy: Policy, project: str, task: str) -> Path:
    if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,32}", value)
           for value in (project, task)):
        raise PolicyError("invalid project or task ID")
    # Keep the unresolved join so existing junctions, symlinks and '..' cannot disappear.
    root = Path(_expanded_text(policy.data_root))
    if ".." in root.parts:
        raise PolicyError("data root contains traversal")
    joined = root.absolute() / "worktrees" / project / task
    try:
        resolved = joined.resolve(strict=False)
        if (".." in joined.parts or os.path.normcase(str(resolved)) != os.path.normcase(str(joined))):
            raise PolicyError("worktree path contains traversal or an alias")
    except (OSError, RuntimeError) as exc:
        raise PolicyError(f"could not resolve worktree path: {exc}") from None
    if len(str(resolved)) > policy.max_path_len:
        raise PolicyError("worktree path exceeds max_path_len")
    return resolved


def check_target_repo(policy: Policy, repo_path: Path, hub_root: Path,
                      *, git: Callable = subprocess.run) -> Path:
    repo = expand(str(repo_path))
    for denied in (*_deny_paths(policy, hub_root), expand(policy.data_root)):
        if is_inside(repo, denied):
            raise PolicyError(f"target repo is inside a forbidden path: {denied}")
    if not repo.is_dir() or not inside_git_repo(repo, git=git):
        raise PolicyError("target must be an existing git repo")
    return repo


def check_scope(changed_paths: list[str], allowed_globs: list[str]) -> list[str]:
    violations = []
    for path in changed_paths:
        normalized = path.replace("\\", "/")
        relative, windows = PurePosixPath(normalized), PureWindowsPath(path)
        if (not normalized or relative.is_absolute() or windows.drive or windows.root
                or ".." in relative.parts
                or not any(fnmatch.fnmatchcase(normalized, pattern.replace("\\", "/"))
                           for pattern in allowed_globs)):
            violations.append(path)
    return violations


def question_class(policy: Policy, qtype: str) -> Literal["clarify", "owner-decision"]:
    return "clarify" if qtype in RELAY_TYPES and qtype in policy.relay_types else "owner-decision"


@dataclass(frozen=True)
class Decision:
    ok: bool
    reason: str


def _counter(state: dict, name: str) -> int | float:
    value = state.get(name, 0)
    if type(value) not in (int, float) or not 0 <= value < float("inf"):
        raise ValueError(f"invalid {name}")
    return value


def team_active_seconds(state: dict, now: datetime) -> float:
    elapsed = float(_counter(state, "team_active_seconds"))
    for run in state.get("runs", {}).values():
        if run.get("status") == "running":
            started = (datetime.fromisoformat(run["started_at"]) if run.get("started_at")
                       else datetime.fromtimestamp(run["create_time"], timezone.utc))
            elapsed += max(0.0, (now - started).total_seconds())
    return elapsed


def may_spawn(*, policy: Policy, spec_text: str, state: dict,
              live_runs: list[dict], role: str, idem_key: str, dynamic: bool = False,
              now: datetime | None = None) -> Decision:
    if role not in ROLE_STATUSES or state.get("status") not in ROLE_STATUSES[role]:
        return Decision(False, "status does not permit this role")
    try:
        approval = state.get("approval")
        if approval is None:
            return Decision(False, "approval missing")
        check_approval(approval, project=state["project"], task=state["task"],
                       plan_hash=plan_hash(spec_text), policy_hash=policy.policy_hash,
                       used_nonces=approval_nonces(state))
        if load_policy(policy.hub_root) != policy:
            raise PolicyError("policy changed since loading")
    except Exception:
        return Decision(False, "plan or policy changed: owner approval needed")
    try:
        if any(q.get("blocking") and q.get("status") != "answered" for q in state.get("questions", [])):
            return Decision(False, "blocking question unanswered")
        if len(live_runs) >= policy.max_processes:
            return Decision(False, "process slots full")
        if dynamic and sum(bool(run.get("dynamic")) for run in live_runs) >= policy.max_dynamic:
            return Decision(False, "dynamic slots full")
        spawned = state.get("spawned_keys", {})
        # A list records one entry per start; a mapping stores total starts per key.
        count = spawned.count(idem_key) if isinstance(spawned, list) else spawned.get(idem_key, 0)
        if type(count) is not int or count < 0 or not isinstance(idem_key, str) or not idem_key:
            raise ValueError("invalid spawn key or count")
        if count > policy.respawn_per_key or any(run.get("idem_key") == idem_key for run in live_runs):
            return Decision(False, "duplicate key or respawn cap reached")
        if role in {"coder", "tester"} and _counter(state, "round") > policy.coder_tester_rounds:
            return Decision(False, "coder/tester round cap reached")
        if _counter(state, "review_fix_cycles") > policy.review_fix_cycles:
            return Decision(False, "review-fix cap reached")
        if team_active_seconds(state, now or datetime.now(timezone.utc)) >= policy.team_minutes * 60:
            return Decision(False, "team time cap reached")
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError) as exc:
        return Decision(False, f"invalid spawn state: {exc}")
    return Decision(True, "approval and spawn checks passed")
