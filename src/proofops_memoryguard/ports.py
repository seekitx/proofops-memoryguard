from __future__ import annotations

from typing import Any, ContextManager, Protocol

from .models import (
    AnchorPlan,
    AnchorVerification,
    DecisionDraft,
    FinalizationResult,
    StoredObservation,
    SubjectMemory,
)
from .agent_models import AgentRun, ModelPlan


class MemoryPort(Protocol):
    @property
    def production_kind(self) -> str: ...

    def health(self) -> dict[str, Any]: ...

    def load_subject(self, subject_ref: str) -> SubjectMemory | None: ...

    def commit_observation(
        self,
        *,
        previous_version: int,
        subject: SubjectMemory,
        observation: StoredObservation,
    ) -> None: ...

    def save_decision(self, decision: DecisionDraft) -> None: ...

    def load_decision(self, decision_id: str) -> DecisionDraft | None: ...

    def save_finalization(self, result: FinalizationResult) -> None: ...

    def load_finalization(self, decision_id: str) -> FinalizationResult | None: ...


class AnchorPort(Protocol):
    def plan(self, decision: DecisionDraft) -> AnchorPlan | None: ...

    def verify(self, decision: DecisionDraft, tx_hash: str) -> AnchorVerification: ...


class ModelPort(Protocol):
    @property
    def production_kind(self) -> str: ...

    def health(self) -> dict[str, Any]: ...

    def plan(self, *, context: dict[str, Any], allowed_tools: tuple[str, ...]) -> ModelPlan: ...


class RunLedgerPort(Protocol):
    @property
    def production_kind(self) -> str: ...

    def health(self) -> dict[str, Any]: ...

    def claim(self, run_id: str) -> ContextManager[None]: ...

    def save(self, run: AgentRun) -> None: ...

    def load(self, run_id: str) -> AgentRun | None: ...


class SafetyActionPort(Protocol):
    @property
    def production_kind(self) -> str: ...

    def health(self) -> dict[str, Any]: ...

    def prepare_review(self, decision: DecisionDraft) -> dict[str, Any]: ...

    def create_escalation(self, decision: DecisionDraft) -> dict[str, Any]: ...

    def prepare_evidence_brief(self, decision: DecisionDraft) -> dict[str, Any]: ...
