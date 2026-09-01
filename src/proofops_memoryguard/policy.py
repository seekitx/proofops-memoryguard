from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .models import (
    EvidenceMode,
    Observation,
    ObservationKind,
    ObservationStatus,
    PaymentIntent,
    StoredObservation,
    Verdict,
)

_INSTRUCTION_PATTERNS = {
    "ignore_previous_rules": re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|safety)"),
    "authority_override": re.compile(r"(?i)(override|bypass|disable).{0,24}(policy|rule|guard)"),
    "payment_instruction": re.compile(r"(?i)(pay|transfer|send).{0,24}(now|immediately|funds|money)"),
    "prompt_boundary_attack": re.compile(r"(?i)(system prompt|developer message|act as|tool call)"),
    "secret_request": re.compile(r"(?i)(private key|api key|access token|cookie|password)"),
}

_EVM_ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")
_MACHINE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_METHOD = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_REVOCATION_REASONS = {
    "user_revoked",
    "security_incident",
    "compliance_hold",
    "manual_block",
}

_ALLOWED_FIELDS: dict[ObservationKind, frozenset[str]] = {
    ObservationKind.BASELINE_APPROVED: frozenset(
        {"chain_id", "target", "method", "max_amount_usd", "expires_at"}
    ),
    ObservationKind.DISPUTE_OPENED: frozenset({"target", "dispute_id", "status"}),
    ObservationKind.TARGET_REVOKED: frozenset({"target", "reason_code"}),
    ObservationKind.VENDOR_NOTE: frozenset(),
}

_TRUSTED_MODES = {
    EvidenceMode.DEMO_FIXTURE,
    EvidenceMode.IDENTITY_VERIFIED,
    EvidenceMode.BASE_TESTNET,
    EvidenceMode.BASE_MAINNET,
}


@dataclass(frozen=True)
class ObservationClassification:
    status: ObservationStatus
    accepted_facts: dict[str, Any]
    quarantined_fields: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDecision:
    verdict: Verdict
    reason_codes: tuple[str, ...]
    causal_memory_ids: tuple[str, ...]


def _validate_fact(
    kind: ObservationKind, key: str, value: Any
) -> tuple[bool, Any, str | None]:
    if key == "target":
        if isinstance(value, str) and _EVM_ADDRESS.fullmatch(value):
            return True, value.lower(), None
        return False, None, "invalid_target"
    if key == "chain_id":
        if isinstance(value, int) and not isinstance(value, bool) and value in {8453, 84532}:
            return True, value, None
        return False, None, "invalid_chain_id"
    if key == "method":
        if isinstance(value, str) and _METHOD.fullmatch(value):
            return True, value, None
        return False, None, "invalid_method"
    if key == "max_amount_usd":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, None, "invalid_max_amount"
        amount = float(value)
        if not math.isfinite(amount) or amount <= 0 or amount > 1_000_000:
            return False, None, "invalid_max_amount"
        return True, amount, None
    if key == "expires_at":
        if not isinstance(value, str):
            return False, None, "invalid_expiry"
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False, None, "invalid_expiry"
        if parsed.tzinfo is None:
            return False, None, "invalid_expiry"
        return True, parsed.astimezone(UTC).isoformat(), None
    if key == "status":
        if kind == ObservationKind.DISPUTE_OPENED and value == "open":
            return True, "open", None
        return False, None, "invalid_dispute_status"
    if key == "dispute_id":
        if isinstance(value, str) and _MACHINE_ID.fullmatch(value):
            return True, value, None
        return False, None, "invalid_dispute_id"
    if key == "reason_code":
        if isinstance(value, str) and value in _REVOCATION_REASONS:
            return True, value, None
        return False, None, "invalid_reason_code"
    return False, None, "unknown_fact_field"


