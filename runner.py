"""Python-run tests execute coder-authored code with the owner's Windows privileges.

Accepted residual risk in Phase 1 (ARCHITECTURE §6.4 T6); Security Gate NOT PASS.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

import psutil
import yaml

from adapters.base import Adapter, Outcome, Route, scrub
from agent_loader import AgentTemplate, render_prompt
from policy import (
    PolicyError,
    check_scope,
    load_policy,
    may_spawn,
    team_active_seconds,
    worktree_path,
)
from approvals import check_approval, approval_nonces
from hashing import sha256_file
from state_writer import StateStore, atomic_write_text, plan_hash, approved_scope, read_text_retry
from worktree_manager import WorktreeManager

_ENV_KEYS = frozenset(
    key.upper()
    for key in (
        "SystemRoot",
        "SystemDrive",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "PATH",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "HOMEDRIVE",
        "HOMEPATH",
        "USERNAME",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
    )
)


def _child_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    return {
        **{key: value for key, value in os.environ.items() if key.upper() in _ENV_KEYS},
        **(overrides or {}),
        "HUB_WORKER": "1",
    }


def is_same_process(pid: int, create_time: float) -> bool:
    if type(pid) is not int or pid <= 0 or type(create_time) not in (int, float):
        return False
    try:
        process = psutil.Process(pid)
        return (
            abs(process.create_time() - create_time) <= 1
            and process.is_running()
            and process.status() != psutil.STATUS_ZOMBIE
        )
    except (psutil.Error, OSError):
        return False


class Runner:
    def __init__(
        self,
        store: StateStore,
        adapters: dict[str, Adapter],
        worktrees: WorktreeManager,
        hub_root: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.store = store
        self.adapters = adapters
        self.worktrees = worktrees
        self.hub_root = Path(hub_root).resolve()
        if store.root.resolve() != self.hub_root:
            raise ValueError("store must belong to the configured hub")
        self.clock = clock
        self._processes: dict[tuple[str, str, str], subprocess.Popen] = {}

    def _new_run(self, project: str, task: str) -> tuple[str, Path]:
        parent = self.store.task_dir(project, task) / "runs"
        parent.mkdir(parents=True, exist_ok=True)
        while True:
            run_id = (
                "R-"
                + self.clock().astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
                + "-"
                + secrets.token_hex(2)
            )
            directory = parent / run_id
            try:
                directory.mkdir()
                return run_id, directory
            except FileExistsError:
                continue

    def _directory(self, project: str, task: str, run_id: str) -> Path:
        if re.fullmatch(r"R-\d{14}-[0-9a-f]{4}", run_id) is None:
            raise ValueError("invalid run ID")
        return self.store.task_dir(project, task) / "runs" / run_id

    def _write(self, path: Path, text: str) -> None:
        atomic_write_text(
            path, text, self.store.replace_retries, self.store.replace_backoff
        )

    def _event(
        self, project: str, task: str, kind: str, data: dict, run_id: str, changes: dict
    ) -> None:
        with self.store.transaction(project, task) as txn:
            runs = dict(txn.state.get("runs", {}))
            runs[run_id] = {**runs.get(run_id, {}), **changes}
            updates = {"runs": runs}
            if kind == "run.finished" and txn.state.get("runs", {}).get(run_id, {}).get("status") == "running":
                updates["team_active_seconds"] = team_active_seconds(
                    {"team_active_seconds": txn.state.get("team_active_seconds", 0),
                     "runs": {run_id: txn.state["runs"][run_id]}},
                    datetime.fromisoformat(changes["finished_at"]))
            elif kind == "tests.finished":
                updates["team_active_seconds"] = txn.state.get("team_active_seconds", 0) + changes["duration"]
            txn.state.update(updates)
            txn.emit(kind, {"run": run_id, **data, "set": updates})

    def start(
        self,
        project: str,
        task: str,
        role: str,
        route: Route,
        template: AgentTemplate,
        worktree: Path,
        idem_key: str,
        prompt_context: dict[str, str],
        dynamic: bool = False,
    ) -> str:
        if template.role != role:
            raise ValueError("template role mismatch")
        policy = load_policy(self.hub_root)
        expected_worktree = worktree_path(policy, project, task)
        if (
            Path(worktree).absolute() != expected_worktree
            or not (expected_worktree / ".git").is_file()
        ):
            raise PolicyError("spawn requires the task's policy worktree")
        adapter = self.adapters[route.vendor]
        snapshot = self.store.read_state(project, task)
        for prior_id, prior in snapshot.get("runs", {}).items():
            if prior.get("idem_key") == idem_key and prior.get("status") == "abandoned":
                decision = may_spawn(
                    policy=policy,
                    spec_text=self.store.read_spec(project, task),
                    state=snapshot,
                    live_runs=self.live_runs(),
                    role=role,
                    idem_key=idem_key,
                    dynamic=dynamic,
                    now=self.clock(),
                )
                if not decision.ok:
                    raise PolicyError(decision.reason)
                if self.adopt_intent(project, task, prior_id):
                    return prior_id
        with self.store.transaction(project, task) as txn:
            runs = dict(txn.state.get("runs", {}))
            # Only reconciliation may abandon an intent before a bounded retry.
            if any(
                run.get("idem_key") == idem_key
                and run.get("status") in {"intent", "running"}
                for run in runs.values()
            ):
                raise PolicyError("duplicate pending spawn key")
            # Count durable reservations under the same writer lock as the new intent.
            live = self.live_runs()
            live += [
                run
                for _, _, state in self._tasks()
                for run in state.get("runs", {}).values()
                if run.get("status") == "intent"
            ]
            decision = may_spawn(
                policy=policy,
                spec_text=self.store.read_spec(project, task),
                state=txn.state,
                live_runs=live,
                role=role,
                idem_key=idem_key,
                dynamic=dynamic,
                now=self.clock(),
            )
            if not decision.ok:
                raise PolicyError(decision.reason)
            run_id, directory = self._new_run(project, task)
            prompt = directory / "prompt.md"
            self._write(prompt, render_prompt(template, prompt_context))
            invocation = adapter.build(
                template, route, directory, expected_worktree, prompt
            )
            run_token = secrets.token_hex(16)
            invocation = replace(invocation, env={**invocation.env, "HUB_WORKER": "1", "HUB_RUN_TOKEN": run_token})
            record = {
                "run": run_id,
                "role": role,
                "route": asdict(route),
                "idem_key": idem_key,
                "status": "intent",
                "dynamic": dynamic,
                "worktree": str(expected_worktree),
                "intent_at": self.clock().isoformat(),
                "run_token": run_token,
            }
            runs[run_id] = record
            keys = dict(txn.state.get("spawned_keys", {}))
            keys[idem_key] = keys.get(idem_key, 0) + 1
            updates = {
                "runs": runs,
                "team_active_seconds": txn.state.get("team_active_seconds", 0),
                "spawned_keys": keys,
                "active_run": run_id,
                "first_dispatch_at": txn.state.get("first_dispatch_at")
                or self.clock().isoformat(),
            }
            txn.state.update(updates)
            txn.emit("spawn.intent", {"key": idem_key, **record, "set": updates})
        with (
            (directory / "output.jsonl").open("wb") as output,
            (directory / "stderr.txt").open("wb") as errors,
        ):
            process = subprocess.Popen(
                invocation.argv,
                cwd=invocation.cwd,
                stdin=subprocess.PIPE,
                stdout=output,
                stderr=errors,
                env=_child_env(invocation.env),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0,
            )
            child = psutil.Process(process.pid)
            created = child.create_time()
            identity = {"pid": process.pid, "create_time": created,
                        "run_token": run_token, "exe": child.exe()}
            self._write(directory / "pid.json", json.dumps(identity))
            self._write(directory / "pid", str(process.pid))
        self._processes[project, task, run_id] = process
        started = {**identity, "started_at": self.clock().isoformat()}
        self._event(
            project,
            task,
            "spawn.started",
            started,
            run_id,
            {**started, "status": "running"},
        )
        try:
            if invocation.stdin_text is not None:
                process.stdin.write(invocation.stdin_text.encode("utf-8"))
        except BrokenPipeError:
            pass
        finally:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        return run_id

    def adopt_intent(self, project: str, task: str, run_id: str) -> bool:
        """Recover an unjournalled launch; uncertainty must never permit a second writer."""
        run = self.store.read_state(project, task)["runs"][run_id]
        if run.get("status") not in {"intent", "abandoned"}:
            raise PolicyError("only pending or abandoned intents can be adopted")
        directory = self._directory(project, task, run_id).resolve()
        worktree = Path(run["worktree"]).resolve()
        matches = []
        uncertain = False
        identity_path = directory / "pid.json"
        try:
            recorded = json.loads(read_text_retry(identity_path)) if identity_path.exists() else None
            if recorded is not None and (
                type(recorded.get("pid")) is not int
                or type(recorded.get("create_time")) not in (int, float)
                or recorded.get("run_token") != run.get("run_token")
                or not isinstance(recorded.get("exe"), str)
            ):
                raise ValueError("invalid recorded process identity")
            adapter = self.adapters[run["route"]["vendor"]]
            expected = adapter.executable
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise PolicyError("cannot read orphan process identity") from exc

        def normalized(value: str) -> str:
            return os.path.normcase(os.path.normpath(value.strip('"')))

        try:
            for process in psutil.process_iter():
                if process.pid in {0, 4, os.getpid()}:
                    continue
                try:
                    command = process.cmdline()
                    cwd = process.cwd()
                    related = (bool(cwd) and Path(cwd).resolve() == worktree
                               or any(str(directory).casefold() in arg.casefold() for arg in command)
                               or recorded is not None and process.pid == recorded["pid"])
                    vendor_match = any(
                        [normalized(arg) for arg in command[index:index + len(expected)]]
                        == [normalized(arg) for arg in expected]
                        for index in range(len(command))
                    ) if expected else False
                    if not related and not vendor_match:
                        continue
                    if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                        continue
                    created, exe = process.create_time(), process.exe()
                    token = process.environ().get("HUB_RUN_TOKEN")
                    valid = (bool(run.get("run_token")) and token == run["run_token"] and vendor_match)
                    if recorded is not None:
                        valid = (valid and process.pid == recorded["pid"]
                                 and abs(created - recorded["create_time"]) <= 1
                                 and normalized(exe) == normalized(recorded["exe"]))
                    if valid:
                        matches.append({"pid": process.pid, "create_time": created,
                                        "run_token": token, "exe": exe,
                                        "started_at": datetime.fromtimestamp(created, timezone.utc).isoformat()})
                    elif related:
                        uncertain = True
                except psutil.NoSuchProcess:
                    continue
                except (psutil.Error, OSError):
                    uncertain = True
        except (psutil.Error, OSError) as exc:
            raise PolicyError("cannot inspect possible orphan processes") from exc
        if len(matches) == 1 and not uncertain:
            identity = matches[0]
            self._write(directory / "pid.json", json.dumps(identity))
            self._write(directory / "pid", str(identity["pid"]))
            self._event(
                project,
                task,
                "spawn.adopted",
                identity,
                run_id,
                {**identity, "status": "running"},
            )
            return True
        if uncertain or matches:
            raise PolicyError("orphan process inspection is incomplete or ambiguous")
        return False

    def poll(self, project: str, task: str, run_id: str) -> Outcome | None:
        directory = self._directory(project, task, run_id)
        record = self.store.read_state(project, task)["runs"][run_id]
        process = self._processes.get((project, task, run_id))
        if record["status"] == "intent":
            return None
        if process is not None:
            exit_code = process.poll()
            if exit_code is None:
                return None
        elif record.get("status") == "running" and is_same_process(
            record["pid"], record["create_time"]
        ):
            return None
        else:
            # Restart cannot infer a successful exit from agent text alone.
            exit_code = record.get("exit_code", 1)
        adapter = self.adapters[record["route"]["vendor"]]
        events = []
        for line in read_text_retry(directory / "output.jsonl").splitlines():
            event = adapter.parse_line(line)
            if event is not None:
                events.append(event)
        errors = read_text_retry(directory / "stderr.txt")
        outcome = adapter.classify(exit_code, events, scrub(errors[-8192:]))
        outcome = replace(
            outcome,
            result_text=scrub(outcome.result_text),
            usage=json.loads(scrub(json.dumps(outcome.usage))),
        )
        self._write(directory / "result.md", outcome.result_text)
        finished = {
            "finished_at": self.clock().isoformat(),
            "status": outcome.status,
            "reset_at": outcome.reset_at.isoformat() if outcome.reset_at else None,
            "reset_source": outcome.reset_source,
            "session_id": outcome.session_id,
            "exit_code": exit_code,
        }
        self._write(
            directory / "meta.md",
            "# Run metadata\n\n```json\n"
            + scrub(json.dumps(finished, indent=2))
            + "\n```\n",
        )
        if record["status"] == "running":
            self._event(project, task, "run.finished", finished, run_id, finished)
        self._processes.pop((project, task, run_id), None)
        return outcome

    def run_tests(
        self,
        project: str,
        task: str,
        worktree: Path,
        test_command: list[str],
        timeout_s: float,
    ) -> dict:
        if (
            not test_command
            or Path(test_command[0]).resolve() != Path(sys.executable).resolve()
            or timeout_s <= 0
        ):
            raise ValueError(
                "tests require the trusted Python executable and a positive timeout"
            )
        policy = load_policy(self.hub_root)
        before = self._snapshot(worktree, policy)
        state = self.store.read_state(project, task)
        digest = plan_hash(self.store.read_spec(project, task))
        run_id, directory = self._new_run(project, task)
        start = time.monotonic()
        try:
            completed = subprocess.run(
                test_command,
                cwd=worktree,
                capture_output=True,
                timeout=timeout_s,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_child_env(),
            )
            code, output = completed.returncode, completed.stdout + completed.stderr
        except subprocess.TimeoutExpired as exc:
            code = -1
            output = "Test command timed out\n" + (exc.stdout or b"").decode(
                "utf-8", errors="replace"
            )
            output += (exc.stderr or b"").decode("utf-8", errors="replace")
        except OSError as exc:
            code, output = -1, str(exc)
        result = {
            "exit_code": code,
            "passed": code == 0,
            "duration": time.monotonic() - start,
            "round": state.get("round", 1), "plan_hash": digest,
            "policy_hash": policy.policy_hash, "files": before,
        }
        if before != self._snapshot(worktree, policy):
            result["passed"] = False
        self._write(directory / "test-log.txt", scrub(output))
        self._event(
            project,
            task,
            "tests.finished",
            result,
            run_id,
            {"kind": "tests", "status": "finished", **result},
        )
        with self.store.transaction(project, task) as txn:
            txn.state["last_test_run"] = run_id
            txn.emit("tests.recorded", {"set": {"last_test_run": run_id}})
        return result

    def scope_check(
        self, project: str, task: str, worktree: Path, allowed_globs: list[str]
    ) -> list[str]:
        policy = load_policy(self.hub_root)
        violations = check_scope(self.worktrees.changed_files(worktree, policy.ignored_artifact_globs), allowed_globs)
        if violations:
            with self.store.transaction(project, task) as txn:
                updates = {"status": "needs-you"}
                txn.state.update(updates)
                txn.emit("scope.violation", {"paths": violations, "set": updates})
        return violations

    def _tasks(self) -> Iterator[tuple[str, str, dict]]:
        for path in sorted((self.hub_root / "projects").glob("*/tasks/*/state.md")):
            project, task = path.parents[2].name, path.parent.name
            yield project, task, self.store.read_state(project, task)

    def live_runs(self) -> list[dict]:
        return [
            {**run, "project": project, "task": task, "run": run_id}
            for project, task, state in self._tasks()
            for run_id, run in state.get("runs", {}).items()
            if run.get("status") == "running"
            and is_same_process(run.get("pid"), run.get("create_time"))
        ]

    def stop(self, pid: int, create_time: float) -> None:
        owned = any(
            run.get("pid") == pid and run.get("create_time") == create_time
            for run in self.live_runs()
        )
        if not owned or not is_same_process(pid, create_time):
            raise PolicyError("refusing to signal a foreign or reused PID")
        try:
            process = psutil.Process(pid)
            if abs(process.create_time() - create_time) > 1:
                raise PolicyError("PID identity changed")
            process.terminate()
        except (psutil.Error, OSError) as exc:
            raise PolicyError("could not stop owned process") from exc

    def _snapshot(self, worktree: Path, policy) -> dict[str, str]:
        files = {}
        for name in self.worktrees.changed_files(worktree, policy.ignored_artifact_globs):
            path = worktree / name
            if check_scope([name], ["*"]) or not path.resolve().is_relative_to(worktree.resolve()):
                raise PolicyError("changed path escapes task worktree")
            if path.is_dir():
                raise PolicyError("changed directory cannot be committed as a file")
            files[name] = sha256_file(path) if path.exists() else "deleted"
        return files

    def commit_task(self, project: str, task: str) -> str:
        policy = load_policy(self.hub_root)
        worktree = worktree_path(policy, project, task)
        if not (worktree / ".git").is_file():
            raise PolicyError("commit requires the task worktree")
        with self.store.transaction(project, task) as txn:
            state = txn.state
            if load_policy(self.hub_root) != policy:
                raise PolicyError("policy changed while waiting to commit")
            if state.get("status") != "ready_to_commit":
                raise PolicyError("task not ready to commit")
            if any(r.get("status") in {"running", "intent"} for r in state.get("runs", {}).values()):
                raise PolicyError("task still has active runs")
            spec = self.store.read_spec(project, task)
            digest = plan_hash(spec)
            check_approval(state.get("approval"), project=project, task=task,
                           plan_hash=digest, policy_hash=policy.policy_hash,
                           used_nonces=approval_nonces(state))
            tests = state.get("runs", {}).get(state.get("last_test_run"), {})
            round_no = state.get("round", 1)
            if (tests.get("kind") != "tests" or tests.get("passed") is not True
                    or tests.get("exit_code") != 0 or tests.get("round") != round_no):
                raise PolicyError("last trusted tests must pass for the current round")
            review = state.get("review", {})
            review_run = state.get("runs", {}).get(review.get("run"), {})
            if (review.get("verdict") != "PASS" or review.get("round") != round_no
                    or review.get("test_run") != state.get("last_test_run")
                    or review_run.get("role") != "reviewer" or review_run.get("status") != "ok"):
                raise PolicyError("review PASS required for the current round and tests")
            files = self._snapshot(worktree, policy)
            if files != tests.get("files"):
                raise PolicyError("task files changed since trusted tests")
            project_text = read_text_retry(self.hub_root / "projects" / project / "project.md")
            blocks = re.findall(r"^```hub-project\s*\n(.*?)^```[ \t]*$", project_text, re.M | re.S)
            if len(blocks) != 1:
                raise PolicyError("project configuration missing")
            config = yaml.safe_load(blocks[0])
            violations = check_scope(list(files), config["allowed_paths"] + approved_scope(spec))
            if violations:
                raise PolicyError(f"scope check failed: {violations}")
            if self.worktrees._git(["rev-parse", "--abbrev-ref", "HEAD"], worktree).strip() != f"hub/{task}":
                raise PolicyError("commit branch must match the task")
            if not files:
                raise PolicyError("task has no changed files to commit")
            title = state.get("title") or next((line[2:].strip() for line in spec.splitlines() if line.startswith("# ")), task)
            message = f"{task}: {title} (tests PASS, review PASS, Security Gate NOT PASS)"
            self.worktrees._git(["add", "--", *files], worktree)
            self.worktrees._git(["commit", "--no-gpg-sign", "-m", message], worktree)
            sha = self.worktrees._git(["rev-parse", "HEAD"], worktree).strip()
            updates = {"status": "committed", "commit_sha": sha}
            state.update(updates)
            txn.emit("commit.created", {"sha": sha, "files": list(files), "set": updates})
        return sha
