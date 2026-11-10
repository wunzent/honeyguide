from datetime import datetime, timezone
import pytest
import state_writer
from approvals import ApprovalError, WorkerContextError, build_record, check_approval, check_record, approval_nonces, ensure_not_worker
from hashing import canonical, sha256_text, sha256_file
from state_writer import StateStore, get_approval_block, plan_hash, plan_section, set_approval_block, approved_scope

MOMENT = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
SPEC = "# Task\n\n## Proposed Plan\n\nImplement the scoped feature.\n\n## Notes\nPreserve this.\n"


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


def record(**changes):
    values = dict(project="p", task="t", plan_hash=plan_hash(SPEC), policy_hash="b" * 64,
                  quote="  approve exactly this\n", desktop="codex", now=MOMENT)
    values.update(changes)
    return build_record(values.pop("kind", "approve-plan"), **values)


def check(value, **changes):
    bindings = dict(project="p", task="t", plan_hash=plan_hash(SPEC), policy_hash="b" * 64,
                    used_nonces=[])
    bindings.update(changes)
    return check_approval(value, **bindings)


def test_hash_helpers(tmp_path):
    path = tmp_path / "file"
    path.write_bytes(b"a\r\nb")
    assert sha256_file(path) != sha256_text("a\r\nb")
    assert sha256_text("a\r\nb") == sha256_text("a\nb")
    assert canonical({"z": "ไทย", "a": 1}) == '{"a":1,"z":"ไทย"}'.encode()


@pytest.mark.parametrize("kind", ["approve-plan", "answer", "approve-scope", "pause", "resume", "cancel"])
def test_record_kinds_and_exact_quote(kind):
    value = record(kind=kind, question_id="q" if kind == "answer" else "", extra={"add": ["src/*"]})
    assert value["quote"] == "  approve exactly this\n"
    assert value["recorded_by"] == "orchestrator" and value["at"] == MOMENT.isoformat()
    assert len(value["nonce"]) == 32 and value["nonce"] != record()["nonce"]
    assert value["extra"] == {"add": ["src/*"]}


@pytest.mark.parametrize("changes", [{"quote": ""}, {"quote": " \n"}, {"quote": "x" * 2001},
    {"quote": None}, {"desktop": "worker"}, {"kind": "unknown"}, {"extra": []},
    {"now": MOMENT.replace(tzinfo=None)}, {"kind": "answer"}])
def test_invalid_records(changes):
    with pytest.raises(ApprovalError):
        record(**changes)


@pytest.mark.parametrize("change", [{"kind": "pause"}, {"recorded_by": "worker"}, {"project": "other"},
    {"task": "other"}, {"plan_hash": "c" * 64}, {"policy_hash": "c" * 64}, {"quote": " "},
    {"nonce": "bad"}, {"desktop": "worker"}, {"at": "bad"}, {"answer": None}])
def test_approval_binding_and_validation(change):
    with pytest.raises(ApprovalError):
        check(record() | change)


def test_current_approval_reusable_but_duplicate_history_rejected():
    first, current = record(), record()
    state = {"approval": current, "approval_history": [first, current]}
    nonces = approval_nonces(state)
    for _ in range(3):
        assert check(current, used_nonces=nonces) is None
    with pytest.raises(ApprovalError):
        check(first, used_nonces=nonces)
    state["approval_history"].append(current)
    with pytest.raises(ApprovalError):
        check(current, used_nonces=approval_nonces(state))
    with pytest.raises(ApprovalError):
        check(current, used_nonces=[current["nonce"]])


def test_answer_record_binding():
    value = record(kind="answer", question_id="q", answer="A")
    bindings = dict(kind="answer", project="p", task="t", plan_hash=plan_hash(SPEC),
                    policy_hash="b" * 64, used_nonces=[], question_id="q")
    assert check_record(value, **bindings) is None
    with pytest.raises(ApprovalError):
        check_record(value, **(bindings | {"question_id": "other"}))


@pytest.mark.parametrize("env,inside", [({"HUB_WORKER": "1"}, False), ({"HUB_RUN_TOKEN": ""}, False),
                                       ({"HUB_RUN_TOKEN": "token"}, False), ({}, True)])
def test_worker_context_refused(tmp_path, env, inside):
    root = tmp_path / "data"
    with pytest.raises(WorkerContextError):
        ensure_not_worker(env, root / "task" if inside else tmp_path, root)


def test_orchestrator_context_allowed(tmp_path):
    assert ensure_not_worker({}, tmp_path, tmp_path / "data") is None


@pytest.mark.parametrize("body", ["[]", "- src/*\n- tests/*"])
def test_scope_block(body):
    spec = "## Proposed Plan\nDo work\n```hub-scope\n" + body + "\n```\n"
    assert approved_scope(spec) == ([] if body == "[]" else ["src/*", "tests/*"])
    assert approved_scope(SPEC) == []


@pytest.mark.parametrize("body", ["{}", "- 1", "- ''", "null"])
def test_scope_block_rejects_invalid_yaml_list(body):
    with pytest.raises(ValueError):
        approved_scope("## Proposed Plan\n```hub-scope\n" + body + "\n```\n")


def test_transaction_spec_and_approval_recover_together(tmp_path):
    store = StateStore(tmp_path)
    store.write_spec("p", "t", SPEC)
    def crash(phase):
        if phase == "after_event_append":
            raise RuntimeError("crash")
    broken = StateStore(tmp_path, fault_hook=crash)
    value = record()
    with pytest.raises(RuntimeError):
        with broken.transaction("p", "t") as txn:
            txn.write_spec(SPEC + "\nExtra notes\n")
            txn.state["approval"] = value
            txn.emit("approval.recorded", {"record": value, "set": {"approval": value}})
    store.recover("p", "t")
    assert store.read_spec("p", "t") == SPEC + "\nExtra notes\n"
    assert store.read_state("p", "t")["approval"] == value


