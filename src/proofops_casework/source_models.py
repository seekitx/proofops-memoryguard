"""Server-owned source policy; request bodies never determine provenance authority."""
from __future__ import annotations

import json
import re
from pathlib import Path
import stat
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from .core import CaseworkError
from .models import Command, Digest, Identifier, Scope, StrictModel

PositiveInt = Annotated[int, Field(strict=True, ge=1)]


def _validate_cli_home_path(raw_home: str, *, require_exists: bool = False) -> Path:
    """Check the filesystem boundary used by the read-only ACP CLI.

    Config validation runs before an operator may have mounted the isolated
    home, so a missing path is allowed there.  The runner calls this same
    helper with ``require_exists=True`` immediately before spawning the CLI.
    Every existing component is checked with ``lstat``: a symlink, a
    non-directory, or group/other write permission is never an acceptable
    home or parent directory.
    """
    try:
        home = Path(raw_home)
        if (not home.is_absolute() or home == Path(home.anchor)
                or any(part in {".", ".."} for part in home.parts)):
            raise ValueError("invalid ACP CLI home path")
        current = Path(home.anchor)
        for part in home.parts[1:]:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                if require_exists:
                    raise ValueError("ACP CLI home does not exist")
                break
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ValueError("ACP CLI home contains an unsafe component")
            if info.st_mode & 0o022:
                raise ValueError("ACP CLI home is group/world writable")
            if current == home and info.st_mode & 0o077:
                raise ValueError("ACP CLI home is not operator-only")
        return home
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("ACP CLI home"):
            raise
        raise ValueError("invalid ACP CLI home path") from exc


class SourceSpec(StrictModel):
    source_id: Identifier
    kind: Literal["github_issue", "base_transaction"]
    tenant_id: Identifier
    subjects: list[Identifier] = Field(min_length=1, max_length=32)
    # Two sources operated by one organization do not become independent witnesses.
    independence_group: Identifier
    repositories: list[str] = Field(default_factory=list, max_length=32)
    token_env: str | None = None
    rpc_url: str | None = None
    chain_id: Literal[8453, 84532] = 84532
    ttl_seconds: Annotated[int, Field(strict=True, ge=15, le=86400)] = 300
    min_confirmations: Annotated[int, Field(strict=True, ge=1, le=100)] = 3
    max_attempts_per_case: Annotated[int, Field(strict=True, ge=1, le=100)] = 20

    @model_validator(mode="after")
    def validate_config(self):
        if self.token_env is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]{2,95}", self.token_env):
            raise ValueError("token_env must name a server environment variable")
        if self.kind == "github_issue":
            if not self.repositories or self.rpc_url is not None:
                raise ValueError("GitHub source needs an explicit repository allowlist")
            for repo in self.repositories:
                if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repo) or repo.split("/")[1] in {".", ".."}:
                    raise ValueError("invalid repository")
            object.__setattr__(self, "repositories", sorted(set(repo.lower() for repo in self.repositories)))
        else:
            if not self.rpc_url:
                raise ValueError("Base source needs an operator-owned HTTPS RPC URL")
            parsed = urlsplit(self.rpc_url)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.fragment or parsed.hostname in {"localhost", "localhost.localdomain"}):
                raise ValueError("invalid RPC URL")
            # The config file is trusted operator input, not an HTTP request field.
            import ipaddress
            try:
                address = ipaddress.ip_address(parsed.hostname)
            except ValueError:
                address = None
            if address and not address.is_global:
                raise ValueError("private RPC IP is forbidden")
        return self


class ScopeEvidencePolicy(StrictModel):
    tenant_id: Identifier
    scope: Scope
    required_sources: list[Identifier] = Field(min_length=1, max_length=8)
    min_independence_groups: Annotated[int, Field(strict=True, ge=1, le=8)] = 1
    # Evidence is necessary for a resolution, never sufficient to authorize it.
    require_for_resolution: Literal[True] = True


