from __future__ import annotations

from typing import Any, Protocol

from .models import (
    AnchorPlan,
    AnchorVerification,
    DecisionDraft,
    FinalizationResult,
    StoredObservation,
    SubjectMemory,
)


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
