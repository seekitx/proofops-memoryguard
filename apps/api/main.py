from __future__ import annotations

import json
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
    DeterministicModelAdapter,
    DisabledAnchorAdapter,
    HttpModelAdapter,
    build_sibyl_adapter,
    build_sibyl_run_ledger,
    build_sibyl_safety_actions,
)
from proofops_memoryguard.agent import MemoryGuardAgent
from proofops_memoryguard.errors import (
    DecisionNotFoundError,
    FinalizationError,
    MemoryBackendUnavailable,
    MemoryConflictError,
    MemoryIntegrityError,
)
from proofops_memoryguard.http import build_router
from proofops_memoryguard.module import MemoryGuard
from proofops_memoryguard.rate_limit import FixedWindowRateLimiter
from proofops_memoryguard.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "apps" / "web"
EVIDENCE_ROOT = ROOT / "evidence"
AGENT_RUN_LIMITER = FixedWindowRateLimiter(limit=10, window_seconds=60)
PUBLIC_WRITE_LIMITER = FixedWindowRateLimiter(limit=60, window_seconds=60)


def _build_guard(settings: Settings) -> MemoryGuard:
    policy = settings.load_policy()
    memory = build_sibyl_adapter(
        path=settings.sibyl_memory_path,
        tenant_id=settings.sibyl_tenant_id,
        policy=policy,
    )
    if settings.app_env == "production" and not memory.health().get("production_eligible"):
        raise ValueError("production requires the pinned Sibyl SDK import identity")
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


def _build_agent(
    settings: Settings,
    guard: MemoryGuard,
    runtime_instance_id: str,
) -> MemoryGuardAgent:
    ledger = build_sibyl_run_ledger(
        path=settings.sibyl_memory_path,
        tenant_id=settings.sibyl_tenant_id,
    )
    actions = build_sibyl_safety_actions(
        path=settings.sibyl_memory_path,
        tenant_id=settings.sibyl_tenant_id,
    )
    if settings.app_env == "production":
        if not ledger.health().get("production_eligible"):
            raise ValueError("production requires the pinned Sibyl run-ledger SDK identity")
        if not actions.health().get("production_eligible"):
            raise ValueError("production requires the pinned Sibyl safety-action SDK identity")
    if settings.agent_model_mode == "remote":
        model = HttpModelAdapter(
            url=settings.agent_model_url,
            api_key=settings.agent_model_api_key,
            model=settings.agent_model_name,
            timeout_seconds=settings.agent_model_timeout_seconds,
        )
    else:
        model = DeterministicModelAdapter()
    return MemoryGuardAgent(
        guard=guard,
        model=model,
        ledger=ledger,
        actions=actions,
        runtime_instance_id=runtime_instance_id,
        production=settings.app_env == "production",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    settings.ensure_dirs()
    settings.validate()
    app.state.settings = settings
    app.state.guard = _build_guard(settings)
    app.state.runtime_instance_id = f"runtime_{uuid.uuid4().hex[:20]}"
    app.state.agent = _build_agent(
        settings,
        app.state.guard,
        app.state.runtime_instance_id,
    )
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


def get_agent() -> MemoryGuardAgent:
    return app.state.agent


app.include_router(build_router(get_guard, get_agent))
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
    if request.method == "POST" and request.url.path.startswith("/api/"):
        client_host = request.client.host if request.client else "unknown"
        limiter = (
            AGENT_RUN_LIMITER
            if request.url.path == "/api/agent/runs"
            else PUBLIC_WRITE_LIMITER
        )
        allowed, retry_after = limiter.allow(client_host)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "RATE_LIMITED", "request_id": request_id},
                headers={"Retry-After": str(retry_after)},
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


