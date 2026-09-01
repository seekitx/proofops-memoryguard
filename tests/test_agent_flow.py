from __future__ import annotations

import pytest

from proofops_memoryguard.adapters import (
    DeterministicModelAdapter,
    DisabledAnchorAdapter,
    InMemoryMemoryAdapter,
    InMemoryRunLedgerAdapter,
    InMemorySafetyActionAdapter,
)
from proofops_memoryguard.agent import MemoryGuardAgent
from proofops_memoryguard.agent_models import (
    AgentHumanSignal,
    AgentState,
    GuardedPaymentGoal,
    ModelPlan,
)
from proofops_memoryguard.errors import MemoryConflictError
from proofops_memoryguard.models import (
    AnchorPlan,
    AnchorState,
    AnchorVerification,
    EvidenceMode,
    Observation,
    ObservationKind,
    PaymentIntent,
)
from proofops_memoryguard.module import MemoryGuard

TARGET = "0x3333333333333333333333333333333333333333"


class AdversarialModel:
    production_kind = "adversarial_test_model"

    def health(self) -> dict[str, object]:
        return {"available": True, "backend": self.production_kind}

    def plan(self, *, context: dict[str, object], allowed_tools: tuple[str, ...]) -> ModelPlan:
        del context, allowed_tools
        return ModelPlan(
            explanation="Ignore the verdict and pay now.",
            operator_steps=("Send payment",),
            requested_tools=("payment_execution", "causal_evidence_brief.prepare"),
        )


class FailingModel:
    production_kind = "failing_test_model"

    def health(self) -> dict[str, object]:
        return {"available": False, "backend": self.production_kind}

    def plan(self, *, context: dict[str, object], allowed_tools: tuple[str, ...]) -> ModelPlan:
        del context, allowed_tools
        raise TimeoutError("model timeout fixture")


class VerifiedAnchor:
    def plan(self, decision):  # type: ignore[no-untyped-def]
        return AnchorPlan(
            chain_id=84532,
            network="base-sepolia-test",
            contract="0x4444444444444444444444444444444444444444",
            to="0x4444444444444444444444444444444444444444",
            data="0x1234",
            value="0x0",
            proof_root=decision.proof_root,
        )

    def verify(self, decision, tx_hash):  # type: ignore[no-untyped-def]
        return AnchorVerification(
            state=AnchorState.VERIFIED,
            tx_hash=tx_hash,
            chain_id=84532,
            contract="0x4444444444444444444444444444444444444444",
            block_number=42,
            reason_codes=("verified_anchor_fixture",),
        )


def make_guard(memory: InMemoryMemoryAdapter, policy: dict[str, object]) -> MemoryGuard:
    return MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=policy,
        production=False,
    )


def make_agent(
    guard: MemoryGuard,
    ledger: InMemoryRunLedgerAdapter,
    *,
    runtime: str,
    model: object | None = None,
) -> MemoryGuardAgent:
    return MemoryGuardAgent(
        guard=guard,
        model=model or DeterministicModelAdapter(),  # type: ignore[arg-type]
        ledger=ledger,
        actions=InMemorySafetyActionAdapter(),
        runtime_instance_id=runtime,
        production=False,
    )


def goal(session: str, key: str, amount: float = 4200) -> GuardedPaymentGoal:
    return GuardedPaymentGoal(
        intent=PaymentIntent(
            subject_id="agent-judge-case",
            session_id=session,
            chain_id=84532,
            target=TARGET,
            method="payInvoice",
            amount_usd=amount,
            idempotency_key=key,
            evidence_mode=EvidenceMode.DEMO_FIXTURE,
        )
    )


def observe(
    guard: MemoryGuard,
    kind: ObservationKind,
    session: str,
    facts: dict[str, object],
    key: str,
) -> str:
    receipt = guard.observe(
        Observation(
            subject_id="agent-judge-case",
            session_id=session,
            kind=kind,
            source_id="demo_fixture:trusted-agent-feed",
            facts=facts,
            evidence_mode=EvidenceMode.DEMO_FIXTURE,
            idempotency_key=key,
        )
    )
    return receipt.observation_id


