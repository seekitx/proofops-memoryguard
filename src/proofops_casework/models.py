from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,95}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Minor = Annotated[int, Field(strict=True, gt=0, le=100_000_000)]
Revision = Annotated[int, Field(strict=True, ge=0)]
Verdict = Literal["READY", "DENY", "NEEDS_HUMAN"]
Role = Literal["owner", "investigator", "reviewer", "viewer"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Actor(StrictModel):
    """Constructed ONLY from the server credential registry, never a request body."""
    actor_id: Identifier
    tenant_id: Identifier
    role: Role
    subjects: list[Identifier]


class Scope(StrictModel):
    subject_id: Identifier
    chain_id: Literal[8453, 84532] = 84532
    target: Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]
    method: Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")]

    @field_validator("target")
    @classmethod
    def normalize_target(cls, value: str) -> str:
        return value.lower()


class Intent(StrictModel):
    scope: Scope
    amount_minor: Minor
    currency: Literal["USD"] = "USD"  # valuation cents, NOT token or onchain units


class Command(StrictModel):
    idempotency_key: Identifier
    session_id: Identifier
    expected_revision: Revision


class BaselineCommand(Command):
    scope: Scope
    limit_minor: Minor
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        return value.astimezone(timezone.utc)


class TaskCommand(Command):
    intent: Intent
    depends_on: list[Identifier] = Field(default_factory=list, max_length=64)


class OpenCaseCommand(Command):
    scope: Scope
    kind: Literal["dispute", "revocation"]
    evidence_digest: Digest


class ReopenCommand(Command):
    evidence_digest: Digest


class HandoffCommand(Command):
    report_id: Identifier
    reviewer_id: Identifier


class ResolveCommand(Command):
    handoff_id: Identifier
    resolution: Literal["resolved", "false_positive_verified", "remediation_verified"]
    evidence_digest: Digest


class NoteCommand(Command):
    scope: Scope
    text: Annotated[str, Field(min_length=1, max_length=10_000)]


class Baseline(StrictModel):
    scope: Scope
    version: int
    limit_minor: Minor
    expires_at: datetime
    actor_id: Identifier
    event_seq: int


class RiskCase(StrictModel):
    case_id: Identifier
    scope: Scope
    kind: Literal["dispute", "revocation"]
    version: int = 1
    status: Literal["OPEN", "RESOLVED"] = "OPEN"
    opened_by: Identifier
    opened_seq: int
    evidence_digest: Digest
    resolution: str | None = None
    resolved_by: Identifier | None = None
    resolved_seq: int | None = None


class Task(StrictModel):
    task_id: Identifier
    intent: Intent
    depends_on: list[Identifier] = Field(default_factory=list)
    taints: dict[str, str] = Field(default_factory=dict)
    status: Literal["READY", "DENY", "NEEDS_HUMAN", "SUSPENDED"] = "NEEDS_HUMAN"
    current_decision_id: Identifier | None = None


class Decision(StrictModel):
    decision_id: Identifier
    task_id: Identifier
    verdict: Verdict
    reason_codes: list[str]
    causal_refs: list[str]
    active_blockers: list[Identifier]
    action_fingerprint: Digest
    basis_hash: Digest
    memory_revision: int
    session_id: Identifier
    runtime_id: Identifier
    process_id: int
    build_commit: str
    created_at: datetime
    expires_at: datetime
    tool: Literal["human_review.prepare", "operator_escalation.create"]
    proof_root: str = ""
    executable: Literal[False] = False


class Report(StrictModel):
    report_id: Identifier
    case_id: Identifier
    case_version: int
    investigator_id: Identifier
    basis_hash: Digest
    case_refs: list[Identifier]
    affected_tasks: list[Identifier]
    precedent_ids: list[Identifier]
    trace: list[dict]
    model_receipt: dict | None = None
    planner_status: Literal["DETERMINISTIC", "REMOTE", "DEGRADED"]
    raw_text_received_by_model: Literal[False] = False
    authoritative: Literal[False] = False
    report_root: str = ""


class Handoff(StrictModel):
    handoff_id: Identifier
    report_id: Identifier
    case_id: Identifier
    case_version: int
    reviewer_id: Identifier
    investigator_id: Identifier
    accepted: bool = False


class Workspace(StrictModel):
    schema_version: Literal["memoryguard-casework/2"] = "memoryguard-casework/2"
    tenant_id: Identifier
    revision: int = 0
    baselines: dict[str, Baseline] = Field(default_factory=dict)
    cases: dict[str, RiskCase] = Field(default_factory=dict)
    case_history: dict[str, list[RiskCase]] = Field(default_factory=dict)
    baseline_history: dict[str, list[Baseline]] = Field(default_factory=dict)
    tasks: dict[str, Task] = Field(default_factory=dict)
    decisions: dict[str, Decision] = Field(default_factory=dict)
    reports: dict[str, Report] = Field(default_factory=dict)
    handoffs: dict[str, Handoff] = Field(default_factory=dict)
    lessons: dict[str, dict] = Field(default_factory=dict)
    artifacts: dict[str, dict] = Field(default_factory=dict)
    audit: list[dict] = Field(default_factory=list)
    idempotency: dict[str, dict] = Field(default_factory=dict)
    state_root: str = ""


class BootstrapCommand(Command):
    confirmation: Literal["CREATE_CASEWORK_WORKSPACE"]


class AnchorCommand(Command):
    decision_id: Identifier


class VerifyAnchorCommand(Command):
    tx_hash: Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{64}$")]
