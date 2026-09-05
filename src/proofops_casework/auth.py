from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from pathlib import Path

from .core import CaseworkError
from .models import Actor


class TokenRegistry:
    """Small deployment-controlled RBAC registry, not an identity-provider service."""

    def __init__(self, records: list[dict]):
        self.actors: dict[str, Actor] = {}
        self.entries: list[tuple[str, Actor]] = []
        seen: set[str] = set()
        for row in records:
            if set(row) != {"token_sha256", "principal"}:
                raise ValueError("unexpected credential field")
            token_hash = row["token_sha256"]
            if not isinstance(token_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", token_hash):
                raise ValueError("credential digest must be SHA-256 hex")
            principal = Actor.model_validate(row["principal"])
            if token_hash in seen or principal.actor_id in self.actors:
                raise ValueError("duplicate token digest or actor ID")
            if not principal.subjects:
                raise ValueError("principal needs explicit allowed subjects")
            seen.add(token_hash)
            self.actors[principal.actor_id] = principal
            self.entries.append((token_hash, principal))
        if not self.entries:
            raise ValueError("empty credential registry")

    @classmethod
    def from_file(cls, path: Path) -> "TokenRegistry":
        stat = path.stat()
        if os.name == "posix" and stat.st_mode & 0o077:
            raise ValueError("credential registry permissions must be 0600 or stricter")
        if stat.st_size > 64_000:
            raise ValueError("credential registry too large")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"credentials"}:
            raise ValueError("invalid credential registry")
        return cls(data["credentials"])

    def authenticate(self, authorization: str | None) -> Actor:
        if not authorization or not authorization.startswith("Bearer "):
            raise CaseworkError("AUTHENTICATION_REQUIRED", 401)
        token = authorization[7:]
        if not 32 <= len(token) <= 512:
            raise CaseworkError("INVALID_CREDENTIAL", 401)
        candidate = hashlib.sha256(token.encode()).hexdigest()
        matched = None
        for expected, principal in self.entries:
            if secrets.compare_digest(candidate, expected):
                matched = principal
        if matched is None:
            raise CaseworkError("INVALID_CREDENTIAL", 401)
        return matched.model_copy(deep=True)