class IncidentSpec(StrictModel):
    source_id: Identifier
    actor_id: Identifier
    secret_env: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,95}$")]
    scope: Scope
    max_clock_skew_seconds: Annotated[int, Field(strict=True, ge=15, le=600)] = 120


class VirtualsSpec(StrictModel):
    tenant_id: Identifier
    subjects: list[Identifier] = Field(min_length=1, max_length=32)
    chain_id: Literal[8453, 84532] = 84532
    client_address: Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]
    provider_address: Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]
    offering_name: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.-]{1,95}$")]
    # USDC micro-units, not USD valuation cents. Only an operator funds the job.
    max_budget_micros: Annotated[int, Field(strict=True, ge=1, le=10_000_000)] = 100_000
    cli_executable: str
    cli_sha256: Digest
    cli_home: str
    ttl_seconds: Annotated[int, Field(strict=True, ge=60, le=86400)] = 3600

    @model_validator(mode="after")
    def paths_and_identity(self):
        if not Path(self.cli_executable).is_absolute() or not Path(self.cli_home).is_absolute():
            raise ValueError("ACP executable and isolated HOME must be absolute")
        # Reject an already unsafe configured path early.  The runner repeats
        # the lstat checks immediately before spawning to cover a mount or
        # permission change after startup; missing paths remain a runtime
        # configuration error rather than a reason to break test doubles.
        _validate_cli_home_path(self.cli_home)
        if self.client_address.lower() == self.provider_address.lower():
            raise ValueError("ACP client and provider must differ")
        return self


class ConnectorConfig(StrictModel):
    schema_version: Literal["casework-connectors/1"] = "casework-connectors/1"
    sources: list[SourceSpec] = Field(default_factory=list, max_length=32)
    policies: list[ScopeEvidencePolicy] = Field(default_factory=list, max_length=32)
    incidents: list[IncidentSpec] = Field(default_factory=list, max_length=16)
    virtuals: VirtualsSpec | None = None

    @model_validator(mode="after")
    def cross_references(self):
        ids = [s.source_id for s in self.sources]
        if len(set(ids)) != len(ids) or len({x.source_id for x in self.incidents}) != len(self.incidents):
            raise ValueError("duplicate source IDs")
        lookup = {s.source_id: s for s in self.sources}
        seen = set()
        for policy in self.policies:
            key = (policy.tenant_id, policy.scope.model_dump_json())
            if key in seen or len(set(policy.required_sources)) != len(policy.required_sources):
                raise ValueError("duplicate policy/source entry")
            seen.add(key)
            selected = [lookup.get(key) for key in policy.required_sources]
            if any(s is None or s.tenant_id != policy.tenant_id or
                   policy.scope.subject_id not in s.subjects for s in selected):
                raise ValueError("policy references a missing or incorrectly scoped source")
            if len({s.independence_group for s in selected}) < policy.min_independence_groups:
                raise ValueError("declared source groups cannot satisfy policy")
        return self

    @classmethod
    def from_file(cls, path: Path):
        from .json_boundary import read_json_file
        value, _ = read_json_file(path, max_bytes=128_000)
        return cls.model_validate(value)


class CollectCommand(Command):
    source_id: Identifier
    resource: Annotated[str, Field(min_length=1, max_length=240)]
    force_refresh: Annotated[bool, Field(strict=True)] = False


class SourceQuery(StrictModel):
    source_id: Identifier
    resource: Annotated[str, Field(min_length=1, max_length=240)]


class MissionCommand(Command):
    queries: list[SourceQuery] = Field(min_length=1, max_length=4)
    reviewer_id: Identifier | None = None


class ReviewJobCommand(Command):
    job_id: Annotated[str, Field(pattern=r"^[1-9][0-9]{0,29}$")]


class IncidentBody(StrictModel):
    kind: Literal["dispute", "revocation"]
    evidence_digest: Digest
    # Incoming note is deliberately not accepted or persisted.
