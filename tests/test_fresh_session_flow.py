from __future__ import annotations

from proofops_memoryguard.adapters import DisabledAnchorAdapter, InMemoryMemoryAdapter
from proofops_memoryguard.models import (
    EvidenceMode,
    Observation,
    ObservationKind,
    PaymentIntent,
    Verdict,
)
from proofops_memoryguard.module import MemoryGuard

TARGET = "0x1111111111111111111111111111111111111111"


def observation(kind: ObservationKind, session_id: str, facts: dict[str, object], key: str) -> Observation:
    return Observation(
        subject_id="judge-case-fresh-session",
        session_id=session_id,
        kind=kind,
        source_id="demo_fixture:trusted-feed",
        facts=facts,
        evidence_mode=EvidenceMode.DEMO_FIXTURE,
        idempotency_key=key,
    )


def intent(session_id: str, key: str) -> PaymentIntent:
    return PaymentIntent(
        subject_id="judge-case-fresh-session",
        session_id=session_id,
        chain_id=84532,
        target=TARGET,
        method="payInvoice",
        amount_usd=4200,
        idempotency_key=key,
        evidence_mode=EvidenceMode.DEMO_FIXTURE,
    )


def test_same_intent_changes_only_after_cross_session_recall(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    session_a = "session-a-0001"
    guard_a = MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=policy,
        production=False,
    )
    baseline = guard_a.observe(
        observation(
            ObservationKind.BASELINE_APPROVED,
            session_a,
            {
                "chain_id": 84532,
                "target": TARGET,
                "method": "payInvoice",
                "max_amount_usd": 5000,
            },
            "baseline-fresh-case",
        )
    )
    before = guard_a.decide(intent(session_a, "decision-before-incident"))
    dispute = guard_a.observe(
        observation(
            ObservationKind.DISPUTE_OPENED,
            session_a,
            {"target": TARGET, "dispute_id": "disp-42", "status": "open"},
            "dispute-fresh-case",
        )
    )

    # A new Module instance has no in-process state from guard_a. The shared
    # Memory Adapter is the only path by which Session B can see the dispute.
    guard_b = MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=policy,
        production=False,
    )
    after = guard_b.decide(intent("session-b-0002", "decision-after-incident"))

    assert baseline.status.value == "accepted"
    assert before.verdict == Verdict.READY
    assert before.cross_session is False
    assert before.causal_memory_ids == (baseline.observation_id,)
    assert before.intent_hash == after.intent_hash
    assert after.verdict == Verdict.DENY
    assert after.cross_session is True
    assert after.causal_memory_ids == (dispute.observation_id,)
    assert after.reason_codes == ("open_dispute_recalled_from_persistent_memory",)
    assert before.to_dict()["executable"] is False
    assert after.to_dict()["executable"] is False
