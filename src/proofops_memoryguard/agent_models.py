from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .models import AnchorState, DecisionDraft, PaymentIntent, Verdict, _parse_time, utc_now


class AgentState(str, Enum):
    AWAIT_FINALIZE = "await_finalize"
    BLOCK_AND_ESCALATE = "block_and_escalate"
    AWAIT_HUMAN_REVIEW = "await_human_review"
    HALT_MEMORY_UNAVAILABLE = "halt_memory_unavailable"
    BLOCK_AND_REDECIDE = "block_and_redecide"
    HALT_ACTION_UNAVAILABLE = "halt_action_unavailable"
    DEGRADED_SAFE_ONLY = "degraded_safe_only"
    CANCELLED = "cancelled"
    ANCHOR_VERIFIED = "anchor_verified"


class ToolPhase(str, Enum):
    CONSIDERED = "considered"
    CALLED = "called"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True)
class GuardedPaymentGoal:
    intent: PaymentIntent


@dataclass(frozen=True)
class ModelPlan:
    explanation: str
    operator_steps: tuple[str, ...]
    requested_tools: tuple[str, ...]


@dataclass(frozen=True)
class ToolEvent:
    sequence: int
    tool: str
    phase: ToolPhase
    reason_code: str
    input_hash: str
    output_hash: str | None = None
    occurred_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "phase": self.phase.value,
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolEvent:
        return cls(
            sequence=int(data["sequence"]),
            tool=str(data["tool"]),
            phase=ToolPhase(str(data["phase"])),
            reason_code=str(data["reason_code"]),
            input_hash=str(data["input_hash"]),
            output_hash=str(data["output_hash"]) if data.get("output_hash") else None,
            occurred_at=_parse_time(data["occurred_at"]),
        )


@dataclass(frozen=True)
class AgentRun:
    run_id: str
    request_hash: str
    runtime_instance_id: str
    state: AgentState
    decision: DecisionDraft
    action_fingerprint: str
    explanation: str
    operator_steps: tuple[str, ...]
    planning_degraded: bool
    model_kind: str
    model_requested_safe_tools: tuple[str, ...]
    tool_trace: tuple[ToolEvent, ...]
    artifacts: dict[str, Any]
    anchor_state: AnchorState
    executable: bool = False
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def verdict(self) -> Verdict:
        return self.decision.verdict

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "request_hash": self.request_hash,
            "runtime_instance_id": self.runtime_instance_id,
            "state": self.state.value,
            "verdict": self.verdict.value,
            "decision": self.decision.to_dict(),
            "decision_id": self.decision.decision_id,
            "action_fingerprint": self.action_fingerprint,
            "cross_session": self.decision.cross_session,
            "causal_memory_ids": list(self.decision.causal_memory_ids),
            "explanation": self.explanation,
            "explanation_source": "deterministic_authoritative_copy",
            "raw_model_output_persisted": False,
            "operator_steps": list(self.operator_steps),
            "planning_degraded": self.planning_degraded,
            "model_kind": self.model_kind,
            "model_requested_safe_tools": list(self.model_requested_safe_tools),
            "tool_trace": [event.to_dict() for event in self.tool_trace],
            "artifacts": self.artifacts,
            "proof_root": self.decision.proof_root,
            "anchor_state": self.anchor_state.value,
            "executable": self.executable,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentRun:
        return cls(
            run_id=str(data["run_id"]),
            request_hash=str(data["request_hash"]),
            runtime_instance_id=str(data["runtime_instance_id"]),
            state=AgentState(str(data["state"])),
            decision=DecisionDraft.from_dict(dict(data["decision"])),
            action_fingerprint=str(data["action_fingerprint"]),
            explanation=str(data["explanation"]),
            operator_steps=tuple(str(item) for item in data.get("operator_steps", ())),
            planning_degraded=bool(data.get("planning_degraded", False)),
            model_kind=str(data["model_kind"]),
            model_requested_safe_tools=tuple(
                str(item) for item in data.get("model_requested_safe_tools", ())
            ),
            tool_trace=tuple(
                ToolEvent.from_dict(dict(item)) for item in data.get("tool_trace", ())
            ),
            artifacts=dict(data.get("artifacts", {})),
            anchor_state=AnchorState(str(data.get("anchor_state", "not_configured"))),
            executable=bool(data["executable"]),
            created_at=_parse_time(data["created_at"]),
            updated_at=_parse_time(data["updated_at"]),
        )


@dataclass(frozen=True)
class AgentHumanSignal:
    kind: str
    confirmation_tx_hash: str | None = None
