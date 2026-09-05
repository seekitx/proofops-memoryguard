"""Pure receipt/bundle helpers. Artifacts live inside the existing sealed workspace."""
from __future__ import annotations

from datetime import datetime
import json
from .core import CaseworkError, digest


def source_key(case_id: str, source_id: str) -> str:
    return digest("source-head", [case_id, source_id])


def evidence_heads(state, case_id: str) -> dict:
    case = state.cases[case_id]
    result = {}
    for key, head in state.artifacts.items():
        if (head.get("kind") == "SOURCE_HEAD" and head.get("case_id") == case_id
                and head.get("case_version") == case.version):
            source_id = head.get("source_id")
            if source_id in result:
                # Two current heads for one source make the authoritative choice
                # ambiguous.  Do not let dict insertion order silently pick one.
                raise CaseworkError("SOURCE_CONFLICT", 503)
            result[source_id] = head
    return result


def evidence_basis(state, case_id: str) -> dict:
    # In-progress/failed fetches displace older snapshots; do not silently reuse a
    # last-good observation after a forced refresh failed or a resource was changed.
    return {key: {k: v for k, v in head.items() if k not in {"kind"}}
            for key, head in sorted(evidence_heads(state, case_id).items())}


def parsed_time(value: str) -> datetime:
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("time must be timezone-aware")
        return at
    except (ValueError, TypeError, AttributeError) as exc:
        raise CaseworkError("STORED_EVIDENCE_TIME_INVALID", 503) from exc


_VOLATILE_FACT_FIELDS = frozenset({"updated_at", "confirmations"})


def source_conflicts(receipts: list[dict]) -> list[dict]:
    """Return same-resource disagreements without exposing fact values.

    A source snapshot is provenance, not truth, but two current snapshots that
    disagree on a stable field must not be treated as complete evidence.  Fetch
    time and confirmation count are expected to move between observations and
    are therefore excluded.  The returned digests are only diagnostic bindings;
    callers must still stop the investigation/resolution path.
    """
    claims: dict[tuple[str, str], dict[str, list[str]]] = {}
    for receipt in receipts:
        resource = receipt.get("resource")
        facts = receipt.get("facts")
        source_id = receipt.get("source_id")
        if not isinstance(resource, str) or not isinstance(facts, dict):
            continue
        resource_key = resource.lower()
        for field, value in facts.items():
            if field in _VOLATILE_FACT_FIELDS:
                continue
            try:
                encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError):
                # A non-JSON fact cannot be a trusted comparable claim.  Hash
                # its representation and let the normal receipt binding gate
                # decide whether the source is usable.
                encoded = repr(value)
            claims.setdefault((resource_key, str(field)), {}).setdefault(encoded, []).append(source_id)
    conflicts = []
    for (resource, field), values in sorted(claims.items()):
        if len(values) <= 1:
            continue
        conflicts.append({
            "resource_digest": digest("source-conflict-resource", resource),
            "field": field,
            "source_ids": sorted({source_id for source_ids in values.values() for source_id in source_ids}),
            "value_digests": sorted(digest("source-conflict-value", value) for value in values),
            "reason": "SOURCE_CONFLICT",
        })
    return conflicts


def current_receipts(state, case_id: str, at: datetime, source_specs: dict) -> tuple[list, list]:
    accepted, rejected = [], []
    for source_id, head in sorted(evidence_heads(state, case_id).items()):
        receipt = state.artifacts.get(head.get("receipt_id", ""))
        spec = source_specs.get(source_id)
        reason = None
        if head.get("state") != "OBSERVED" or receipt is None:
            reason = "SOURCE_NOT_OBSERVED"
        elif (receipt.get("kind") != "SOURCE_RECEIPT" or receipt.get("case_id") != case_id
              or receipt.get("case_version") != state.cases[case_id].version
              or receipt.get("source_id") != source_id
              or receipt.get("receipt_id") != head.get("receipt_id")):
            reason = "SOURCE_RECEIPT_BINDING_INVALID"
        elif spec is None or receipt.get("source_spec_hash") != digest("source-spec", spec.model_dump(mode="json")):
            reason = "SOURCE_POLICY_CHANGED"
        elif receipt.get("expires_at") is None or parsed_time(receipt["expires_at"]) <= at:
            reason = "SOURCE_EXPIRED"
        elif receipt.get("receipt_root") != digest("source-receipt", {k:v for k,v in receipt.items() if k != "receipt_root"}):
            reason = "SOURCE_RECEIPT_CORRUPT"
        if reason:
            rejected.append({"source_id": source_id, "reason": reason})
        else:
            accepted.append(receipt)
    return accepted, rejected
