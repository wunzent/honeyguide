from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import multiprocessing as mp
import os
from pathlib import Path
import time

import pytest
import yaml

import state_writer
from state_writer import (
    Event, StateStore, StateWriteError, apply_event, atomic_write_text, read_text_retry,
)


def _increment(root: Path, count: int, start) -> None:
    store = StateStore(root, lock_timeout=90)
    if not start.wait(20):
        raise TimeoutError("start gate")
    for _ in range(count):
        with store.transaction("project", "T-1") as txn:
            counter = txn.state.get("counter", 0) + 1
            txn.state["counter"] = counter
            txn.emit("counter.updated", {"set": {"counter": counter}})


def _crash(root: Path, point: str) -> None:
    def fault(actual: str) -> None:
        if point == actual:
            os._exit(17)

    with StateStore(root, fault_hook=fault).transaction("project", "T-1") as txn:
        txn.state["counter"] = 42
        txn.emit("counter.updated", {"set": {"counter": 42}})


def _try_lock(root: Path, operation: str, result) -> None:
    store = StateStore(root, lock_timeout=0.05)
    try:
        if operation == "transaction":
            with store.transaction("other", "T-2"):
                pass
        elif operation == "recover":
            store.recover("other", "T-2")
        else:
            store.write_runtime_file("schedule.md", "test")
    except TimeoutError:
        result.put("timeout")
    else:
        result.put("unexpected success")


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path, replace_backoff=0)


def test_empty_reads_and_ids(store: StateStore) -> None:
    assert store.task_dir("Project-1", "T-1") == (
        store.root / "projects" / "Project-1" / "tasks" / "T-1"
    )
    assert store.read_state("project", "T-1")["last_event_seq"] == 0
    assert store.read_events("project", "T-1") == []
    assert not (store.root / "projects").exists()


@pytest.mark.parametrize("invalid", ["", "../x", "x/y", "x\\y", "a_b", "a" * 33, "ไทย", "x\n"])
def test_invalid_ids(store: StateStore, invalid: str) -> None:
    for project, task in [(invalid, "T-1"), ("project", invalid)]:
        with pytest.raises(ValueError):
            store.task_dir(project, task)


@pytest.mark.parametrize("options", [
    {"lock_timeout": -1}, {"replace_retries": -1}, {"replace_backoff": -1},
])
def test_invalid_store_options(tmp_path: Path, options: dict) -> None:
    with pytest.raises(ValueError):
        StateStore(tmp_path, **options)


def test_transaction_formats_sequence_and_snapshot(store: StateStore) -> None:
    payload = {"set": {"counter": 1}, "text": "ไทย | line\nnext\u0085\u2028"}
    with store.transaction("project", "T-1") as txn:
        txn.state["counter"] = 1
        assert txn.emit("spawn.intent", payload) == 1
        payload["set"]["counter"] = 999
        assert txn.emit("spawn.started", {"key": "T-1:coder:1", "pid": 123}) == 2
        txn.state["last_event_seq"] = 999  # Writer owns the cursor.
    state = store.read_state("project", "T-1")
    assert state["counter"] == 1
    assert state["last_event_seq"] == 2
    directory = store.task_dir("project", "T-1")
    text = (directory / "state.md").read_text(encoding="utf-8")
    assert text.startswith("# Task state\n")
    assert yaml.safe_load(text.split("```hub-state\n")[1].split("```")[0]) == state
    lines = (directory / "events.md").read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert len(lines) == 2
    assert lines[0].startswith("- 000001 | ")
    assert '"set":{"counter":1}' in lines[0]
    events = store.read_events("project", "T-1")
    assert [event.seq for event in events] == [1, 2]
    assert events[0].data["set"]["counter"] == 1
    assert events[0].data["text"] == "ไทย | line\nnext\u0085\u2028"
    assert datetime.fromisoformat(events[0].ts).utcoffset() is not None
    with store.transaction("project", "T-1") as txn:
        assert txn.emit("run.lost", {}) == 3
    assert store.read_state("project", "T-1")["last_event_seq"] == 3


def test_exception_rolls_back_and_releases_lock(store: StateStore) -> None:
    with pytest.raises(RuntimeError):
        with store.transaction("project", "T-1") as txn:
            txn.state["counter"] = 9
            txn.emit("changed", {"set": {"counter": 9}})
            raise RuntimeError("abort")
    assert store.read_events("project", "T-1") == []
    assert not store.task_dir("project", "T-1").exists()
    with store.transaction("project", "T-1") as txn:
        assert txn.emit("changed", {}) == 1
    directory = store.task_dir("project", "T-1")
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(RuntimeError):
        with store.transaction("project", "T-1") as txn:
            txn.emit("changed", {})
            raise RuntimeError("abort")
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}


