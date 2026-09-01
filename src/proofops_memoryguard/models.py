from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class EvidenceMode(str, Enum):
    DEMO_FIXTURE = "demo_fixture"
    CALLER_SUPPLIED = "caller_supplied"
    IDENTITY_VERIFIED = "identity_verified"
    BASE_TESTNET = "base_testnet"
    BASE_MAINNET = "base_mainnet"


class ObservationKind(str, Enum):
    BASELINE_APPROVED = "baseline_approved"
    DISPUTE_OPENED = "dispute_opened"
    TARGET_REVOKED = "target_revoked"
    VENDOR_NOTE = "vendor_note"


class ObservationStatus(str, Enum):
    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"
    QUARANTINED = "quarantined"
    REVIEW_REQUIRED = "review_required"


class Verdict(str, Enum):
    READY = "ready"
    DENY = "deny"
    NEEDS_HUMAN = "needs_human"
    MEMORY_UNAVAILABLE = "memory_unavailable"


class AnchorState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    LOCAL_FINALIZED = "local_finalized"
    CONFIRMATION_REQUIRED = "confirmation_required"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass(frozen=True)
class Observation:
    subject_id: str
    session_id: str
    kind: ObservationKind
    source_id: str
    facts: dict[str, Any] = field(default_factory=dict)
    raw_text: str | None = None
    evidence_mode: EvidenceMode = EvidenceMode.DEMO_FIXTURE
    idempotency_key: str = ""
    observed_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class StoredObservation:
    observation_id: str
    subject_ref: str
    session_id: str
    kind: ObservationKind
    source_id: str
    evidence_mode: EvidenceMode
    status: ObservationStatus
    accepted_facts: dict[str, Any]
    quarantined_fields: tuple[str, ...]
    reason_codes: tuple[str, ...]
    raw_text_hash: str | None
    idempotency_key: str
    observed_at: datetime
    previous_hash: str
    observation_hash: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "kind": self.kind.value,
                "evidence_mode": self.evidence_mode.value,
                "status": self.status.value,
                "quarantined_fields": list(self.quarantined_fields),
                "reason_codes": list(self.reason_codes),
                "observed_at": self.observed_at.isoformat(),
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredObservation:
        return cls(
            observation_id=str(data["observation_id"]),
            subject_ref=str(data["subject_ref"]),
            session_id=str(data["session_id"]),
            kind=ObservationKind(str(data["kind"])),
            source_id=str(data["source_id"]),
            evidence_mode=EvidenceMode(str(data["evidence_mode"])),
            status=ObservationStatus(str(data["status"])),
            accepted_facts=dict(data.get("accepted_facts", {})),
            quarantined_fields=tuple(data.get("quarantined_fields", ())),
            reason_codes=tuple(data.get("reason_codes", ())),
            raw_text_hash=(str(data["raw_text_hash"]) if data.get("raw_text_hash") else None),
            idempotency_key=str(data["idempotency_key"]),
            observed_at=_parse_time(data["observed_at"]),
            previous_hash=str(data["previous_hash"]),
            observation_hash=str(data["observation_hash"]),
        )


@dataclass(frozen=True)
class SubjectMemory:
    subject_ref: str
    version: int
    memory_root: str
    observations: tuple[StoredObservation, ...]
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "subject_ref": self.subject_ref,
            "version": self.version,
            "memory_root": self.memory_root,
            "observations": [item.to_dict() for item in self.observations],
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def empty(cls, subject_ref: str) -> SubjectMemory:
        return cls(subject_ref, 0, "0" * 64, (), utc_now())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubjectMemory:
        return cls(
            subject_ref=str(data["subject_ref"]),
            version=int(data["version"]),
            memory_root=str(data["memory_root"]),
            observations=tuple(
                StoredObservation.from_dict(dict(item))
                for item in data.get("observations", ())
            ),
            updated_at=_parse_time(data["updated_at"]),
        )


@dataclass(frozen=True)
class ObservationReceipt:
    observation_id: str
    status: ObservationStatus
    accepted_fields: tuple[str, ...]
    quarantined_fields: tuple[str, ...]
    reason_codes: tuple[str, ...]
    memory_version: int
    memory_root: str
    evidence_mode: EvidenceMode
    observed_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "status": self.status.value,
            "accepted_fields": list(self.accepted_fields),
            "quarantined_fields": list(self.quarantined_fields),
            "reason_codes": list(self.reason_codes),
            "evidence_mode": self.evidence_mode.value,
            "observed_at": self.observed_at.isoformat(),
        }


