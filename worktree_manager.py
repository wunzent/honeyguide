from __future__ import annotations

import ast
import os
import re
import subprocess
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Callable, Iterable

from policy import (
    Policy,
    PolicyError,
    check_data_root,
    check_scope,
    check_target_repo,
    worktree_path,
)


class GitForbidden(ValueError):
    pass


def _validate_git(args: list[str], cwd: Path) -> None:
    if any(arg.startswith(("--git-dir", "--work-tree")) for arg in args):
        raise GitForbidden("alternate git directory or worktree is forbidden")
    command = tuple(args[:2]) if args[:1] == ["worktree"] else tuple(args[:1])
    flags = {
        ("init",): set(),
        ("status",): {
            "--porcelain",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignored",
            "--ignored=matching",
        },
        ("diff",): {
            "--stat",
            "--name-only",
            "--name-status",
            "-z",
            "--cached",
            "--no-ext-diff",
            "--no-textconv",
        },
        ("add",): {"-A"},
        ("commit",): {"--no-gpg-sign", "-m"},
        ("rev-parse",): {"--abbrev-ref", "--show-toplevel", "--verify"},
        ("worktree", "add"): {"-b"},
        ("worktree", "list"): {"--porcelain"},
        ("log",): {"-1", "--format=%H", "--format=%s", "--oneline"},
        ("apply",): {"--check"},
    }
    if command not in flags or command == ("log",) and args[1:2] != ["-1"]:
        raise GitForbidden(f"forbidden git command: {args[:2]}")
    positional = []
    index = len(command)
    paths_only = False
    while index < len(args):
        arg = args[index]
        if not paths_only and arg == "--":
            paths_only = True
        elif arg.startswith("-") and not paths_only:
            if arg not in flags[command]:
                raise GitForbidden(f"forbidden git flag: {arg}")
            if arg in {"-m", "-b"}:
                index += 1
                if index >= len(args):
                    raise GitForbidden("missing git flag value")
        else:
            positional.append(arg)
        index += 1
    if command == ("commit",) and (positional or args.count("-m") != 1):
        raise GitForbidden("commit requires -m only")
    if command == ("init",) and positional:
        raise GitForbidden("init must use cwd")
    if command == ("add",):
        if not positional and "-A" not in args:
            raise GitForbidden("add requires -A or explicit relative paths")
        root = Path(cwd).resolve()
        for arg in positional:
            path = Path(arg)
            if (
                not arg
                or ":" in arg
                or path.is_absolute()
                or PureWindowsPath(arg).anchor
                or ".." in arg.replace("\\", "/").split("/")
                or ".git" in arg.replace("\\", "/").lower().split("/")
                or arg.startswith("-")
                or not (root / path).resolve().is_relative_to(root)
            ):
                raise GitForbidden("add path must stay inside worktree")


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Validate each subcommand before adding the manager's trusted config."""
    _validate_git(args, cwd)
    # Disable executable hooks for all trusted local operations, without changing config.
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={Path(cwd).resolve().as_posix()}",
            "-c",
            "core.hooksPath=NUL" if os.name == "nt" else "core.hooksPath=/dev/null",
            *args,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