@pytest.mark.parametrize("kind,data", [("bad | kind", {}), ("x\ny", {}), ("ok", []), ("ok", {"set": []})])
def test_invalid_event_writes_nothing(store: StateStore, kind: str, data) -> None:
    with pytest.raises(ValueError):
        with store.transaction("project", "T-1") as txn:
            txn.emit(kind, data)
    assert store.read_events("project", "T-1") == []


def test_unserializable_state_does_not_append(store: StateStore) -> None:
    with pytest.raises(yaml.representer.RepresenterError):
        with store.transaction("project", "T-1") as txn:
            txn.emit("changed", {})
            txn.state["invalid"] = object()
    assert store.read_events("project", "T-1") == []


def test_apply_event_is_pure_and_uses_only_set() -> None:
    state = {"nested": {"old": [1]}, "keep": True, "last_event_seq": 1}
    event = Event(2, "2026-11-09T17:40:00+07:00", "agent.result", "T-1",
                  {"set": {"nested": {"new": [2]}, "last_event_seq": 999},
                   "text": "APPROVED", "spawn": "never execute"})
    original_state, original_event = deepcopy(state), deepcopy(event)
    result = apply_event(state, event)
    assert result == {"nested": {"new": [2]}, "keep": True, "last_event_seq": 2}
    result["nested"]["new"].append(3)
    assert state == original_state
    assert event == original_event
    assert apply_event(state, Event(3, "", "unknown", "T-1", {}))["last_event_seq"] == 3


def test_concurrent_writes(tmp_path: Path) -> None:
    context = mp.get_context("spawn")
    start = context.Event()
    processes = [context.Process(target=_increment, args=(tmp_path, 200, start)) for _ in range(8)]
    for process in processes:
        process.start()
    start.set()
    deadline = time.monotonic() + 120
    try:
        for process in processes:
            process.join(max(0, deadline - time.monotonic()))
        assert [process.exitcode for process in processes] == [0] * 8
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
            process.join()
    store = StateStore(tmp_path)
    assert store.read_state("project", "T-1")["counter"] == 1600
    assert store.read_state("project", "T-1")["last_event_seq"] == 1600
    events = store.read_events("project", "T-1")
    assert [event.seq for event in events] == list(range(1, 1601))
    assert [event.data["set"]["counter"] for event in events] == list(range(1, 1601))


@pytest.mark.parametrize("point", ["after_event_append", "before_replace"])
def test_process_crash_and_recovery(store: StateStore, point: str) -> None:
    with store.transaction("project", "T-1") as txn:
        txn.state["counter"] = 1
        txn.emit("counter.updated", {"set": {"counter": 1}})
    process = mp.get_context("spawn").Process(target=_crash, args=(store.root, point))
    process.start()
    process.join(20)
    try:
        assert process.exitcode == 17
    finally:
        if process.is_alive():
            process.terminate()
        process.join()
    assert store.read_state("project", "T-1")["counter"] == 1
    assert len(store.read_events("project", "T-1")) == 2
    if point == "before_replace":
        assert list(store.task_dir("project", "T-1").glob("state.md.tmp-*"))
    store.recover("project", "T-1")
    expected = store.read_state("project", "T-1")
    assert expected["counter"] == 42
    assert expected["last_event_seq"] == 2
    assert not list(store.task_dir("project", "T-1").glob("*.tmp-*"))
    store.recover("project", "T-1")
    assert store.read_state("project", "T-1") == expected


def test_write_order_and_fault_points(store: StateStore, monkeypatch) -> None:
    with store.transaction("project", "T-1") as txn:
        txn.emit("changed", {})
    ordered = []
    fsync, replace = os.fsync, os.replace

    def synced(descriptor):
        fsync(descriptor)
        ordered.append("fsync")

    def replaced(source, target):
        ordered.append("replace")
        replace(source, target)

    def fault(point: str) -> None:
        ordered.append(point)
        assert store.read_events("project", "T-1")[-1].seq == 2
        assert store.read_state("project", "T-1")["last_event_seq"] == 1
        if point == "before_replace":
            temporary = store.task_dir("project", "T-1") / f"state.md.tmp-{os.getpid()}"
            assert "last_event_seq: 2" in temporary.read_text(encoding="utf-8")

    monkeypatch.setattr(state_writer.os, "fsync", synced)
    monkeypatch.setattr(state_writer.os, "replace", replaced)
    store = StateStore(store.root, fault_hook=fault)
    with store.transaction("project", "T-1") as txn:
        txn.emit("changed", {})
    assert ordered == ["fsync", "after_event_append", "fsync", "before_replace", "replace"]


