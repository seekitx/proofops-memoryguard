from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from proofops_memoryguard.adapters import (
    BaseAnchorAdapter,
    DisabledAnchorAdapter,
    build_sibyl_adapter,
)
from proofops_memoryguard.errors import (
    DecisionNotFoundError,
    FinalizationError,
    MemoryBackendUnavailable,
    MemoryConflictError,
    MemoryIntegrityError,
)
from proofops_memoryguard.http import build_router
from proofops_memoryguard.module import MemoryGuard
from proofops_memoryguard.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "apps" / "web"


def _build_guard(settings: Settings) -> MemoryGuard:
    policy = settings.load_policy()
    memory = build_sibyl_adapter(
        path=settings.sibyl_memory_path,
        tenant_id=settings.sibyl_tenant_id,
        policy=policy,
    )
    anchor = DisabledAnchorAdapter()
    if settings.base_anchor_address:
        anchor = BaseAnchorAdapter(
            chain_id=settings.base_chain_id,
            network=settings.base_network,
            rpc_url=settings.base_rpc_url,
            contract=settings.base_anchor_address,
            timeout_seconds=settings.base_rpc_timeout_seconds,
        )
    return MemoryGuard(
        memory=memory,
        anchor=anchor,
        policy=policy,
        decision_ttl_seconds=settings.decision_ttl_seconds,
        production=settings.app_env == "production",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    settings.ensure_dirs()
    settings.validate()
    app.state.settings = settings
    app.state.guard = _build_guard(settings)
    yield


app = FastAPI(
    title="ProofOps MemoryGuard",
    version="0.1.0",
    description="Load-bearing Sibyl Memory safety for high-risk Agent decisions",
    lifespan=lifespan,
)

startup_settings = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(startup_settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


def get_guard() -> MemoryGuard:
    return app.state.guard


app.include_router(build_router(get_guard))
app.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="assets")


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:20]}"
    try:
        content_length = int(request.headers.get("content-length", "0") or 0)
    except ValueError:
        content_length = 1_000_001
    if content_length > 1_000_000:
        return JSONResponse(
            status_code=413,
            content={"error": "PAYLOAD_TOO_LARGE", "request_id": request_id},
        )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(MemoryBackendUnavailable)
async def memory_unavailable(_request: Request, exc: MemoryBackendUnavailable) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "MEMORY_BACKEND_UNAVAILABLE",
            "verdict": "memory_unavailable",
            "message": str(exc),
            "executable": False,
        },
    )


@app.exception_handler(MemoryIntegrityError)
async def memory_integrity(_request: Request, exc: MemoryIntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": "MEMORY_INTEGRITY_FAILED", "message": str(exc), "executable": False},
    )


@app.exception_handler(MemoryConflictError)
async def memory_conflict(_request: Request, exc: MemoryConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "MEMORY_CONFLICT", "message": str(exc)},
    )


@app.exception_handler(DecisionNotFoundError)
async def decision_not_found(_request: Request, exc: DecisionNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "DECISION_NOT_FOUND", "message": str(exc)},
    )


@app.exception_handler(FinalizationError)
async def finalization_failed(_request: Request, exc: FinalizationError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "FINALIZATION_FAILED", "message": str(exc)},
    )


@app.exception_handler(ValueError)
async def validation_failed(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "MEMORY_INVALID", "message": str(exc)},
    )


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> JSONResponse:
    memory = get_guard().backend_status
    content = {"status": "ready" if memory.get("available") else "degraded", "memory": memory}
    return JSONResponse(status_code=200 if memory.get("available") else 503, content=content)


@app.get("/api/runtime")
async def runtime() -> dict[str, Any]:
    settings: Settings = app.state.settings
    memory = get_guard().backend_status
    return {
        "app_env": settings.app_env,
        "memory": memory,
        "sibyl_is_load_bearing": memory.get("backend") == "sibyl_memory",
        "production_fallback": False,
        "base": {
            "chain_id": settings.base_chain_id,
            "network": settings.base_network,
            "anchor_configured": bool(settings.base_anchor_address),
            "multiplier_claimed": False,
        },
        "github_repo_url": settings.github_repo_url,
        "build_commit": settings.build_commit,
        "server_time_utc": datetime.now(UTC).isoformat(),
    }


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/proof", include_in_schema=False)
async def proof_page() -> FileResponse:
    return FileResponse(WEB_ROOT / "proof.html")