def classify_observation(observation: Observation) -> ObservationClassification:
    allowed = _ALLOWED_FIELDS[observation.kind]
    accepted: dict[str, Any] = {}
    quarantined: list[str] = []
    reasons: list[str] = []

    for key, value in observation.facts.items():
        if key in allowed:
            valid, normalized, reason = _validate_fact(observation.kind, key, value)
            if valid:
                accepted[key] = normalized
            else:
                quarantined.append(key)
                reasons.append(reason or "invalid_fact_value")
        else:
            quarantined.append(key)
            reasons.append("unknown_fact_field")

    if observation.raw_text:
        quarantined.append("raw_text")
        matched = [code for code, pattern in _INSTRUCTION_PATTERNS.items() if pattern.search(observation.raw_text)]
        reasons.extend(matched or ["untrusted_free_text"])

    if observation.evidence_mode not in _TRUSTED_MODES and accepted:
        quarantined.extend(accepted)
        accepted = {}
        reasons.append("source_not_identity_verified")

    if observation.kind == ObservationKind.VENDOR_NOTE:
        accepted = {}
        if "raw_text" not in quarantined:
            quarantined.append("raw_text")
        reasons.append("vendor_text_never_authoritative")

    if accepted and quarantined:
        status = ObservationStatus.PARTIALLY_ACCEPTED
    elif accepted:
        status = ObservationStatus.ACCEPTED
    elif observation.evidence_mode == EvidenceMode.CALLER_SUPPLIED and observation.facts:
        status = ObservationStatus.REVIEW_REQUIRED
    else:
        status = ObservationStatus.QUARANTINED

    return ObservationClassification(
        status=status,
        accepted_facts=accepted,
        quarantined_fields=tuple(sorted(set(quarantined))),
        reason_codes=tuple(sorted(set(reasons or ["structured_fact_accepted"]))),
    )


def _active_for_mode(item: StoredObservation, mode: EvidenceMode) -> bool:
    if item.status not in {ObservationStatus.ACCEPTED, ObservationStatus.PARTIALLY_ACCEPTED}:
        return False
    if mode == EvidenceMode.DEMO_FIXTURE:
        return item.evidence_mode in _TRUSTED_MODES
    return item.evidence_mode in {
        EvidenceMode.IDENTITY_VERIFIED,
        EvidenceMode.BASE_TESTNET,
        EvidenceMode.BASE_MAINNET,
    }


def decide(intent: PaymentIntent, observations: tuple[StoredObservation, ...]) -> PolicyDecision:
    active = [item for item in observations if _active_for_mode(item, intent.evidence_mode)]
    target = intent.target.lower()

    revocations = [
        item
        for item in active
        if item.kind == ObservationKind.TARGET_REVOKED
        and str(item.accepted_facts.get("target", "")).lower() == target
    ]
    if revocations:
        return PolicyDecision(
            Verdict.DENY,
            ("target_revoked_in_persistent_memory",),
            tuple(item.observation_id for item in revocations),
        )

    disputes = [
        item
        for item in active
        if item.kind == ObservationKind.DISPUTE_OPENED
        and str(item.accepted_facts.get("target", "")).lower() == target
        and str(item.accepted_facts.get("status", "open")).lower() != "resolved"
    ]
    if disputes:
        return PolicyDecision(
            Verdict.DENY,
            ("open_dispute_recalled_from_persistent_memory",),
            tuple(item.observation_id for item in disputes),
        )

    baselines = [
        item
        for item in active
        if item.kind == ObservationKind.BASELINE_APPROVED
        and str(item.accepted_facts.get("target", "")).lower() == target
        and item.accepted_facts.get("chain_id") == intent.chain_id
        and item.accepted_facts.get("method") == intent.method
    ]
    valid_baselines: list[StoredObservation] = []
    for item in baselines:
        limit = float(item.accepted_facts.get("max_amount_usd", 0))
        expires = item.accepted_facts.get("expires_at")
        if expires:
            parsed = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)) <= datetime.now(UTC):
                continue
        if intent.amount_usd <= limit:
            valid_baselines.append(item)
    if valid_baselines:
        return PolicyDecision(
            Verdict.READY,
            ("trusted_baseline_recalled", "human_confirmation_still_required"),
            tuple(item.observation_id for item in valid_baselines[-1:]),
        )

    return PolicyDecision(
        Verdict.NEEDS_HUMAN,
        ("no_authoritative_memory_for_target",),
        (),
    )
