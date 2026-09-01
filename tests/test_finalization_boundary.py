from __future__ import annotations

import pytest

from proofops_memoryguard.adapters import (
    BaseAnchorAdapter,
    DisabledAnchorAdapter,
    InMemoryMemoryAdapter,
)
from proofops_memoryguard.errors import FinalizationError
from proofops_memoryguard.models import (
    DecisionDraft,
    EvidenceMode,
    Observation,
    ObservationKind,
    PaymentIntent,
)
from proofops_memoryguard.module import MemoryGuard

TARGET = "0x3333333333333333333333333333333333333333"
ANCHOR = "0x4444444444444444444444444444444444444444"


def ready_decision(guard: MemoryGuard) -> DecisionDraft:
    guard.observe(
        Observation(
            subject_id="finalize-case",
            session_id="session-finalize-a",
            kind=ObservationKind.BASELINE_APPROVED,
            source_id="demo_fixture:trusted-approver",
            facts={
                "chain_id": 84532,
                "target": TARGET,
                "method": "payInvoice",
                "max_amount_usd": 100,
            },
            evidence_mode=EvidenceMode.DEMO_FIXTURE,
            idempotency_key="finalize-baseline-0001",
        )
    )
    return guard.decide(
        PaymentIntent(
            subject_id="finalize-case",
            session_id="session-finalize-a",
            chain_id=84532,
            target=TARGET,
            method="payInvoice",
            amount_usd=75,
            idempotency_key="finalize-decision-0001",
            evidence_mode=EvidenceMode.DEMO_FIXTURE,
        )
    )


def test_ready_cannot_finalize_without_base_anchor(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=policy,
        production=False,
    )
    decision = ready_decision(guard)
    result = guard.finalize(decision.decision_id)
    assert result.state.value == "failed"
    assert result.executable is False
    assert result.reason_codes == ("base_anchor_required_before_ready_can_finalize",)


def test_base_plan_is_fixed_by_server_side_decision(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = MemoryGuard(
        memory=memory,
        anchor=BaseAnchorAdapter(
            chain_id=84532,
            network="base-sepolia",
            rpc_url="https://sepolia.base.org",
            contract=ANCHOR,
        ),
        policy=policy,
        production=False,
    )
    decision = ready_decision(guard)
    result = guard.finalize(decision.decision_id)

    assert result.state.value == "confirmation_required"
    assert result.executable is False
    assert result.anchor_plan is not None
    assert result.anchor_plan.to == ANCHOR
    assert result.anchor_plan.proof_root == decision.proof_root
    assert result.anchor_plan.chain_id == 84532
    assert result.anchor_plan.data.startswith("0x")
    assert len(result.anchor_plan.data) == 138


def test_ready_draft_cannot_finalize_after_memory_changes(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = MemoryGuard(
        memory=memory,
        anchor=BaseAnchorAdapter(
            chain_id=84532,
            network="base-sepolia",
            rpc_url="https://sepolia.base.org",
            contract=ANCHOR,
        ),
        policy=policy,
        production=False,
    )
    decision = ready_decision(guard)
    guard.observe(
        Observation(
            subject_id="finalize-case",
            session_id="session-finalize-b",
            kind=ObservationKind.DISPUTE_OPENED,
            source_id="demo_fixture:trusted-dispute-feed",
            facts={"target": TARGET, "dispute_id": "late-disp", "status": "open"},
            evidence_mode=EvidenceMode.DEMO_FIXTURE,
            idempotency_key="late-dispute-0001",
        )
    )

    with pytest.raises(FinalizationError, match="memory changed"):
        guard.finalize(decision.decision_id)


def test_ready_draft_cannot_finalize_after_policy_changes(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    first_guard = MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=policy,
        production=False,
    )
    decision = ready_decision(first_guard)
    changed_policy = {**policy, "policy_id": "memoryguard-v2"}
    changed_guard = MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=changed_policy,
        production=False,
    )
    with pytest.raises(FinalizationError, match="policy changed"):
        changed_guard.finalize(decision.decision_id)


def test_local_finalization_is_stable_when_inspected_again(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=policy,
        production=False,
    )
    guard.observe(
        Observation(
            subject_id="stable-proof-case",
            session_id="stable-session-a",
            kind=ObservationKind.TARGET_REVOKED,
            source_id="demo_fixture:trusted-feed",
            facts={"target": TARGET, "reason_code": "user_revoked"},
            evidence_mode=EvidenceMode.DEMO_FIXTURE,
            idempotency_key="stable-proof-revoke",
        )
    )
    decision = guard.decide(
        PaymentIntent(
            subject_id="stable-proof-case",
            session_id="stable-session-b",
            chain_id=84532,
            target=TARGET,
            method="payInvoice",
            amount_usd=75,
            idempotency_key="stable-proof-decision",
            evidence_mode=EvidenceMode.DEMO_FIXTURE,
        )
    )
    first = guard.finalize(decision.decision_id)
    second = guard.inspect_finalization(decision.decision_id)
    assert first == second
    assert second.state.value == "local_finalized"

    attacker_result = guard.finalize(decision.decision_id, "0x" + "a" * 64)
    after_attack = guard.inspect_finalization(decision.decision_id)
    assert attacker_result == first
    assert after_attack == first
