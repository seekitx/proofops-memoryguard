from __future__ import annotations

from typing import Any

from .canonical import ZERO_HASH, domain_hash
from .errors import MemoryIntegrityError
from .models import DecisionDraft, PaymentIntent, StoredObservation, SubjectMemory


def observation_hash_payload(item: StoredObservation) -> dict[str, Any]:
    return {
        "observation_id": item.observation_id,
        "subject_ref": item.subject_ref,
        "session_id": item.session_id,
        "kind": item.kind.value,
        "source_id": item.source_id,
        "evidence_mode": item.evidence_mode.value,
        "status": item.status.value,
        "accepted_facts": item.accepted_facts,
        "quarantined_fields": list(item.quarantined_fields),
        "reason_codes": list(item.reason_codes),
        "raw_text_hash": item.raw_text_hash,
        "idempotency_key": item.idempotency_key,
        "observed_at": item.observed_at.isoformat(),
        "previous_hash": item.previous_hash,
    }


def compute_observation_hash(item: StoredObservation) -> str:
    return domain_hash("observation", observation_hash_payload(item))


def validate_subject(subject: SubjectMemory) -> None:
    if subject.version != len(subject.observations):
        raise MemoryIntegrityError("memory version does not match observation count")
    previous = ZERO_HASH
    for item in subject.observations:
        if item.subject_ref != subject.subject_ref:
            raise MemoryIntegrityError("cross-subject observation detected")
        if item.previous_hash != previous:
            raise MemoryIntegrityError("observation hash chain is broken")
        expected = compute_observation_hash(item)
        if item.observation_hash != expected:
            raise MemoryIntegrityError("observation content hash mismatch")
        previous = expected
    if subject.memory_root != previous:
        raise MemoryIntegrityError("subject memory root mismatch")


def intent_hash_payload(intent: PaymentIntent) -> dict[str, Any]:
    """Return only action identity fields, excluding session/request metadata."""
    return {
        "subject_ref": intent.subject_id,
        "chain_id": intent.chain_id,
        "target": intent.target.lower(),
        "method": intent.method,
        "amount_usd": intent.amount_usd,
        "evidence_mode": intent.evidence_mode.value,
    }


def compute_intent_hash(intent: PaymentIntent) -> str:
    return domain_hash("intent", intent_hash_payload(intent))


def decision_proof_payload(decision: DecisionDraft) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "subject_ref": decision.subject_ref,
        "session_id": decision.session_id,
        "verdict": decision.verdict.value,
        "reason_codes": list(decision.reason_codes),
        "causal_memory_ids": list(decision.causal_memory_ids),
        "cross_session": decision.cross_session,
        "memory_version": decision.memory_version,
        "memory_root": decision.memory_root,
        "policy_hash": decision.policy_hash,
        "intent_hash": decision.intent_hash,
        "nonce": decision.nonce,
        "created_at": decision.created_at.isoformat(),
        "expires_at": decision.expires_at.isoformat(),
    }


def compute_decision_proof_root(decision: DecisionDraft) -> str:
    return domain_hash("decision-proof", decision_proof_payload(decision))


def validate_decision(decision: DecisionDraft) -> None:
    if decision.intent.subject_id != decision.subject_ref:
        raise MemoryIntegrityError("decision intent subject does not match subject reference")
    if decision.intent.session_id != decision.session_id:
        raise MemoryIntegrityError("decision intent session does not match decision session")
    if compute_intent_hash(decision.intent) != decision.intent_hash:
        raise MemoryIntegrityError("decision intent hash mismatch")
    if compute_decision_proof_root(decision) != decision.proof_root:
        raise MemoryIntegrityError("decision proof root mismatch")
