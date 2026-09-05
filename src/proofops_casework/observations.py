"""Strict adapter return envelope. An adapter never owns case/expiry/authority fields."""
import re
from .core import CaseworkError
from .json_boundary import strict_json
import json


def bounded_observation(value):
    required = {"facts", "payload_sha256", "provenance", "external_calls", "claim_boundary"}
    if not isinstance(value, dict) or set(value) != required:
        raise CaseworkError("SOURCE_ENVELOPE_INVALID", 502)
    if (not isinstance(value["facts"], dict) or len(value["facts"]) > 64
            or not isinstance(value["payload_sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", value["payload_sha256"])
            or type(value["external_calls"]) is not int or not 1 <= value["external_calls"] <= 32
            or not isinstance(value["provenance"], str) or len(value["provenance"]) > 96
            or not isinstance(value["claim_boundary"], str) or len(value["claim_boundary"]) > 1000):
        raise CaseworkError("SOURCE_ENVELOPE_INVALID", 502)
    try:
        # Detach a bounded JSON value so a mutable adapter result cannot change
        # the observation after validation, during a concurrent completion.
        return strict_json(json.dumps(value, ensure_ascii=False, allow_nan=False), max_bytes=64_000)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CaseworkError("SOURCE_ENVELOPE_INVALID", 502) from exc
