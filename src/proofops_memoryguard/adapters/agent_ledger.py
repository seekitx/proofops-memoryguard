from __future__ import annotations

import copy
import fcntl
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from ..agent_models import AgentRun
from ..canonical import domain_hash
from ..errors import MemoryBackendUnavailable


class InMemoryRunLedgerAdapter:
    """Test-only Agent run ledger."""

    production_kind = "test_only_agent_ledger"

    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}
        self._lock = RLock()

    def health(self) -> dict[str, Any]:
        return {"available": True, "backend": self.production_kind, "production_eligible": False}

    @contextmanager
    def claim(self, run_id: str):  # type: ignore[no-untyped-def]
        del run_id
        with self._lock:
            yield

    def save(self, run: AgentRun) -> None:
        with self._lock:
            self._runs[run.run_id] = copy.deepcopy(run)

    def load(self, run_id: str) -> AgentRun | None:
        with self._lock:
            return copy.deepcopy(self._runs.get(run_id))


class UnavailableRunLedgerAdapter:
    production_kind = "sibyl_agent_ledger_unavailable"

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def health(self) -> dict[str, Any]:
        return {
            "available": False,
            "backend": self.production_kind,
            "production_eligible": False,
            "reason": self._reason,
        }

    @contextmanager
    def claim(self, run_id: str):  # type: ignore[no-untyped-def]
        del run_id
        raise MemoryBackendUnavailable(self._reason)
        yield

    def save(self, run: AgentRun) -> None:
        del run
        raise MemoryBackendUnavailable(self._reason)

    def load(self, run_id: str) -> AgentRun | None:
        del run_id
        raise MemoryBackendUnavailable(self._reason)


class SibylAgentRunAdapter:
    """Persists authoritative Agent states and executor-generated traces in Sibyl."""

    production_kind = "sibyl_agent_ledger"
    _CATEGORY = "memoryguard-agent-run"

    def __init__(self, *, path: Path, tenant_id: str) -> None:
        from sibyl_memory_client import MemoryClient, NotFoundError, SibylMemoryError

        self._client = MemoryClient.local(path, tenant_id=tenant_id)
        self._not_found_error = NotFoundError
        self._sibyl_error = SibylMemoryError
        self._lock_dir = path.parent / ".memoryguard-agent-locks"
        self._lock_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(run_id: str) -> str:
        return domain_hash("sibyl-agent-run-key", run_id)

    def health(self) -> dict[str, Any]:
        try:
            return {
                "available": True,
                "backend": self.production_kind,
                "production_eligible": True,
                "schema_version": self._client.schema_version(),
                "tenant_isolated": True,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "available": False,
                "backend": self.production_kind,
                "production_eligible": False,
                "reason": type(exc).__name__,
            }

    @contextmanager
    def claim(self, run_id: str):  # type: ignore[no-untyped-def]
        lock_path = self._lock_dir / f"{self._key(run_id)}.lock"
        with lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def save(self, run: AgentRun) -> None:
        try:
            run_body = run.to_dict()
            envelope = {
                "schema_version": "1.0",
                "run": run_body,
                "run_hash": domain_hash("agent-run-ledger", run_body),
            }
            self._client.set_entity(
                self._CATEGORY,
                self._key(run.run_id),
                envelope,
                status=run.state.value,
            )
            self._client.write_event(
                evaluated=["memoryguard_agent_run_reduced"],
                forward=["commit_agent_run_entity"],
                extra={
                    "run_id": run.run_id,
                    "state": run.state.value,
                    "decision_id": run.decision.decision_id,
                    "verdict": run.verdict.value,
                    "trace_length": len(run.tool_trace),
                    "executable": False,
                },
            )
        except self._sibyl_error as exc:
            raise MemoryBackendUnavailable(
                f"Sibyl Agent run ledger failed: {type(exc).__name__}"
            ) from exc

    def load(self, run_id: str) -> AgentRun | None:
        try:
            row = self._client.get_entity(self._CATEGORY, self._key(run_id))
            envelope = dict(row["body"])
            run_body = dict(envelope["run"])
            if envelope.get("run_hash") != domain_hash("agent-run-ledger", run_body):
                raise MemoryBackendUnavailable("Sibyl Agent run ledger integrity check failed")
            return AgentRun.from_dict(run_body)
        except self._not_found_error:
            return None
        except self._sibyl_error as exc:
            raise MemoryBackendUnavailable(
                f"Sibyl Agent run ledger failed: {type(exc).__name__}"
            ) from exc


def build_sibyl_run_ledger(
    *, path: Path, tenant_id: str
) -> SibylAgentRunAdapter | UnavailableRunLedgerAdapter:
    try:
        return SibylAgentRunAdapter(path=path, tenant_id=tenant_id)
    except (ImportError, ModuleNotFoundError) as exc:
        return UnavailableRunLedgerAdapter(
            f"official sibyl-memory-client is unavailable: {type(exc).__name__}"
        )
    except Exception as exc:  # noqa: BLE001
        return UnavailableRunLedgerAdapter(
            f"Sibyl Agent ledger startup failed: {type(exc).__name__}"
        )