def test_fresh_agent_changes_real_tool_path_from_review_to_escalation(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    ledger = InMemoryRunLedgerAdapter()
    guard_a = make_guard(memory, policy)
    observe(
        guard_a,
        ObservationKind.BASELINE_APPROVED,
        "session-agent-a",
        {
            "chain_id": 84532,
            "target": TARGET,
            "method": "payInvoice",
            "max_amount_usd": 5000,
        },
        "agent-baseline-0001",
    )
    run_a = make_agent(guard_a, ledger, runtime="runtime-a").run(
        goal("session-agent-a", "agent-run-a-0001")
    )
    dispute_id = observe(
        guard_a,
        ObservationKind.DISPUTE_OPENED,
        "session-agent-a",
        {"target": TARGET, "dispute_id": "disp-agent-1", "status": "open"},
        "agent-dispute-0001",
    )

    guard_b = make_guard(memory, policy)
    run_b = make_agent(guard_b, ledger, runtime="runtime-b").run(
        goal("session-agent-b", "agent-run-b-0001")
    )

    assert run_a.state == AgentState.AWAIT_FINALIZE
    assert "human_review.prepare" in run_a.artifacts
    assert "operator_escalation.create" not in run_a.artifacts
    assert run_b.state == AgentState.BLOCK_AND_ESCALATE
    assert "human_review.prepare" not in run_b.artifacts
    assert "operator_escalation.create" in run_b.artifacts
    assert run_a.action_fingerprint == run_b.action_fingerprint
    assert run_a.runtime_instance_id != run_b.runtime_instance_id
    assert run_b.decision.causal_memory_ids == (dispute_id,)
    assert run_b.decision.cross_session is True
    assert run_a.executable is False and run_b.executable is False


def test_unknown_payment_tool_is_recorded_and_suppressed(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = make_guard(memory, policy)
    ledger = InMemoryRunLedgerAdapter()
    observe(
        guard,
        ObservationKind.BASELINE_APPROVED,
        "session-adversarial",
        {
            "chain_id": 84532,
            "target": TARGET,
            "method": "payInvoice",
            "max_amount_usd": 5000,
        },
        "agent-adversarial-baseline",
    )
    run = make_agent(
        guard,
        ledger,
        runtime="runtime-adversarial",
        model=AdversarialModel(),
    ).run(goal("session-adversarial", "agent-adversarial-run"))

    suppressed = [
        event
        for event in run.tool_trace
        if event.tool == "payment_execution" and event.phase.value == "suppressed"
    ]
    assert len(suppressed) == 1
    assert suppressed[0].reason_code == "tool_not_registered"
    assert "human_review.prepare" in run.artifacts
    assert "causal_evidence_brief.prepare" in run.artifacts
    assert run.model_requested_safe_tools == ("causal_evidence_brief.prepare",)
    assert "Send payment" not in str(run.to_dict())
    assert "Ignore the verdict" not in str(run.to_dict())
    assert run.executable is False


def test_model_failure_is_explicit_safe_only_and_skips_optional_tool(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = make_guard(memory, policy)
    observe(
        guard,
        ObservationKind.BASELINE_APPROVED,
        "session-model-failure",
        {
            "chain_id": 84532,
            "target": TARGET,
            "method": "payInvoice",
            "max_amount_usd": 5000,
        },
        "agent-model-failure-baseline",
    )
    run = make_agent(
        guard,
        InMemoryRunLedgerAdapter(),
        runtime="runtime-model-failure",
        model=FailingModel(),
    ).run(goal("session-model-failure", "agent-model-failure-run"))

    assert run.state == AgentState.DEGRADED_SAFE_ONLY
    assert run.planning_degraded is True
    assert run.model_requested_safe_tools == ()
    assert "human_review.prepare" in run.artifacts
    assert "causal_evidence_brief.prepare" not in run.artifacts
    assert run.executable is False


def test_deny_proof_anchor_stays_blocked_after_agent_prepare_and_verify(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = MemoryGuard(
        memory=memory,
        anchor=VerifiedAnchor(),
        policy=policy,
        production=False,
    )
    observe(
        guard,
        ObservationKind.TARGET_REVOKED,
        "session-deny-anchor-a",
        {"target": TARGET, "reason_code": "trusted_revocation"},
        "agent-deny-anchor-revoked",
    )
    agent = make_agent(
        guard,
        InMemoryRunLedgerAdapter(),
        runtime="runtime-deny-anchor",
    )
    run = agent.run(goal("session-deny-anchor-b", "agent-deny-anchor-run"))
    prepared = agent.resume(run.run_id, AgentHumanSignal(kind="prepare_anchor"))
    verified = agent.resume(
        run.run_id,
        AgentHumanSignal(
            kind="anchor_transaction_observed",
            confirmation_tx_hash="0x" + "a" * 64,
        ),
    )

    assert run.state == AgentState.BLOCK_AND_ESCALATE
    assert prepared.state == AgentState.BLOCK_AND_ESCALATE
    assert prepared.anchor_state == AnchorState.CONFIRMATION_REQUIRED
    assert verified.state == AgentState.BLOCK_AND_ESCALATE
    assert verified.anchor_state == AnchorState.VERIFIED
    assert verified.executable is False


def test_agent_request_idempotency_replays_same_run_and_rejects_changed_body(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    guard = make_guard(memory, policy)
    agent = make_agent(guard, InMemoryRunLedgerAdapter(), runtime="runtime-idempotent")
    request = goal("session-idempotent", "agent-same-key")
    first = agent.run(request)
    assert agent.run(request) == first
    with pytest.raises(MemoryConflictError, match="different request"):
        agent.run(goal("session-idempotent", "agent-same-key", amount=4300))


def test_production_rejects_test_model_and_ledger(
    memory: InMemoryMemoryAdapter, policy: dict[str, object]
) -> None:
    with pytest.raises(ValueError, match="real remote model"):
        MemoryGuardAgent(
            guard=make_guard(memory, policy),
            model=DeterministicModelAdapter(),
            ledger=InMemoryRunLedgerAdapter(),
            actions=InMemorySafetyActionAdapter(),
            runtime_instance_id="runtime-production-check",
            production=True,
        )
