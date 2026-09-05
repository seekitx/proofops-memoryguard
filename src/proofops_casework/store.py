from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .core import CaseworkError, digest, validate_workspace
from .models import Workspace


class SibylWorkspaceStore:
    """Official SDK only. One atomic entity is the tenant's consistency boundary.

    File locks coordinate processes; they contain no business state. This adapter
    supports a SINGLE POSIX host on local storage, not NFS or distributed replicas.
    """
    production_kind = "official_sibyl_casework"
    category = "memoryguard-casework-v2"

    def __init__(self, path: Path, *, lock_timeout: float = 5.0):
        if os.name != "posix":
            raise RuntimeError("Casework locking currently requires Linux or macOS")
        from sibyl_memory_client import MemoryClient, NotFoundError
        self.client_factory = MemoryClient.local
        self.not_found = NotFoundError
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_dir = self.path.parent / (self.path.name + ".casework-locks")
        self.lock_dir.mkdir(mode=0o700, exist_ok=True)
        self.timeout = lock_timeout
        self.thread_lock = threading.RLock()
        self.local = threading.local()

    def _client(self, tenant_id: str):
        clients = getattr(self.local, "clients", None)
        if clients is None:
            clients = self.local.clients = {}
        if tenant_id not in clients:
            clients[tenant_id] = self.client_factory(self.path, tenant_id=tenant_id)
        return clients[tenant_id]

    @contextmanager
    def transaction(self, tenant_id: str) -> Iterator[None]:
        import fcntl
        filename = self.lock_dir / (digest("lock", tenant_id) + ".lock")
        if not self.thread_lock.acquire(timeout=self.timeout):
            raise CaseworkError("MEMORY_LOCK_TIMEOUT", 503)
        fd = None
        try:
            fd = os.open(filename, os.O_RDWR | os.O_CREAT, 0o600)
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise CaseworkError("MEMORY_LOCK_TIMEOUT", 503)
                    time.sleep(0.01)
            yield
        except CaseworkError:
            raise
        except Exception as exc:
            raise CaseworkError("MEMORY_BACKEND_UNAVAILABLE", 503) from exc
        finally:
            if fd is not None:
                os.close(fd)  # also releases flock
            self.thread_lock.release()

    def load(self, tenant_id: str) -> Workspace | None:
        try:
            client = self._client(tenant_id)
            row = client.get_entity(self.category, digest("workspace-key", tenant_id))
            state = Workspace.model_validate(row["body"])
            validate_workspace(state)
            return state
        except self.not_found:
            return None
        except CaseworkError:
            raise
        except Exception as exc:
            raise CaseworkError("MEMORY_BACKEND_UNAVAILABLE", 503) from exc

    def save(self, tenant_id: str, state: Workspace) -> None:
        validate_workspace(state)
        body = state.model_dump(mode="json")
        if len(json.dumps(body, ensure_ascii=False).encode()) > 8_000_000:
            raise CaseworkError("WORKSPACE_CAPACITY_REACHED", 413)
        try:
            self._client(tenant_id).set_entity(
                self.category, digest("workspace-key", tenant_id), body, status="active")
        except Exception as exc:
            # The write MAY have committed before a transport/storage error. Retry
            # with the same idempotency key; never claim an external action happened.
            raise CaseworkError("MEMORY_WRITE_UNCERTAIN", 503) from exc

    def close(self) -> None:
        for client in getattr(self.local, "clients", {}).values():
            close = getattr(client, "close", None) or getattr(getattr(client, "storage", None), "close", None)
            if callable(close):
                close()
        self.local.clients = {}
