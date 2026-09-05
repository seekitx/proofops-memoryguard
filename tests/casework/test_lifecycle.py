from datetime import timedelta

import pytest
from pydantic import ValidationError

from proofops_casework.core import CaseworkError, digest, seal
from proofops_casework.models import *
from proofops_casework.service import CaseworkService
from .support import Harness, TestStore


def test_complete_recovery_never_resurrects_old_proof():
    h = Harness(); h.baseline()
    initial = h.task(); tid = initial["task"]["task_id"]
    first = initial["decision"]
    risk = h.risk()["case"]["case_id"]
    assert h.evaluate(tid)["verdict"] == "DENY"
    h.resolve(risk)
    assert h.evaluate(tid)["verdict"] == "NEEDS_HUMAN"
    last = h.evaluate(tid, review=True)
    assert last["verdict"] == "READY"
    assert last["action_fingerprint"] == first["action_fingerprint"]
    assert last["proof_root"] != first["proof_root"]
    assert any(item.startswith("resolution:") for item in last["causal_refs"])
    with pytest.raises(CaseworkError, match="DECISION_SUPERSEDED"):
        h.svc.prepare_review(h.actors["reviewer"], h.command(), tid, first["decision_id"])
    result = h.svc.prepare_review(h.actors["reviewer"], h.command(), tid, last["decision_id"])
    assert result["artifact"]["executable"] is False


def test_all_open_cases_must_clear_individually():
    h = Harness(); h.baseline(); tid = h.task()["task"]["task_id"]
    first = h.risk()["case"]["case_id"]
    second = h.risk(kind="revocation")["case"]["case_id"]
    h.resolve(first)
    denied = h.evaluate(tid, review=True)
    assert denied["verdict"] == "DENY"
    assert denied["active_blockers"] == [second]
    h.resolve(second)
    assert h.evaluate(tid, review=True)["verdict"] == "READY"


def test_scope_and_transitive_blast_radius():
    h = Harness()
    for i in range(1, 6): h.baseline(i)
    a = h.task(1)["task"]["task_id"]
    b = h.task(2, depends=[a])["task"]["task_id"]
    c = h.task(3, depends=[b])["task"]["task_id"]
    d = h.task(4, depends=[c])["task"]["task_id"]
    unrelated = h.task(5)["task"]["task_id"]
    # Same scope as a dependent task does not make this independent task dependent.
    independent_b = h.task(2)["task"]["task_id"]
    result = h.risk(1)
    assert set(result["affected_tasks"]) == {a, b, c, d}
    state = h.store.load("tenant_demo")
    assert state.tasks[unrelated].status == state.tasks[independent_b].status == "READY"
    assert h.evaluate(d)["verdict"] == "DENY"
    h.resolve(result["case"]["case_id"])
    assert h.evaluate(d, review=True)["verdict"] == "NEEDS_HUMAN"
    for task in [a, b, c, d]:
        assert h.evaluate(task, review=True)["verdict"] == "READY"


def test_new_task_created_while_blocked_also_requires_review():
    h = Harness(); h.baseline(); case = h.risk()["case"]["case_id"]
    task = h.task(); assert task["decision"]["verdict"] == "DENY"
    h.resolve(case)
    assert h.evaluate(task["task"]["task_id"])["verdict"] == "NEEDS_HUMAN"
    assert h.evaluate(task["task"]["task_id"], review=True)["verdict"] == "READY"


def test_latest_tightened_baseline_is_authoritative():
    h = Harness(); h.baseline(limit=500000); tid = h.task()["task"]["task_id"]
    h.baseline(limit=100000)
    assert h.evaluate(tid, review=True)["reason_codes"] == ["LIMIT_EXCEEDED"]
    h.baseline(limit=500000)
    assert h.evaluate(tid)["verdict"] == "NEEDS_HUMAN"
    assert h.evaluate(tid, review=True)["verdict"] == "READY"


def test_expiry_and_scope_do_not_inherit_a_permissive_baseline():
    h = Harness(); h.baseline(expires_at=h.time + timedelta(seconds=2))
    t = h.task()["task"]["task_id"]
    assert h.task(2)["decision"]["verdict"] == "NEEDS_HUMAN"
    h.time += timedelta(seconds=3)
    assert h.evaluate(t)["reason_codes"] == ["BASELINE_EXPIRED"]


def test_reopen_invalidates_old_handoff():
    h = Harness(); h.baseline(); h.task(); cid = h.risk()["case"]["case_id"]
    h.resolve(cid)
    h.svc.reopen_case(h.actors["owner"], h.command(ReopenCommand, evidence_digest="3" * 64), cid)
    handoff = next(iter(h.store.load("tenant_demo").handoffs))
    with pytest.raises(CaseworkError, match="STALE_INVESTIGATION|STALE_HANDOFF"):
        h.svc.resolve(h.actors["reviewer"], h.command(ResolveCommand, handoff_id=handoff,
            resolution="resolved", evidence_digest="4" * 64), cid)


def test_fresh_service_reads_same_store_not_process_memory():
    h = Harness(); h.baseline(); initial = h.task(); tid = initial["task"]["task_id"]
    h.risk()
    fresh = CaseworkService(h.store, h.svc.actors, test_mode=True, clock=lambda: h.time)
    h.session = "session_beta"
    new = fresh.evaluate(h.actors["owner"], h.command(), tid)["decision"]
    assert new["runtime_id"] != initial["decision"]["runtime_id"]
    assert new["action_fingerprint"] == initial["decision"]["action_fingerprint"]
    assert new["verdict"] == "DENY"
    assert new["tool"] == "operator_escalation.create"
    # Same OS process here; the separate official-SDK subprocess test is separate.


def test_dependency_memory_corruption_fails_closed():
    h = Harness(); h.baseline(); t = h.task()["task"]["task_id"]
    state = h.store.states["tenant_demo"]
    state.tasks[t].depends_on = [t]
    seal(state)  # simulate structurally valid but cyclic legacy/import data
    with pytest.raises(CaseworkError, match="DEPENDENCY_CYCLE"):
        h.evaluate(t)


@pytest.mark.parametrize("amount", [True, 0, -1, 0.1, 1.0, "420000", 100_000_001])
def test_money_requires_bounded_integer_cents(amount):
    with pytest.raises(ValidationError):
        Intent(scope=Harness.scope(), amount_minor=amount)


def test_no_unbounded_test_backend_in_production():
    with pytest.raises(ValueError, match="official Sibyl"):
        CaseworkService(TestStore(), {})