def test_recovery_without_initial_state_and_next_transaction(store: StateStore) -> None:
    def fault(point: str) -> None:
        if point == "after_event_append":
            raise RuntimeError("simulated crash")

    with pytest.raises(RuntimeError):
        with StateStore(store.root, fault_hook=fault).transaction("project", "T-1") as txn:
            txn.emit("changed", {"set": {"counter": 7}})
            txn.emit("changed", {"set": {"counter": 8}})
    with store.transaction("project", "T-1") as txn:
        assert txn.state["counter"] == 8
        assert txn.emit("changed", {"set": {"counter": 9}}) == 3
        txn.state["counter"] = 9
    assert store.read_state("project", "T-1")["counter"] == 9


def test_aborted_transaction_does_not_checkpoint_pending_events(store: StateStore) -> None:
    with store.transaction("project", "T-1") as txn:
        txn.emit("changed", {})
    directory = store.task_dir("project", "T-1")
    original_state = (directory / "state.md").read_bytes()

    def fault(point: str) -> None:
        if point == "after_event_append":
            raise RuntimeError("simulated crash")

    with pytest.raises(RuntimeError):
        with StateStore(store.root, fault_hook=fault).transaction("project", "T-1") as txn:
            txn.emit("changed", {"set": {"counter": 7}})
    original_events = (directory / "events.md").read_bytes()
    with pytest.raises(RuntimeError):
        with store.transaction("project", "T-1") as txn:
            assert txn.state["counter"] == 7
            txn.emit("changed", {"set": {"counter": 8}})
            raise RuntimeError("abort")
    assert (directory / "state.md").read_bytes() == original_state
    assert (directory / "events.md").read_bytes() == original_events
    store.recover("project", "T-1")
    assert store.read_state("project", "T-1")["counter"] == 7


def test_stale_tmp_cleanup_only_for_selected_task(store: StateStore) -> None:
    directory = store.task_dir("project", "T-1")
    directory.mkdir(parents=True)
    stale = directory / "state.md.tmp-12345"
    stale.write_text("partial", encoding="utf-8")
    keep = directory / "result.md"
    keep.write_text("keep", encoding="utf-8")
    other = store.task_dir("project", "T-2")
    other.mkdir()
    other_stale = other / "state.md.tmp-12345"
    other_stale.write_text("keep", encoding="utf-8")
    store.recover("project", "T-1")
    assert not stale.exists()
    assert keep.read_text(encoding="utf-8") == "keep"
    assert other_stale.exists()


@pytest.mark.parametrize("operation", ["transaction", "recover", "runtime"])
def test_global_lock_timeout(store: StateStore, operation: str) -> None:
    context = mp.get_context("spawn")
    result = context.Queue()
    with store.transaction("project", "T-1"):
        process = context.Process(target=_try_lock, args=(store.root, operation, result))
        process.start()
        try:
            assert result.get(timeout=20) == "timeout"
        finally:
            process.join(10)
            if process.is_alive():
                process.terminate()
                process.join()
            result.close()
            result.join_thread()
        assert process.exitcode == 0


@pytest.mark.parametrize("failures", [1, 3])
def test_replace_permission_retry(store: StateStore, monkeypatch, failures: int) -> None:
    replace = os.replace
    attempts = []
    sleeps = []

    def flaky(source, target):
        attempts.append((source, target))
        if len(attempts) <= failures:
            raise PermissionError("sharing violation")
        replace(source, target)

    monkeypatch.setattr(state_writer.os, "replace", flaky)
    monkeypatch.setattr(state_writer.time, "sleep", sleeps.append)
    store.replace_backoff = 0.01
    with store.transaction("project", "T-1") as txn:
        txn.emit("changed", {})
    assert len(attempts) == failures + 1
    assert sleeps == [0.01 * attempt for attempt in range(1, failures + 1)]
    assert store.read_state("project", "T-1")["last_event_seq"] == 1
    assert not list(store.task_dir("project", "T-1").glob("*.tmp-*"))


def test_replace_cap_preserves_original_then_recover(store: StateStore, monkeypatch) -> None:
    with store.transaction("project", "T-1") as txn:
        txn.state["counter"] = 1
        txn.emit("changed", {"set": {"counter": 1}})
    path = store.task_dir("project", "T-1") / "state.md"
    original = path.read_bytes()
    attempts = []

    def denied(source, target):
        attempts.append(source)
        raise PermissionError("sharing violation")

    with monkeypatch.context() as patch:
        patch.setattr(state_writer.os, "replace", denied)
        store.replace_retries = 2
        with pytest.raises(StateWriteError):
            with store.transaction("project", "T-1") as txn:
                txn.state["counter"] = 2
                txn.emit("changed", {"set": {"counter": 2}})
    assert len(attempts) == 3
    assert path.read_bytes() == original
    assert attempts[0].name == f"state.md.tmp-{os.getpid()}"
    assert attempts[0].exists()
    store.recover("project", "T-1")
    assert store.read_state("project", "T-1")["counter"] == 2
    assert not attempts[0].exists()


