"""Bounded HTTP, no redirects/proxy inheritance and no automatic status retries."""
from __future__ import annotations

import json
import time
import httpx
from ..core import CaseworkError


class BoundedHTTP:
    def __init__(self, *, transport=None, max_bytes=512_000, timeout=12.0):
        self.transport = transport
        self.max_bytes = max_bytes
        self.timeout = timeout

    def json(self, method: str, url: str, *, headers=None, payload=None):
        try:
            deadline = time.monotonic() + self.timeout
            with httpx.Client(transport=self.transport, timeout=httpx.Timeout(self.timeout),
                              follow_redirects=False, trust_env=False) as client:
                with client.stream(method, url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        raise CaseworkError("SOURCE_HTTP_FAILURE", 502)
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        if time.monotonic() > deadline:
                            raise CaseworkError("SOURCE_RESPONSE_DEADLINE", 504)
                        raw.extend(chunk)
                        if len(raw) > self.max_bytes:
                            raise CaseworkError("SOURCE_RESPONSE_TOO_LARGE", 502)
                    data = json.loads(raw)
                    if not isinstance(data, dict):
                        raise CaseworkError("SOURCE_SCHEMA_INVALID", 502)
                    return data, bytes(raw)
        except CaseworkError:
            raise
        except Exception as exc:
            # Never expose URL query credentials, request headers, or upstream prose.
            raise CaseworkError("SOURCE_TRANSPORT_UNAVAILABLE", 502) from exc
