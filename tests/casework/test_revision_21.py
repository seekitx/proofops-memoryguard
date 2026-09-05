"""Regression specifications for the 3ff9863 review. No live providers or funds."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from proofops_casework.core import CaseworkError, seal
from proofops_casework.models import HandoffCommand, ReopenCommand
from proofops_casework.receipts import bound_receipt, expected_model_context_hash
from proofops_casework.store import SibylWorkspaceStore
from .support import Harness
from .test_anchor import configured


def test_expired_grandparent_blocks_grandchild_even_when_direct_parent_was_newer():
    h = Harness(); h.baseline(); root = h.task()["task"]["task_id"]
    h.time += timedelta(minutes=5)
    h.baseline(2); parent = h.task(2, depends=[root])["task"]["task_id"]
    h.time += timedelta(minutes=1)
    h.baseline(3); child = h.task(3, depends=[parent])["task"]["task_id"]
    h.time += timedelta(minutes=5)
    result = h.evaluate(child, review=True)
    assert result["verdict"] == "NEEDS_HUMAN"
    assert result["reason_codes"] == ["DEPENDENCY_REVIEW_REQUIRED"]


def test_ready_proof_cannot_outlive_its_baseline_or_ancestor():
    h = Harness(); h.baseline(expires_at=h.time + timedelta(seconds=90)); h.baseline(2)
    root = h.task(); child = h.task(2, depends=[root["task"]["task_id"]])
    assert root["decision"]["expires_at"] == child["decision"]["expires_at"]
    assert datetime.fromisoformat(root["decision"]["expires_at"].replace("Z", "+00:00")) == h.time + timedelta(seconds=90)


def test_overview_never_calls_expired_baseline_proof_current():
    h = Harness(); h.baseline(expires_at=h.time + timedelta(seconds=2)); h.task()
    h.time += timedelta(seconds=3)
    task = h.svc.overview(h.actors["viewer"])["tasks"][0]
    assert task["current_proof_valid"] is False
    assert task["effective_reason_codes"] == ["BASELINE_EXPIRED"]
    assert task["review_preparable"] is False


def test_recovery_is_read_only_topological_and_does_not_include_unrelated_tasks():
    h = Harness()
    for n in (1, 2, 3): h.baseline(n)
    root = h.task()["task"]["task_id"]
    child = h.task(2, depends=[root])["task"]["task_id"]
    other = h.task(3)["task"]["task_id"]
    cid = h.risk()["case"]["case_id"]
    before = h.store.load("tenant_demo").state_root
    plan = h.svc.recovery(h.actors["viewer"], child)
    assert [step["task_id"] for step in plan["ordered_steps"]] == [root, child]
    assert other not in str(plan)
    assert all(cid in step["active_blockers"] for step in plan["ordered_steps"])
    assert before == h.store.load("tenant_demo").state_root
    assert plan["read_only"] and plan["executable"] is False


def test_recovery_query_rechecks_subject_permissions():
    h = Harness(); tid = h.task()["task"]["task_id"]
    actor = h.actors["viewer"].model_copy(update={"subjects": ["other_subject"]})
    with pytest.raises(CaseworkError, match="TASK_NOT_FOUND"):
        h.svc.recovery(actor, tid)


def test_reopening_a_precedent_invalidates_zero_task_investigation():
    h = Harness(); first = h.risk()["case"]["case_id"]; h.resolve(first)
    second = h.risk()["case"]["case_id"]
    report = h.investigate(second)["report"]
    assert report["precedent_ids"]
    h.svc.reopen_case(h.actors["owner"], h.command(ReopenCommand, evidence_digest="a"*64), first)
    assert not h.investigate(second)["report"]["precedent_ids"]
    with pytest.raises(CaseworkError, match="STALE_INVESTIGATION"):
        h.handoff(second, report["report_id"])


def test_unversioned_legacy_lesson_is_retained_but_not_reused():
    h = Harness(); first = h.risk()["case"]["case_id"]; h.resolve(first)
    state = h.store.states["tenant_demo"]
    for lesson in state.lessons.values():
        lesson.pop("case_version"); lesson.pop("resolved_seq")
    seal(state)
    second = h.risk()["case"]["case_id"]
    assert not h.investigate(second)["report"]["precedent_ids"]
    assert len(h.store.load("tenant_demo").lessons) == 1


def test_denial_creates_a_persisted_non_executable_artifact_not_only_a_tool_label():
    h = Harness(); h.baseline(); tid = h.task()["task"]["task_id"]; h.risk()
    decision = h.evaluate(tid)
    artifacts = h.svc.replay(h.actors["viewer"], tid)["safety_artifacts"]
    found = [x for x in artifacts if x.get("decision_id") == decision["decision_id"]]
    assert len(found) == 1
    assert found[0]["kind"] == "OPERATOR_ESCALATION"
    assert found[0]["proof_root"] == decision["proof_root"]
    assert found[0]["executable"] is False


def good_receipt(context, tools):
    return {"generation_id": "synthetic-generation", "resolved_model": "synthetic-model",
        "configured_model": "synthetic-model", "completed_at": "2026-09-05T12:00:00Z",
        "backend": "remote_structured_model", "live_call_verified": True,
        "structured_output_validated": True, "completion_sha256": "a"*64,
        "model_context_hash": expected_model_context_hash(context, tools)}


@pytest.mark.parametrize("field,value", [("model_context_hash", "b"*64),
    ("structured_output_validated", False), ("live_call_verified", False),
    ("completion_sha256", "bogus"), ("backend", "deterministic"),
    ("completed_at", "2026-09-05T12:00:00"), ("resolved_model", 42)])
def test_model_receipt_requires_current_request_and_strict_fields(field, value):
    context = {"verdict": "deny"}; tools = ("case.inspect",)
    record = good_receipt(context, tools); record[field] = value
    with pytest.raises(ValueError): bound_receipt(record, context, tools)


def test_invalid_receipt_degrades_instead_of_claiming_real_model():
    class Model:
        def plan(self, context, allowed_tools):
            record = good_receipt(context, allowed_tools); record["model_context_hash"] = "b"*64
            return SimpleNamespace(requested_tools=("precedent.lookup",), model_receipt=record)
    h = Harness(model=Model()); cid = h.risk()["case"]["case_id"]
    report = h.investigate(cid)["report"]
    assert report["planner_status"] == "DEGRADED" and report["model_receipt"] is None
    assert [x["tool"] for x in report["trace"]] == ["case.inspect", "dependencies.trace"]


@pytest.mark.parametrize("field,value", [("hash", "0x"+"9"*64),
    ("blockHash", "0x"+"9"*64), ("blockNumber", hex(99))])
def test_transaction_object_must_match_receipt_identity(field, value):
    a, replies, plan, tx = configured(); replies["eth_getTransactionByHash"][field] = value
    with pytest.raises(CaseworkError): a.verify(plan, tx)


def test_zero_anchor_root_is_rejected_before_wallet_plan():
    a, _, _, _ = configured()
    with pytest.raises(CaseworkError): a.plan("0"*64, 1, 84532)


def test_anchor_transaction_binding_and_idempotent_replay_do_not_requery_rpc():
    class Anchor:
        calls = 0
        def plan(self, root, version, chain):
            return {"proof_root": root, "memory_version": version, "chain_id": chain}
        def verify(self, plan, tx):
            self.calls += 1
            return {"state": "PENDING", "tx_hash": tx, "audit_only": True}
    h = Harness(); h.baseline(); task = h.task(); h.svc.anchor = anchor = Anchor()
    record = h.svc.prepare_anchor(h.actors["reviewer"], h.command(), task["task"]["task_id"],
                                  task["decision"]["decision_id"])["anchor"]
    command = h.command(); tx = "0x"+"a"*64
    h.svc.verify_anchor(h.actors["reviewer"], command, record["anchor_id"], tx)
    again = h.svc.verify_anchor(h.actors["reviewer"], command, record["anchor_id"], tx)
    assert again["historical_only"] and anchor.calls == 1
    with pytest.raises(CaseworkError, match="ANCHOR_TRANSACTION_ALREADY_BOUND"):
        h.svc.verify_anchor(h.actors["reviewer"], h.command(), record["anchor_id"], "0x"+"b"*64)
    assert anchor.calls == 1


def test_deleted_or_replaced_file_is_detected_before_reusing_cached_sdk_handle(tmp_path):
    # This tests inode guarding only; it does NOT pretend to be an SDK integration.
    store = object.__new__(SibylWorkspaceStore)
    store.path = tmp_path / "fixture.db"; store.path.write_bytes(b"inert-fixture")
    stat = store.path.stat(); store.database_identity = (stat.st_dev, stat.st_ino)
    store._check_database_identity()
    store.path.unlink()
    with pytest.raises(CaseworkError, match="REMOVED"):
        store._check_database_identity()
    store.path.write_bytes(b"inert-new-fixture")
    store.database_identity = (-1, -1)  # don't rely on OS inode reuse behavior
    with pytest.raises(CaseworkError, match="REPLACED"):
        store._check_database_identity()
