from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .api import build_router
from .auth import TokenRegistry
from .core import CaseworkError
from .service import CaseworkService
from .store import SibylWorkspaceStore
from .request_limit import CaseworkBodyLimit


def register_casework(app: FastAPI, web_root: Path) -> None:
    app.add_middleware(CaseworkBodyLimit)
    def service():
        value = getattr(app.state, "casework", None)
        if value is None:
            raise CaseworkError("CASEWORK_NOT_ENABLED", 503)
        return value

    def registry():
        service()  # identical enabled/readiness boundary for auth
        return app.state.casework_registry

    app.include_router(build_router(service, registry, web_root))

    @app.exception_handler(CaseworkError)
    async def casework_error(_request: Request, exc: CaseworkError):
        return JSONResponse(status_code=exc.status, content={"error": exc.code, "executable": False},
                            headers={"Cache-Control": "no-store"})

    @app.middleware("http")
    async def isolate_casework(request: Request, call_next):
        enabled = getattr(app.state, "casework_enabled", False)
        path = request.url.path
        if enabled and path == "/" and request.method in {"GET", "HEAD"}:
            # The old public form cannot continue advertising now-disabled writes.
            return RedirectResponse("/casework", status_code=307,
                                    headers={"Cache-Control": "no-store"})
        # Never allow the legacy anonymous fixture write path to become an
        # alternative authority path when the casework workbench is enabled.
        if (enabled and request.method not in {"GET", "HEAD", "OPTIONS"}
                and path.startswith("/api/") and not path.startswith("/api/v2/")):
            return JSONResponse(status_code=410,
                content={"error": "LEGACY_DEMO_WRITE_DISABLED", "executable": False})
        response = await call_next(request)
        if enabled and path in {"/evidence", "/api/evidence-summary"}:
            response.headers["X-MemoryGuard-Evidence-Scope"] = "historical-v1"
        if path.startswith("/api/v2/") or path == "/casework":
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            if path == "/casework":
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        return response


def start_casework(app: FastAPI, settings) -> None:
    app.state.casework_enabled = os.environ.get("CASEWORK_ENABLED", "0") == "1"
    app.state.casework = None
    if not app.state.casework_enabled:
        return
    registry_path = os.environ.get("CASEWORK_AUTH_FILE")
    if not registry_path:
        raise RuntimeError("CASEWORK_AUTH_FILE is required; no anonymous v2 fallback")
    commit = os.environ.get("BUILD_COMMIT", "local-uncommitted")
    if settings.app_env == "production":
        import re
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise RuntimeError("v2 production evidence requires a full BUILD_COMMIT")
    registry = TokenRegistry.from_file(Path(registry_path))
    store = SibylWorkspaceStore(settings.sibyl_memory_path)
    model = None
    if settings.agent_model_mode == "remote":
        # Reuse the existing bounded planner implementation, not a new provider SDK.
        from proofops_memoryguard.adapters.model import HttpModelAdapter
        model = HttpModelAdapter(url=settings.agent_model_url,
            api_key=settings.agent_model_api_key, model=settings.agent_model_name,
            timeout_seconds=settings.agent_model_timeout_seconds)
    anchor = None
    address = os.environ.get("CASEWORK_BASE_ANCHOR_ADDRESS")
    if address:
        from .anchoring import BaseAuditAnchor
        attester = os.environ.get("CASEWORK_ANCHOR_ATTESTER", "")
        anchor = BaseAuditAnchor(chain_id=settings.base_chain_id, contract=address,
            expected_attester=attester, rpc_url=settings.base_rpc_url)
    app.state.casework_registry = registry
    app.state.casework = CaseworkService(store, registry.actors, model=model, build_commit=commit, anchor=anchor)