def readiness_snapshot(
    *, app_env: str, memory: dict[str, Any], agent: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    """Separate optional planner liveness from load-bearing safety stores."""

    hard_dependencies = (memory, agent["run_ledger"], agent["safe_actions"])
    hard_dependencies_ready = all(
        item.get("available")
        and (app_env != "production" or item.get("production_eligible"))
        for item in hard_dependencies
    )
    model = agent["model"]
    model_config_ready = bool(
        model.get("production_eligible") if app_env == "production" else model.get("available")
    )
    ready = hard_dependencies_ready and model_config_ready
    return ready, {
        "status": "ready" if ready else "degraded",
        "memory": memory,
        "agent": agent,
        "model_live": bool(model.get("live_call_verified") or model.get("available")),
        "model_degraded": not bool(model.get("live_call_verified") or model.get("available")),
        "safety_core_ready": hard_dependencies_ready,
        "model_is_authority_dependency": False,
        "safe_degradation": "deterministic verdict and mandatory safety action remain active",
    }


@app.get("/health/ready")
async def health_ready() -> JSONResponse:
    settings: Settings = app.state.settings
    memory = get_guard().backend_status
    agent = get_agent().backend_status
    available, content = readiness_snapshot(
        app_env=settings.app_env,
        memory=memory,
        agent=agent,
    )
    return JSONResponse(status_code=200 if available else 503, content=content)


@app.get("/api/runtime")
async def runtime() -> dict[str, Any]:
    settings: Settings = app.state.settings
    memory = get_guard().backend_status
    return {
        "app_env": settings.app_env,
        "memory": memory,
        "agent": {
            **get_agent().backend_status,
            "runtime_instance_id": app.state.runtime_instance_id,
            "payment_tool_registered": False,
        },
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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


@app.get("/api/evidence-summary")
async def evidence_summary() -> dict[str, Any]:
    """Return a redacted, claim-aware index of committed local evidence."""

    runtime_evidence = _load_json(EVIDENCE_ROOT / "2026-09-01_RUNTIME_EVIDENCE.json")
    remote_evidence = _load_json(
        EVIDENCE_ROOT / "2026-09-01_OPENROUTER_HTTPS_EVIDENCE.json"
    )
    benchmark = _load_json(EVIDENCE_ROOT / "2026-09-05_JUDGE_BENCHMARK.json")
    current_runtime = await runtime()
    current_commit = current_runtime.get("build_commit")
    benchmark_commit = benchmark.get("build_commit")
    historical_commit = runtime_evidence.get("runtime_build_commit")
    remote_commit = remote_evidence.get("runtime_build_commit")
    restart = runtime_evidence.get("restart_demo") or {}
    isolated = runtime_evidence.get("isolated_probe") or {}
    hardening = remote_evidence.get("post_capture_hardening") or {}
    if not isinstance(restart, dict):
        restart = {}
    if not isinstance(isolated, dict):
        isolated = {}
    if not isinstance(hardening, dict):
        hardening = {}

    return {
        "schema_version": "1.0",
        "scope": "Current server state and commit-labelled historical local evidence. A mismatch means the current build has not re-run that historical proof.",
        "current_runtime": current_runtime,
        "official_sibyl_benchmark": {
            "label": "12-check conformance run",
            "evidence_present": bool(benchmark),
            "captured_at_utc": benchmark.get("captured_at_utc"),
            "build_commit": benchmark_commit,
            "current_runtime_commit": current_commit,
            "current_build_matches": bool(
                benchmark_commit and current_commit and benchmark_commit == current_commit
            ),
            "git_dirty_at_capture": benchmark.get("git_dirty_at_capture"),
            "capture_eligible": benchmark.get("capture_eligible"),
            "checks_passed": benchmark.get("checks_passed"),
            "checks_total": benchmark.get("checks_total"),
            "all_checks_passed": benchmark.get("all_checks_passed"),
            "uses_official_sibyl_sdk": benchmark.get("uses_official_sibyl_sdk"),
            "run_scope": benchmark.get("run_scope"),
            "evidence_boundary": benchmark.get("evidence_boundary"),
        },
        "fresh_session_local_evidence": {
            "evidence_class": "historical_process_restart_run",
            "evidence_build_commit": historical_commit,
            "current_runtime_commit": current_commit,
            "current_build_matches": bool(
                historical_commit and current_commit and historical_commit == current_commit
            ),
            "different_runtime_instance": restart.get("different_runtime_instance"),
            "same_action_fingerprint": restart.get("same_action_fingerprint"),
            "session_a_verdict": restart.get("session_a_verdict"),
            "session_b_verdict": restart.get("session_b_verdict"),
            "exact_dispute_recalled": restart.get("exact_dispute_recalled"),
            "review_tool_suppressed": restart.get("review_tool_suppressed"),
            "escalation_tool_succeeded": restart.get("escalation_tool_succeeded"),
            "comparison_checks_passed": restart.get("comparison_checks_passed"),
            "continuous_video_complete": False,
        },
        "isolated_fail_closed_evidence": {
            "evidence_class": "historical_missing_sdk_probe",
            "evidence_build_commit": historical_commit,
            "current_runtime_commit": current_commit,
            "current_build_matches": bool(
                historical_commit and current_commit and historical_commit == current_commit
            ),
            "health_status": isolated.get("health_status"),
            "decision_status": isolated.get("decision_status"),
            "agent_run_status": isolated.get("agent_run_status"),
            "fail_closed_response_observed": isolated.get(
                "fail_closed_response_observed"
            ),
            "deletion_gate_claimed": False,
        },
        "remote_model_evidence": {
            "evidence_build_commit": remote_commit,
            "current_runtime_commit": current_commit,
            "current_build_matches": bool(
                remote_commit and current_commit and remote_commit == current_commit
            ),
            "legacy_generation_count": len(remote_evidence.get("generations") or []),
            "receipt_bound_schema": hardening.get("agent_run_schema"),
            "receipt_bound_live_ab_rerun": hardening.get("receipt_bound_live_ab_rerun"),
            "production_reliability_claimed": False,
        },
        "claim_boundary": {
            "base_multiplier_claimed": False,
            "virtuals_multiplier_claimed": False,
            "pmf_bonus_claimed": False,
            "contest_gate_claimed_by_json": False,
        },
        "source_files": [
            *(
                ["evidence/2026-09-05_JUDGE_BENCHMARK.json"]
                if benchmark
                else []
            ),
            "evidence/2026-09-01_RUNTIME_EVIDENCE.json",
            "evidence/2026-09-01_OPENROUTER_HTTPS_EVIDENCE.json",
        ],
    }


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/proof", include_in_schema=False)
async def proof_page() -> FileResponse:
    return FileResponse(WEB_ROOT / "proof.html")


@app.get("/evidence", include_in_schema=False)
async def evidence_page() -> FileResponse:
    return FileResponse(WEB_ROOT / "evidence.html")
