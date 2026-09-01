from __future__ import annotations

import copy
from pathlib import Path
from threading import RLock
from typing import Any

from ..canonical import domain_hash
from ..errors import MemoryBackendUnavailable
from ..models import DecisionDraft
from .sibyl_identity import EXPECTED_SIBYL_SCHEMA_VERSION, sibyl_sdk_identity


def _review_receipt(decision: DecisionDraft) -> dict[str, Any]:
    return {
        "action_id": f"act_{domain_hash('review-action', decision.decision_id)[:20]}",
        "kind": "non_executable_human_review_card",
        "decision_id": decision.decision_id,
        "verdict": decision.verdict.value,
        "proof_root": decision.proof_root,
        "expires_at": decision.expires_at.isoformat(),
        "required_gate": "human_review_before_any_external_action",
        "executable": False,
    }


def _escalation_receipt(decision: DecisionDraft) -> dict[str, Any]:
    return {
        "action_id": f"act_{domain_hash('escalation-action', decision.decision_id)[:20]}",
        "kind": "operator_escalation_case",
        "case_ref": domain_hash("agent-escalation", decision.decision_id),
        "decision_id": decision.decision_id,
        "verdict": decision.verdict.value,
        "reason_codes": list(decision.reason_codes),
        "causal_memory_ids": list(decision.causal_memory_ids),
        "executable": False,
    }


def _brief_receipt(decision: DecisionDraft) -> dict[str, Any]:
    return {
        "action_id": f"act_{domain_hash('evidence-brief-action', decision.decision_id)[:20]}",
        "kind": "causal_evidence_brief",
        "decision_id": decision.decision_id,
        "verdict": decision.verdict.value,
        "reason_codes": list(decision.reason_codes),
        "causal_memory_ids": list(decision.causal_memory_ids),
        "memory_version": decision.memory_version,
        "memory_root": decision.memory_root,
        "proof_root": decision.proof_root,
        "executable": False,
    }


class InMemorySafetyActionAdapter:
    """Test-only idempotent store for non-executable safety actions."""

    production_kind = "test_only_safe_actions"

    def __init__(self) -> None:
        self._actions: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def health(self) -> dict[str, Any]:
        return {"available": True, "backend": self.production_kind, "production_eligible": False}

    def _save(self, receipt: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            existing = self._actions.get(str(receipt["action_id"]))
            if existing is not None and existing != receipt:
                raise ValueError("safety action id was reused with different content")
            self._actions[str(receipt["action_id"])] = copy.deepcopy(receipt)
            return copy.deepcopy(receipt)

    def prepare_review(self, decision: DecisionDraft) -> dict[str, Any]:
        return self._save(_review_receipt(decision))

    def create_escalation(self, decision: DecisionDraft) -> dict[str, Any]:
        return self._save(_escalation_receipt(decision))

    def prepare_evidence_brief(self, decision: DecisionDraft) -> dict[str, Any]:
        return self._save(_brief_receipt(decision))


class UnavailableSafetyActionAdapter:
    production_kind = "sibyl_safe_actions_unavailable"

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def health(self) -> dict[str, Any]:
        return {
            "available": False,
            "backend": self.production_kind,
            "production_eligible": False,
            "reason": self._reason,
        }

    def _fail(self) -> dict[str, Any]:
        raise MemoryBackendUnavailable(self._reason)

    def prepare_review(self, decision: DecisionDraft) -> dict[str, Any]:
        del decision
        return self._fail()

    def create_escalation(self, decision: DecisionDraft) -> dict[str, Any]:
        del decision
        return self._fail()

    def prepare_evidence_brief(self, decision: DecisionDraft) -> dict[str, Any]:
        del decision
        return self._fail()


class SibylSafetyActionAdapter:
    """Persists only review/escalation receipts; it has no execution capability."""

    production_kind = "sibyl_safe_actions"
    _CATEGORY = "memoryguard-safe-action"

    def __init__(self, *, path: Path, tenant_id: str) -> None:
        from sibyl_memory_client import MemoryClient, NotFoundError, SibylMemoryError

        self._client = MemoryClient.local(path, tenant_id=tenant_id)
        self._not_found_error = NotFoundError
        self._sibyl_error = SibylMemoryError

    @staticmethod
    def _key(action_id: str) -> str:
        return domain_hash("sibyl-safe-action-key", action_id)

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
                **identity,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "available": False,
                "backend": self.production_kind,
                "production_eligible": False,
                "reason": type(exc).__name__,
            }

    def _save(self, receipt: dict[str, Any]) -> dict[str, Any]:
        try:
            key = self._key(str(receipt["action_id"]))
            try:
                row = self._client.get_entity(self._CATEGORY, key)
                existing = dict(row["body"])
                if existing != receipt:
                    raise ValueError("safety action id was reused with different content")
                return existing
            except self._not_found_error:
                pass
            self._client.write_event(
                evaluated=["memoryguard_safe_action_authorized"],
                forward=["commit_non_executable_safety_action"],
                extra={
                    "action_id": receipt["action_id"],
                    "kind": receipt["kind"],
                    "decision_id": receipt["decision_id"],
                    "verdict": receipt["verdict"],
                    "executable": False,
                },
            )
            self._client.set_entity(
                self._CATEGORY,
                key,
                receipt,
                status="prepared",
            )
            return dict(receipt)
        except ValueError:
            raise
        except self._sibyl_error as exc:
            raise MemoryBackendUnavailable(
                f"Sibyl safety action failed: {type(exc).__name__}"
            ) from exc

    def prepare_review(self, decision: DecisionDraft) -> dict[str, Any]:
        return self._save(_review_receipt(decision))

    def create_escalation(self, decision: DecisionDraft) -> dict[str, Any]:
        return self._save(_escalation_receipt(decision))

    def prepare_evidence_brief(self, decision: DecisionDraft) -> dict[str, Any]:
        return self._save(_brief_receipt(decision))


def build_sibyl_safety_actions(
    *, path: Path, tenant_id: str
) -> SibylSafetyActionAdapter | UnavailableSafetyActionAdapter:
    try:
        return SibylSafetyActionAdapter(path=path, tenant_id=tenant_id)
    except (ImportError, ModuleNotFoundError) as exc:
        return UnavailableSafetyActionAdapter(
            f"official sibyl-memory-client is unavailable: {type(exc).__name__}"
        )
    except Exception as exc:  # noqa: BLE001
        return UnavailableSafetyActionAdapter(
            f"Sibyl safety action startup failed: {type(exc).__name__}"
        )
