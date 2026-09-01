from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime
from enum import Enum
from typing import Any

DOMAIN = "proofops-memoryguard/v1"
ZERO_HASH = "0" * 64

_SENSITIVE_KEY_PARTS = {
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "privatekey",
    "private_key",
    "password",
    "secret",
    "sessiontoken",
    "session_token",
    "accesstoken",
    "access_token",
    "apikey",
    "api_key",
}
_BEARER = re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{8,}")
_PRIVATE_KEY = re.compile(r"(?i)0x[a-f0-9]{64}")


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not canonical")
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return _normalize(value.to_dict())
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    raise TypeError(f"unsupported canonical type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def domain_hash(domain: str, value: Any) -> str:
    prefix = f"{DOMAIN}:{domain}\0".encode()
    return hashlib.sha256(prefix + canonical_json(value).encode()).hexdigest()


def text_hash(value: str) -> str:
    return domain_hash("external-text", unicodedata.normalize("NFC", value))


def subject_ref(subject_id: str) -> str:
    return domain_hash("subject", subject_id.strip().lower())


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            compact = str(key).lower().replace("-", "").replace(" ", "")
            if any(part.replace("_", "") in compact for part in _SENSITIVE_KEY_PARTS):
                result[str(key)] = "<redacted>"
            else:
                result[str(key)] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _PRIVATE_KEY.sub("<redacted-private-key>", _BEARER.sub("<redacted-bearer>", value))
    return value
