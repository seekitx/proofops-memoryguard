from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any

from .canonical import ZERO_HASH, domain_hash, subject_ref, text_hash
from .errors import (
    DecisionNotFoundError,
    FinalizationError,
    MemoryConflictError,
    MemoryIntegrityError,
)
from .models import (
    AnchorState,
    DecisionDraft,
    FinalizationResult,
    Observation,
    ObservationReceipt,
    ObservationStatus,
    PaymentIntent,
    StoredObservation,
    SubjectMemory,
    Verdict,
    utc_now,
)
from .policy import classify_observation, decide as policy_decide
from .ports import AnchorPort, MemoryPort
from .proof import (
    compute_decision_proof_root,
    compute_intent_hash,
    compute_observation_hash,
    validate_decision,
    validate_subject,
)

_EVM_ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")
_METHOD = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_MACHINE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class MemoryGuard:
    """Deep Module for observing, deciding, and finalizing memory-bound decisions."""

    def __init__(
        self,
        *,
        memory: MemoryPort,
        anchor: AnchorPort,
        policy: dict[str, Any],
        decision_ttl_seconds: int = 600,
        production: bool = False,
    ) -> None:
        if decision_ttl_seconds < 30 or decision_ttl_seconds > 3600:
            raise ValueError("decision_ttl_seconds must be in [30, 3600]")
        if production and memory.production_kind != "sibyl_memory":
            raise ValueError("production MemoryGuard requires the Sibyl Memory Adapter")
        self._memory = memory
        self._anchor = anchor
        self._policy = policy
        self._policy_hash = domain_hash("policy", policy)
        self._decision_ttl = decision_ttl_seconds
        self._lock = RLock()

    @property
    def backend_status(self) -> dict[str, Any]:
        return self._memory.health()

    @staticmethod
    def _validate_identifier(name: str, value: str, *, minimum: int = 3, maximum: int = 200) -> None:
        if not isinstance(value, str) or not (minimum <= len(value.strip()) <= maximum):
            raise ValueError(f"{name} length must be in [{minimum}, {maximum}]")
        if any(ord(char) < 32 for char in value):
            raise ValueError(f"{name} cannot contain control characters")

    @classmethod
    def _validate_machine_identifier(
        cls, name: str, value: str, *, minimum: int = 8, maximum: int = 128
    ) -> None:
        cls._validate_identifier(name, value, minimum=minimum, maximum=maximum)
        if not _MACHINE_IDENTIFIER.fullmatch(value):
            raise ValueError(f"{name} must be a stable machine identifier")

    def observe(self, observation: Observation) -> ObservationReceipt:
        self._validate_identifier("subject_id", observation.subject_id)
        self._validate_machine_identifier("session_id", observation.session_id)
        self._validate_identifier("source_id", observation.source_id)
        self._validate_machine_identifier("idempotency_key", observation.idempotency_key)
        if observation.raw_text and len(observation.raw_text) > 10_000:
            raise ValueError("raw_text exceeds 10,000 characters")

        ref = subject_ref(observation.subject_id)
        with self._lock:
            current = self._memory.load_subject(ref) or SubjectMemory.empty(ref)
            validate_subject(current)
            classification = classify_observation(observation)
            duplicate = next(
                (
                    item
                    for item in current.observations
                    if item.idempotency_key == observation.idempotency_key
                ),
                None,
            )
            if duplicate:
                same_request = (
                    duplicate.kind == observation.kind
                    and duplicate.source_id == domain_hash("source", observation.source_id)
                    and duplicate.evidence_mode == observation.evidence_mode
                    and duplicate.accepted_facts == classification.accepted_facts
                    and duplicate.quarantined_fields == classification.quarantined_fields
                    and duplicate.reason_codes == classification.reason_codes
                    and duplicate.raw_text_hash
                    == (text_hash(observation.raw_text) if observation.raw_text else None)
                )
                if not same_request:
                    raise MemoryConflictError(
                        "idempotency key was already used for a different observation"
                    )
                return self._receipt(duplicate, current)

            previous_hash = current.memory_root if current.version else ZERO_HASH
            stored = StoredObservation(
                observation_id=f"obs_{uuid.uuid4().hex[:20]}",
                subject_ref=ref,
                session_id=observation.session_id,
                kind=observation.kind,
                source_id=domain_hash("source", observation.source_id),
                evidence_mode=observation.evidence_mode,
                status=classification.status,
                accepted_facts=classification.accepted_facts,
                quarantined_fields=classification.quarantined_fields,
                reason_codes=classification.reason_codes,
                raw_text_hash=text_hash(observation.raw_text) if observation.raw_text else None,
                idempotency_key=observation.idempotency_key,
                observed_at=observation.observed_at,
                previous_hash=previous_hash,
                observation_hash="",
            )
            stored = StoredObservation(
                **{**stored.__dict__, "observation_hash": compute_observation_hash(stored)}
            )
            updated = SubjectMemory(
                subject_ref=ref,
                version=current.version + 1,
                memory_root=stored.observation_hash,
                observations=(*current.observations, stored),
                updated_at=utc_now(),
            )
            validate_subject(updated)
            self._memory.commit_observation(
                previous_version=current.version,
                subject=updated,
                observation=stored,
            )
            return self._receipt(stored, updated)

    @staticmethod
    def _receipt(item: StoredObservation, subject: SubjectMemory) -> ObservationReceipt:
        return ObservationReceipt(
            observation_id=item.observation_id,
            status=item.status,
            accepted_fields=tuple(sorted(item.accepted_facts)),
            quarantined_fields=item.quarantined_fields,
            reason_codes=item.reason_codes,
            memory_version=subject.version,
            memory_root=subject.memory_root,
            evidence_mode=item.evidence_mode,
            observed_at=item.observed_at,
        )

    def decide(self, intent: PaymentIntent) -> DecisionDraft:
        self._validate_identifier("subject_id", intent.subject_id)
        self._validate_machine_identifier("session_id", intent.session_id)
        self._validate_machine_identifier("idempotency_key", intent.idempotency_key)
        self._validate_identifier("method", intent.method, minimum=1, maximum=120)
        if not _METHOD.fullmatch(intent.method):
            raise ValueError("method must be a stable machine identifier")
        if intent.chain_id not in {8453, 84532}:
            raise ValueError("MemoryGuard contest flow only supports Base chain 8453 or 84532")
        if not _EVM_ADDRESS.fullmatch(intent.target):
            raise ValueError("target must be a 20-byte EVM address")
        if intent.amount_usd <= 0 or intent.amount_usd > 1_000_000:
            raise ValueError("amount_usd must be in (0, 1,000,000]")

        ref = subject_ref(intent.subject_id)
        with self._lock:
            subject = self._memory.load_subject(ref)
            if subject is None:
                subject = SubjectMemory.empty(ref)
            validate_subject(subject)
            policy_result = policy_decide(intent, subject.observations)

            safe_intent = PaymentIntent(
                subject_id=ref,
                session_id=intent.session_id,
                chain_id=intent.chain_id,
                target=intent.target.lower(),
                method=intent.method,
                amount_usd=intent.amount_usd,
                idempotency_key=intent.idempotency_key,
                evidence_mode=intent.evidence_mode,
                created_at=intent.created_at,
            )
            intent_hash = compute_intent_hash(safe_intent)
            created_at = utc_now()
            decision = DecisionDraft(
                decision_id=f"dec_{uuid.uuid4().hex[:20]}",
                subject_ref=ref,
                session_id=intent.session_id,
                verdict=policy_result.verdict,
                reason_codes=policy_result.reason_codes,
                causal_memory_ids=policy_result.causal_memory_ids,
                cross_session=any(
                    item.session_id != intent.session_id
                    for item in subject.observations
                    if item.observation_id in policy_result.causal_memory_ids
                ),
                memory_version=subject.version,
                memory_root=subject.memory_root,
                policy_hash=self._policy_hash,
                intent=safe_intent,
                intent_hash=intent_hash,
                proof_root="",
                nonce=uuid.uuid4().hex,
                created_at=created_at,
                expires_at=created_at + timedelta(seconds=self._decision_ttl),
                anchor_state=AnchorState.NOT_CONFIGURED,
            )
            decision = DecisionDraft(
                **{**decision.__dict__, "proof_root": compute_decision_proof_root(decision)}
            )
            validate_decision(decision)
            self._memory.save_decision(decision)
            return decision

    def finalize(
        self, decision_id: str, confirmation_tx_hash: str | None = None
    ) -> FinalizationResult:
        self._validate_machine_identifier("decision_id", decision_id)
        with self._lock:
            decision = self._memory.load_decision(decision_id)
            if decision is None:
                raise DecisionNotFoundError("decision was not found")
            validate_decision(decision)
            if datetime.now(UTC) >= decision.expires_at:
                raise FinalizationError("decision draft expired; decide again")
            if decision.policy_hash != self._policy_hash:
                raise FinalizationError("decision policy changed; decide again before finalization")

            if decision.verdict == Verdict.READY:
                current_subject = self._memory.load_subject(decision.subject_ref)
                if current_subject is None:
                    raise FinalizationError("decision subject memory is no longer available")
                validate_subject(current_subject)
                if (
                    current_subject.version != decision.memory_version
                    or current_subject.memory_root != decision.memory_root
                ):
                    raise FinalizationError(
                        "subject memory changed after READY draft; decide again before finalization"
                    )

            existing = self._memory.load_finalization(decision_id)
            if existing is not None:
                if (
                    existing.decision_id != decision.decision_id
                    or existing.verdict != decision.verdict
                    or existing.proof_root != decision.proof_root
                ):
                    raise MemoryIntegrityError("stored finalization does not match decision proof")
                if existing.state in {
                    AnchorState.VERIFIED,
                    AnchorState.LOCAL_FINALIZED,
                    AnchorState.FAILED,
                }:
                    existing_tx = (
                        existing.anchor_verification.tx_hash
                        if existing.anchor_verification
                        else None
                    )
                    if (
                        existing.state == AnchorState.VERIFIED
                        and confirmation_tx_hash
                        and confirmation_tx_hash != existing_tx
                    ):
                        raise FinalizationError(
                            "decision is already verified with a different transaction"
                        )
                    return existing
                if (
                    existing.state == AnchorState.PENDING
                    and confirmation_tx_hash
                    and existing.anchor_verification
                    and confirmation_tx_hash != existing.anchor_verification.tx_hash
                ):
                    raise FinalizationError(
                        "pending finalization is bound to a different transaction"
                    )
                if not confirmation_tx_hash:
                    return existing

            if confirmation_tx_hash:
                verification = self._anchor.verify(decision, confirmation_tx_hash)
                executable = (
                    decision.verdict == Verdict.READY
                    and verification.state == AnchorState.VERIFIED
                )
                reasons = list(verification.reason_codes)
                if executable:
                    reasons.append("execution_adapter_not_implemented")
                    executable = False
                result = FinalizationResult(
                    decision_id=decision.decision_id,
                    verdict=decision.verdict,
                    state=verification.state,
                    proof_root=decision.proof_root,
                    executable=executable,
                    anchor_verification=verification,
                    reason_codes=tuple(reasons),
                )
                if verification.state in {AnchorState.PENDING, AnchorState.VERIFIED}:
                    self._memory.save_finalization(result)
                return result

            plan = self._anchor.plan(decision)
            if plan is not None:
                result = FinalizationResult(
                    decision_id=decision.decision_id,
                    verdict=decision.verdict,
                    state=AnchorState.CONFIRMATION_REQUIRED,
                    proof_root=decision.proof_root,
                    executable=False,
                    anchor_plan=plan,
                    reason_codes=("user_wallet_confirmation_required",),
                )
            elif decision.verdict == Verdict.READY:
                result = FinalizationResult(
                    decision_id=decision.decision_id,
                    verdict=decision.verdict,
                    state=AnchorState.FAILED,
                    proof_root=decision.proof_root,
                    executable=False,
                    reason_codes=("base_anchor_required_before_ready_can_finalize",),
                )
            else:
                result = FinalizationResult(
                    decision_id=decision.decision_id,
                    verdict=decision.verdict,
                    state=AnchorState.LOCAL_FINALIZED,
                    proof_root=decision.proof_root,
                    executable=False,
                    reason_codes=("deny_or_review_finalized_locally", "base_anchor_not_configured"),
                )
            self._memory.save_finalization(result)
            return result

    def inspect_finalization(self, decision_id: str) -> FinalizationResult:
        """Read a finalized proof without creating or changing finalization state."""
        self._validate_machine_identifier("decision_id", decision_id)
        with self._lock:
            decision = self._memory.load_decision(decision_id)
            if decision is None:
                raise DecisionNotFoundError("decision was not found")
            validate_decision(decision)
            result = self._memory.load_finalization(decision_id)
            if result is None:
                raise DecisionNotFoundError("decision has not been finalized")
            if (
                result.decision_id != decision.decision_id
                or result.verdict != decision.verdict
                or result.proof_root != decision.proof_root
            ):
                raise MemoryIntegrityError("stored finalization does not match decision proof")
            return result
