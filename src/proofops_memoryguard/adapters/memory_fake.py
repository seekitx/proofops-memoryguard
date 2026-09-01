from __future__ import annotations

import copy
from threading import RLock
from typing import Any

from ..errors import MemoryConflictError
from ..models import DecisionDraft, FinalizationResult, StoredObservation, SubjectMemory


class InMemoryMemoryAdapter:
    """Test-only Memory Adapter. Production wiring must reject this Adapter."""

    production_kind = "test_only_in_memory"

    def __init__(self) -> None:
        self._subjects: dict[str, SubjectMemory] = {}
        self._decisions: dict[str, DecisionDraft] = {}
        self._finalizations: dict[str, FinalizationResult] = {}
        self._lock = RLock()

    def health(self) -> dict[str, Any]:
        return {
            "available": True,
            "backend": self.production_kind,
            "production_eligible": False,
        }

    def load_subject(self, subject_ref: str) -> SubjectMemory | None:
        with self._lock:
            return copy.deepcopy(self._subjects.get(subject_ref))

    def commit_observation(
        self,
        *,
        previous_version: int,
        subject: SubjectMemory,
        observation: StoredObservation,
    ) -> None:
        del observation
        with self._lock:
            current = self._subjects.get(subject.subject_ref)
            actual_version = current.version if current else 0
            if actual_version != previous_version:
                raise MemoryConflictError("subject memory version changed")
            self._subjects[subject.subject_ref] = copy.deepcopy(subject)

    def save_decision(self, decision: DecisionDraft) -> None:
        with self._lock:
            self._decisions[decision.decision_id] = copy.deepcopy(decision)

    def load_decision(self, decision_id: str) -> DecisionDraft | None:
        with self._lock:
            return copy.deepcopy(self._decisions.get(decision_id))

    def save_finalization(self, result: FinalizationResult) -> None:
        with self._lock:
            self._finalizations[result.decision_id] = copy.deepcopy(result)

    def load_finalization(self, decision_id: str) -> FinalizationResult | None:
        with self._lock:
            return copy.deepcopy(self._finalizations.get(decision_id))
