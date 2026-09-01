from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .models import EvidenceMode, Observation, ObservationKind, PaymentIntent
from .agent import MemoryGuardAgent
from .agent_models import AgentHumanSignal, GuardedPaymentGoal
from .module import MemoryGuard

EVM_ADDRESS_PATTERN = r"^0x[a-fA-F0-9]{40}$"
TX_HASH_PATTERN = r"^0x[a-fA-F0-9]{64}$"
PublicEvidenceMode = Literal["demo_fixture", "caller_supplied"]


class ObservationBody(BaseModel):
    subject_id: str = Field(min_length=3, max_length=200)
    session_id: str = Field(min_length=8, max_length=128)
    kind: ObservationKind
    source_id: str = Field(min_length=3, max_length=200)
    facts: dict[str, Any] = Field(default_factory=dict)
    raw_text: str | None = Field(default=None, max_length=10_000)
    evidence_mode: PublicEvidenceMode = "demo_fixture"
    idempotency_key: str = Field(min_length=8, max_length=128)
    observed_at: datetime | None = None


class DecisionBody(BaseModel):
    subject_id: str = Field(min_length=3, max_length=200)
    session_id: str = Field(min_length=8, max_length=128)
    chain_id: Literal[8453, 84532] = 84532
    target: str = Field(pattern=EVM_ADDRESS_PATTERN)
    method: str = Field(min_length=1, max_length=120)
    amount_usd: float = Field(gt=0, le=1_000_000)
    idempotency_key: str = Field(min_length=8, max_length=128)
    evidence_mode: PublicEvidenceMode = "demo_fixture"


class FinalizeBody(BaseModel):
    confirmation_tx_hash: str | None = Field(default=None, pattern=TX_HASH_PATTERN)


class AgentResumeBody(BaseModel):
    kind: Literal["cancel", "prepare_anchor", "anchor_transaction_observed"]
    confirmation_tx_hash: str | None = Field(default=None, pattern=TX_HASH_PATTERN)


def build_router(
    get_guard: Callable[[], MemoryGuard],
    get_agent: Callable[[], MemoryGuardAgent],
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["memoryguard"])

    @router.post("/observations")
    async def observe(body: ObservationBody) -> dict[str, Any]:
        guard = get_guard()
        observation = Observation(
            subject_id=body.subject_id,
            session_id=body.session_id,
            kind=body.kind,
            source_id=body.source_id,
            facts=body.facts,
            raw_text=body.raw_text,
            evidence_mode=EvidenceMode(body.evidence_mode),
            idempotency_key=body.idempotency_key,
            observed_at=body.observed_at or datetime.now().astimezone(),
        )
        return guard.observe(observation).to_dict()

    @router.post("/decisions")
    async def decide(body: DecisionBody) -> dict[str, Any]:
        guard = get_guard()
        intent = PaymentIntent(
            subject_id=body.subject_id,
            session_id=body.session_id,
            chain_id=body.chain_id,
            target=body.target,
            method=body.method,
            amount_usd=body.amount_usd,
            idempotency_key=body.idempotency_key,
            evidence_mode=EvidenceMode(body.evidence_mode),
        )
        return guard.decide(intent).to_dict()

    @router.post("/agent/runs")
    async def run_agent(body: DecisionBody) -> dict[str, Any]:
        intent = PaymentIntent(
            subject_id=body.subject_id,
            session_id=body.session_id,
            chain_id=body.chain_id,
            target=body.target,
            method=body.method,
            amount_usd=body.amount_usd,
            idempotency_key=body.idempotency_key,
            evidence_mode=EvidenceMode(body.evidence_mode),
        )
        return get_agent().run(GuardedPaymentGoal(intent=intent)).to_dict()

    @router.get("/agent/runs/{run_id}")
    async def inspect_agent(run_id: str) -> dict[str, Any]:
        return get_agent().inspect(run_id).to_dict()

    @router.post("/agent/runs/{run_id}/resume")
    async def resume_agent(run_id: str, body: AgentResumeBody) -> dict[str, Any]:
        signal = AgentHumanSignal(
            kind=body.kind,
            confirmation_tx_hash=body.confirmation_tx_hash,
        )
        return get_agent().resume(run_id, signal).to_dict()

    @router.post("/decisions/{decision_id}/finalize")
    async def finalize(decision_id: str, body: FinalizeBody) -> dict[str, Any]:
        guard = get_guard()
        return guard.finalize(decision_id, body.confirmation_tx_hash).to_dict()

    @router.get("/proofs/{decision_id}")
    async def proof(decision_id: str) -> dict[str, Any]:
        guard = get_guard()
        return guard.inspect_finalization(decision_id).to_dict()

    return router
