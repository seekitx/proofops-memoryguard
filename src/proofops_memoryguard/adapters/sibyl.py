from __future__ import annotations

from pathlib import Path
from typing import Any

from ..canonical import domain_hash
from ..errors import MemoryBackendUnavailable, MemoryConflictError
from ..models import DecisionDraft, FinalizationResult, StoredObservation, SubjectMemory
from .sibyl_identity import EXPECTED_SIBYL_SCHEMA_VERSION, sibyl_sdk_identity


class UnavailableMemoryAdapter:
    production_kind = "sibyl_unavailable"

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def health(self) -> dict[str, Any]:
        return {
            "available": False,
            "backend": self.production_kind,
            "production_eligible": False,
            "reason": self._reason,
        }

    def _fail(self) -> None:
        raise MemoryBackendUnavailable(self._reason)

    def load_subject(self, subject_ref: str) -> SubjectMemory | None:
        del subject_ref
        self._fail()

    def commit_observation(
        self,
        *,
        previous_version: int,
        subject: SubjectMemory,
        observation: StoredObservation,
    ) -> None:
        del previous_version, subject, observation
        self._fail()

    def save_decision(self, decision: DecisionDraft) -> None:
        del decision
        self._fail()

    def load_decision(self, decision_id: str) -> DecisionDraft | None:
        del decision_id
        self._fail()

    def save_finalization(self, result: FinalizationResult) -> None:
        del result
        self._fail()

    def load_finalization(self, decision_id: str) -> FinalizationResult | None:
        del decision_id
        self._fail()


class SibylMemoryAdapter:
    """Production Memory Adapter backed only by the official Sibyl SDK."""

    production_kind = "sibyl_memory"
    _SUBJECT_CATEGORY = "memoryguard-subject"
    _DECISION_CATEGORY = "memoryguard-decision"
    _FINALIZATION_CATEGORY = "memoryguard-finalization"

    def __init__(self, *, path: Path, tenant_id: str, policy: dict[str, Any]) -> None:
        from sibyl_memory_client import MemoryClient, NotFoundError, SibylMemoryError

        self._client = MemoryClient.local(path, tenant_id=tenant_id)
        self._not_found_error = NotFoundError
        self._sibyl_error = SibylMemoryError
        self._policy = policy
        self._client.set_reference(
            "memoryguard-policy-v1",
            policy,
            metadata={
                "product": "proofops-memoryguard",
                "purpose": "deterministic decision policy; never model authority",
            },
        )

    @staticmethod
    def _key(value: str) -> str:
        return domain_hash("sibyl-key", value)

    def _translate(self, exc: Exception) -> MemoryBackendUnavailable:
        return MemoryBackendUnavailable(f"Sibyl Memory operation failed: {type(exc).__name__}")

    def health(self) -> dict[str, Any]:
        try:
            identity = sibyl_sdk_identity()
            schema_version = self._client.schema_version()
            schema_compatible = schema_version == EXPECTED_SIBYL_SCHEMA_VERSION
            return {
                "available": True,
                "backend": self.production_kind,
                "production_eligible": identity["sdk_identity_ready"] and schema_compatible,
                "schema_version": schema_version,
                "schema_version_expected": EXPECTED_SIBYL_SCHEMA_VERSION,
                "schema_compatible": schema_compatible,
                "tenant_isolated": True,
                **identity,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "available": False,
                "backend": self.production_kind,
                "production_eligible": False,
                "reason": type(exc).__name__,
            }

    def load_subject(self, subject_ref: str) -> SubjectMemory | None:
        try:
            row = self._client.get_entity(self._SUBJECT_CATEGORY, self._key(subject_ref))
            return SubjectMemory.from_dict(dict(row["body"]))
        except self._not_found_error:
            return None
        except self._sibyl_error as exc:
            raise self._translate(exc) from exc

    def commit_observation(
        self,
        *,
        previous_version: int,
        subject: SubjectMemory,
        observation: StoredObservation,
    ) -> None:
        try:
            current = self.load_subject(subject.subject_ref)
            actual_version = current.version if current else 0
            if actual_version != previous_version:
                raise MemoryConflictError("subject memory version changed before commit")

            safe_event = {
                "observation_id": observation.observation_id,
                "subject_ref": observation.subject_ref,
                "kind": observation.kind.value,
                "status": observation.status.value,
                "evidence_mode": observation.evidence_mode.value,
                "reason_codes": list(observation.reason_codes),
                "observation_hash": observation.observation_hash,
            }
            self._client.write_event(
                evaluated=["memoryguard_observation_validated"],
                forward=["commit_warm_subject_entity"],
                extra=safe_event,
            )
            self._client.set_entity(
                self._SUBJECT_CATEGORY,
                self._key(subject.subject_ref),
                subject.to_dict(),
                status="active",
            )
        except MemoryConflictError:
            raise
        except self._sibyl_error as exc:
            raise self._translate(exc) from exc

    def save_decision(self, decision: DecisionDraft) -> None:
        try:
            self._client.set_entity(
                self._DECISION_CATEGORY,
                self._key(decision.decision_id),
                decision.to_dict(),
                status="draft",
            )
            self._client.write_event(
                evaluated=["memoryguard_decision_drafted"],
                extra={
                    "decision_id": decision.decision_id,
                    "verdict": decision.verdict.value,
                    "proof_root": decision.proof_root,
                    "memory_version": decision.memory_version,
                },
            )
        except self._sibyl_error as exc:
            raise self._translate(exc) from exc

    def load_decision(self, decision_id: str) -> DecisionDraft | None:
        try:
            row = self._client.get_entity(self._DECISION_CATEGORY, self._key(decision_id))
            return DecisionDraft.from_dict(dict(row["body"]))
        except self._not_found_error:
            return None
        except self._sibyl_error as exc:
            raise self._translate(exc) from exc

    def save_finalization(self, result: FinalizationResult) -> None:
        try:
            self._client.write_event(
                evaluated=["memoryguard_finalization_validated"],
                forward=["commit_finalization_entity"],
                extra={
                    "decision_id": result.decision_id,
                    "verdict": result.verdict.value,
                    "proof_root": result.proof_root,
                    "anchor_state": result.state.value,
                    "executable": result.executable,
                },
            )
            self._client.set_entity(
                self._FINALIZATION_CATEGORY,
                self._key(result.decision_id),
                result.to_dict(),
                status=result.state.value,
            )
        except self._sibyl_error as exc:
            raise self._translate(exc) from exc

    def load_finalization(self, decision_id: str) -> FinalizationResult | None:
        try:
            row = self._client.get_entity(
                self._FINALIZATION_CATEGORY, self._key(decision_id)
            )
            return FinalizationResult.from_dict(dict(row["body"]))
        except self._not_found_error:
            return None
        except self._sibyl_error as exc:
            raise self._translate(exc) from exc


def build_sibyl_adapter(
    *, path: Path, tenant_id: str, policy: dict[str, Any]
) -> SibylMemoryAdapter | UnavailableMemoryAdapter:
    try:
        return SibylMemoryAdapter(path=path, tenant_id=tenant_id, policy=policy)
    except (ImportError, ModuleNotFoundError) as exc:
        return UnavailableMemoryAdapter(
            f"official sibyl-memory-client is unavailable: {type(exc).__name__}"
        )
    except Exception as exc:  # noqa: BLE001
        return UnavailableMemoryAdapter(f"Sibyl Memory startup failed: {type(exc).__name__}")