@dataclass(frozen=True)
class PaymentIntent:
    subject_id: str
    session_id: str
    chain_id: int
    target: str
    method: str
    amount_usd: float
    idempotency_key: str
    evidence_mode: EvidenceMode = EvidenceMode.DEMO_FIXTURE
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_mode"] = self.evidence_mode.value
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass(frozen=True)
class DecisionDraft:
    decision_id: str
    subject_ref: str
    session_id: str
    verdict: Verdict
    reason_codes: tuple[str, ...]
    causal_memory_ids: tuple[str, ...]
    cross_session: bool
    memory_version: int
    memory_root: str
    policy_hash: str
    intent: PaymentIntent
    intent_hash: str
    proof_root: str
    nonce: str
    created_at: datetime
    expires_at: datetime
    anchor_state: AnchorState = AnchorState.NOT_CONFIGURED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "decision_id": self.decision_id,
            "subject_ref": self.subject_ref,
            "session_id": self.session_id,
            "verdict": self.verdict.value,
            "reason_codes": list(self.reason_codes),
            "causal_memory_ids": list(self.causal_memory_ids),
            "cross_session": self.cross_session,
            "memory_version": self.memory_version,
            "memory_root": self.memory_root,
            "policy_hash": self.policy_hash,
            "intent": self.intent.to_dict(),
            "intent_hash": self.intent_hash,
            "proof_root": self.proof_root,
            "nonce": self.nonce,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "anchor_state": self.anchor_state.value,
            "executable": False,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionDraft:
        intent_data = dict(data["intent"])
        intent = PaymentIntent(
            subject_id=str(intent_data.get("subject_id", data["subject_ref"])),
            session_id=str(intent_data["session_id"]),
            chain_id=int(intent_data["chain_id"]),
            target=str(intent_data["target"]),
            method=str(intent_data["method"]),
            amount_usd=float(intent_data["amount_usd"]),
            idempotency_key=str(intent_data["idempotency_key"]),
            evidence_mode=EvidenceMode(str(intent_data["evidence_mode"])),
            created_at=_parse_time(intent_data["created_at"]),
        )
        return cls(
            decision_id=str(data["decision_id"]),
            subject_ref=str(data["subject_ref"]),
            session_id=str(data["session_id"]),
            verdict=Verdict(str(data["verdict"])),
            reason_codes=tuple(data.get("reason_codes", ())),
            causal_memory_ids=tuple(data.get("causal_memory_ids", ())),
            cross_session=bool(data["cross_session"]),
            memory_version=int(data["memory_version"]),
            memory_root=str(data["memory_root"]),
            policy_hash=str(data["policy_hash"]),
            intent=intent,
            intent_hash=str(data["intent_hash"]),
            proof_root=str(data["proof_root"]),
            nonce=str(data["nonce"]),
            created_at=_parse_time(data["created_at"]),
            expires_at=_parse_time(data["expires_at"]),
            anchor_state=AnchorState(str(data.get("anchor_state", "not_configured"))),
        )


@dataclass(frozen=True)
class AnchorPlan:
    chain_id: int
    network: str
    contract: str
    to: str
    data: str
    value: str
    proof_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnchorPlan:
        return cls(
            chain_id=int(data["chain_id"]),
            network=str(data["network"]),
            contract=str(data["contract"]),
            to=str(data["to"]),
            data=str(data["data"]),
            value=str(data["value"]),
            proof_root=str(data["proof_root"]),
        )


@dataclass(frozen=True)
class AnchorVerification:
    state: AnchorState
    tx_hash: str | None
    chain_id: int | None
    contract: str | None
    block_number: int | None
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnchorVerification:
        return cls(
            state=AnchorState(str(data["state"])),
            tx_hash=str(data["tx_hash"]) if data.get("tx_hash") else None,
            chain_id=int(data["chain_id"]) if data.get("chain_id") is not None else None,
            contract=str(data["contract"]) if data.get("contract") else None,
            block_number=(
                int(data["block_number"]) if data.get("block_number") is not None else None
            ),
            reason_codes=tuple(data.get("reason_codes", ())),
        )


@dataclass(frozen=True)
class FinalizationResult:
    decision_id: str
    verdict: Verdict
    state: AnchorState
    proof_root: str
    executable: bool
    anchor_plan: AnchorPlan | None = None
    anchor_verification: AnchorVerification | None = None
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "verdict": self.verdict.value,
            "state": self.state.value,
            "proof_root": self.proof_root,
            "executable": self.executable,
            "anchor_plan": self.anchor_plan.to_dict() if self.anchor_plan else None,
            "anchor_verification": (
                self.anchor_verification.to_dict() if self.anchor_verification else None
            ),
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinalizationResult:
        plan_data = data.get("anchor_plan")
        verification_data = data.get("anchor_verification")
        return cls(
            decision_id=str(data["decision_id"]),
            verdict=Verdict(str(data["verdict"])),
            state=AnchorState(str(data["state"])),
            proof_root=str(data["proof_root"]),
            executable=bool(data["executable"]),
            anchor_plan=(AnchorPlan.from_dict(dict(plan_data)) if plan_data else None),
            anchor_verification=(
                AnchorVerification.from_dict(dict(verification_data))
                if verification_data
                else None
            ),
            reason_codes=tuple(data.get("reason_codes", ())),
        )