def test_atomic_helper_and_read_retry(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "nested" / "runtime.md"
    atomic_write_text(path, "ไทย\n", retries=0, backoff=0)
    read = Path.read_text
    attempts = []
    monkeypatch.setattr(state_writer.time, "sleep", lambda _: None)

    def flaky(self, *args, **kwargs):
        attempts.append(self)
        if len(attempts) <= 2:
            raise PermissionError("reader temporarily blocked")
        return read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky)
    assert read_text_retry(path) == "ไทย\n"
    assert len(attempts) == 3
    attempts.clear()

    def denied(self, *args, **kwargs):
        attempts.append(self)
        raise PermissionError("reader blocked")

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(PermissionError):
        read_text_retry(path)
    assert len(attempts) == 11


@pytest.mark.parametrize("retries,backoff", [(-1, 0), (0, -1)])
def test_atomic_invalid_options(tmp_path: Path, retries: int, backoff: float) -> None:
    with pytest.raises(ValueError):
        atomic_write_text(tmp_path / "state.md", "", retries, backoff)


def test_runtime_files(store: StateStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.read_runtime_file("schedule.md")
    store.write_runtime_file("schedule.md", "| id | due_at |\n")
    assert store.read_runtime_file("schedule.md") == "| id | due_at |\n"
    store.write_runtime_file("schedule.md", "updated\n")
    assert store.read_runtime_file("schedule.md") == "updated\n"
    assert store.read_events("project", "T-1") == []


@pytest.mark.parametrize("name", ["../state.md", "locks/writer.lock", "x\\state.md", "x.txt", "", "x.md\n"])
def test_runtime_filename_validation(store: StateStore, name: str) -> None:
    with pytest.raises(ValueError):
        store.write_runtime_file(name, "bad")
    with pytest.raises(ValueError):
        store.read_runtime_file(name)


@pytest.mark.parametrize("text", ["no fence", "```hub-state\n[]\n```", "```hub-state\nlast_event_seq: -1\n```",
                                  "```hub-state\nlast_event_seq: true\n```",
                                  "```hub-state\nlast_event_seq: 0\n```\n```hub-state\n{}\n```"])
def test_invalid_state_fails_closed(store: StateStore, text: str) -> None:
    directory = store.task_dir("project", "T-1")
    directory.mkdir(parents=True)
    (directory / "state.md").write_text(text, encoding="utf-8")
    with pytest.raises(StateWriteError):
        store.read_state("project", "T-1")


@pytest.mark.parametrize("line", [
    '- 000002 | 2026-11-09T17:40:00+07:00 | changed | T-1 | {}\n',
    '- 000001 | 2026-11-09T17:40:00+07:00 | changed | T-2 | {}\n',
    '- 000001 | 2026-11-09T17:40:00+07:00 | changed | T-1 | []\n',
])
def test_invalid_events_fail_closed(store: StateStore, line: str) -> None:
    directory = store.task_dir("project", "T-1")
    directory.mkdir(parents=True)
    (directory / "events.md").write_text(line, encoding="utf-8")
    with pytest.raises(StateWriteError):
        store.recover("project", "T-1")
    assert not (directory / "state.md").exists()


def test_state_ahead_of_journal_fails_closed(store: StateStore) -> None:
    directory = store.task_dir("project", "T-1")
    directory.mkdir(parents=True)
    (directory / "state.md").write_text("```hub-state\nlast_event_seq: 1\n```\n", encoding="utf-8")
    with pytest.raises(StateWriteError):
        store.recover("project", "T-1")


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing-violation semantics")
def test_real_windows_sharing_violation(store: StateStore, monkeypatch) -> None:
    import ctypes
    from ctypes import wintypes
    import threading

    with store.transaction("project", "T-1") as txn:
        txn.emit("changed", {})
    path = store.task_dir("project", "T-1") / "state.md"
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE (no FILE_SHARE_DELETE).
    handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0x80, None)
    assert handle != wintypes.HANDLE(-1).value
    replace = os.replace
    blocked = []
    release = threading.Event()

    def close_after_block() -> None:
        release.wait(5)
        kernel.CloseHandle(handle)

    thread = threading.Thread(target=close_after_block)
    thread.start()

    def tracked(source, target):
        try:
            replace(source, target)
        except PermissionError:
            blocked.append(True)
            release.set()
            raise

    monkeypatch.setattr(state_writer.os, "replace", tracked)
    store.replace_backoff = 0.01
    try:
        with store.transaction("project", "T-1") as txn:
            txn.emit("changed", {})
    finally:
        release.set()
        thread.join(10)
    assert blocked
    assert not thread.is_alive()
    assert store.read_state("project", "T-1")["last_event_seq"] == 2