class WorktreeManager:
    def __init__(
        self, git: Callable[[list[str], Path], tuple[int, str, str]] = run_git
    ) -> None:
        self.git = git

    def _git(self, args: list[str], cwd: Path) -> str:
        try:
            code, out, err = self.git(args, cwd)
        except PermissionError as exc:
            raise PolicyError(f"git {args[0]} permission denied") from exc
        if code:
            raise PolicyError(f"git {args[0]} failed: {err.strip()}")
        return out

    def create(
        self, policy: Policy, project: str, task: str, target_repo: Path, base_ref: str
    ) -> Path:
        target = check_target_repo(policy, target_repo, policy.hub_root)
        check_data_root(policy, policy.hub_root, [target])
        path = worktree_path(policy, project, task)
        if not base_ref or base_ref.startswith("-"):
            raise PolicyError("invalid base ref")
        branch = f"refs/heads/hub/{task}"
        if path.exists():
            records = self._git(["worktree", "list", "--porcelain"], target).split(
                "\n\n"
            )
            for record in records:
                fields = record.splitlines()
                if (
                    f"worktree {path.as_posix()}" in fields
                    or f"worktree {path}" in fields
                ):
                    if f"branch {branch}" in fields and (path / ".git").is_file():
                        return path
            raise PolicyError("worktree path collides with a different repo or branch")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._git(["worktree", "add", "-b", f"hub/{task}", str(path), base_ref], target)
        return path

    def changed_files(self, worktree: Path, ignored_artifact_globs: Iterable[str] = ()) -> list[str]:
        output = self._git(
            ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored"],
            worktree,
        )
        records = iter(output.split("\0"))
        paths: list[str] = []
        patterns = [variant for pattern in ignored_artifact_globs
                    for variant in (pattern, pattern.removeprefix("**/"))]
        for record in records:
            if not record:
                continue
            if record[:2] == "!!" and not check_scope([record[3:]], patterns):
                continue
            paths.append(record[3:])
            if "R" in record[:2] or "C" in record[:2]:
                paths.append(next(records))
        return sorted(set(paths))

    def apply_patch(
        self, worktree: Path, diff_text: str, allowed_globs: list[str]
    ) -> list[str]:
        paths = _patch_paths(diff_text)
        violations = check_scope(paths, allowed_globs)
        if violations:
            raise PolicyError(f"patch outside scope: {violations}")
        patch_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=worktree,
                suffix=".patch",
                delete=False,
            ) as stream:
                patch_path = Path(stream.name)
                stream.write(diff_text)
            self._git(["apply", "--check", "--", str(patch_path)], worktree)
            self._git(["apply", "--", str(patch_path)], worktree)
        finally:
            if patch_path is not None:
                patch_path.unlink(missing_ok=True)
        return paths

    def commit(self, worktree: Path, message: str, signed_commit_record: dict) -> None:
        """Caller must verify the owner signature and current task bindings first."""
        if (
            not isinstance(signed_commit_record, dict)
            or signed_commit_record.get("kind") != "commit"
            or not signed_commit_record.get("signature")
        ):
            raise PolicyError("verified signed commit record required")
        self._git(["add", "-A"], worktree)
        self._git(["commit", "--no-gpg-sign", "-m", message], worktree)


def _patch_paths(text: str) -> list[str]:
    paths: set[str] = set()
    old = new = 0
    for line in text.splitlines():
        if old or new:
            if line.startswith("\\ No newline"):
                continue
            marker = line[:1]
            if marker not in {" ", "+", "-"}:
                raise PolicyError("malformed patch hunk")
            old -= marker in {" ", "-"}
            new -= marker in {" ", "+"}
            if old < 0 or new < 0:
                raise PolicyError("malformed patch hunk length")
            continue
        if line.startswith("diff --git "):
            pair = line[len("diff --git ") :]
            if pair.startswith('"'):
                match = re.fullmatch(r'("(?:[^"\\]|\\.)*") ("(?:[^"\\]|\\.)*")', pair)
                if match is None:
                    raise PolicyError("unsupported patch path quoting")
                names = [_unquote_path(value) for value in match.groups()]
            else:
                parts = pair.split(" b/")
                if len(parts) != 2:
                    raise PolicyError("ambiguous patch paths")
                names = [parts[0], "b/" + parts[1]]
            for prefix, name in zip(("a/", "b/"), names):
                if not name.startswith(prefix):
                    raise PolicyError("invalid patch prefix")
                paths.add(name[2:])
        elif line.startswith("@@"):
            match = re.fullmatch(r"@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@.*", line)
            if match is None:
                raise PolicyError("unsupported patch hunk header")
            old, new = (
                int(count) if count is not None else 1 for count in match.groups()
            )
        elif line.startswith(("--- ", "+++ ")):
            name = line[4:].split("\t", 1)[0]
            if name == "/dev/null":
                continue
            if name.startswith('"'):
                name = _unquote_path(name)
            if not name.startswith(("a/", "b/")):
                raise PolicyError("invalid patch prefix")
            paths.add(name[2:])
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            name = line.split(" ", 2)[2]
            paths.add(_unquote_path(name) if name.startswith('"') else name)
    if old or new:
        raise PolicyError("truncated patch hunk")
    if not paths or any(
        "\x00" in path or ".git" in path.replace("\\", "/").lower().split("/")
        for path in paths
    ):
        raise PolicyError("empty patch or forbidden git metadata path")
    return sorted(paths)


def _unquote_path(value: str) -> str:
    try:
        # Git quotes UTF-8 bytes using C-style octal escapes.
        return ast.literal_eval("b" + value).decode("utf-8")
    except (ValueError, SyntaxError, UnicodeError):
        raise PolicyError("unsupported patch path quoting") from None
