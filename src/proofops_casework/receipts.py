"""Bind a model receipt to the exact bounded plan request (not provider attestation)."""
from datetime import datetime
import re
from typing import Any

_HEX = re.compile(r"^[0-9a-f]{64}$")


def expected_model_context_hash(context: dict, tools: tuple[str, ...]) -> str:
    # Shared implementation must match the existing HttpModelAdapter exactly.
    from proofops_memoryguard.canonical import domain_hash
    return domain_hash("agent-model-context", {"context": context, "allowed_tools": list(tools)})


def bound_receipt(candidate: Any, context: dict, tools: tuple[str, ...]) -> dict:
    if not isinstance(candidate, dict):
        raise ValueError("model receipt missing")
    strings = ("generation_id", "resolved_model", "configured_model", "completed_at")
    if any(not isinstance(candidate.get(k), str) or not 1 <= len(candidate[k]) <= 256
           for k in strings):
        raise ValueError("model receipt fields invalid")
    if (candidate.get("backend") != "remote_structured_model"
            or candidate.get("live_call_verified") is not True
            or candidate.get("structured_output_validated") is not True
            or not isinstance(candidate.get("completion_sha256"), str)
            or not _HEX.fullmatch(candidate["completion_sha256"])
            or candidate.get("model_context_hash") != expected_model_context_hash(context, tools)):
        raise ValueError("model receipt does not bind the current request")
    completed = datetime.fromisoformat(candidate["completed_at"].replace("Z", "+00:00"))
    if completed.tzinfo is None or completed.utcoffset() is None:
        raise ValueError("model receipt timestamp lacks timezone")
    keys = set(strings) | {"backend", "completion_sha256", "model_context_hash",
                           "live_call_verified", "structured_output_validated"}
    return {key: candidate[key] for key in sorted(keys)}
