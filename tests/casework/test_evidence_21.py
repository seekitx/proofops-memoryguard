"""Public evidence must fail closed without reading any private workspace."""
import json
from pathlib import Path
from types import SimpleNamespace

from proofops_casework.evidence import CaptureChecks, public_summary, source_digest
from proofops_casework.runtime import casework_readiness
from .support import Harness


def fixture_capture():
    return {"schema_version": "casework-public-evidence/2.1", "captured_at": "2026-09-05T12:00:00Z",
        "build_commit": "a"*40, "source_digest": "b"*64, "git_clean": True,
        "backend": "OFFICIAL_SIBYL", "sdk_version": "0.7.0", "process_count": 3,
        "checks": {key: True for key in CaptureChecks.model_fields}, "remote_reports": 0}


def read(tmp_path, changes=None):
    data = fixture_capture(); data.update(changes or {})
    path = tmp_path / "synthetic.json"; path.write_text(json.dumps(data))
    return public_summary(path, current_commit="a"*40, current_source_digest="b"*64)


def test_missing_export_never_means_completed():
    assert public_summary(None, current_commit="a"*40, current_source_digest="b"*64)["state"] == "NOT_RECORDED"


def test_matching_self_recorded_is_not_independent_or_judge_verified(tmp_path):
    result = read(tmp_path)
    assert result["state"] == "CURRENT_SELF_RECORDED"
    assert result["contest_gate_awarded"] is False
    assert result["capture"]["independent_evaluation"] is False
    assert result["capture"]["continuous_video"] is False


def test_old_commit_or_source_is_not_current(tmp_path):
    assert read(tmp_path, {"build_commit": "c"*40})["state"] == "HISTORICAL_OR_UNCOMMITTED"
    assert read(tmp_path, {"source_digest": "c"*64})["state"] == "HISTORICAL_OR_UNCOMMITTED"
    assert read(tmp_path, {"git_clean": False})["state"] == "HISTORICAL_OR_UNCOMMITTED"


def test_fixture_backend_is_not_official_evidence(tmp_path):
    assert read(tmp_path, {"backend": "TEST_DOUBLE"})["state"] == "TEST_ONLY"


def test_extra_private_fields_reject_whole_export_without_echo(tmp_path):
    result = read(tmp_path, {"operator_token": "DO_NOT_LEAK_THIS"})
    assert result["state"] == "INVALID_ARTIFACT" and "DO_NOT_LEAK_THIS" not in str(result)


def test_failed_check_is_not_completion(tmp_path):
    data = fixture_capture(); data["checks"]["same_build"] = False
    assert read(tmp_path, data)["state"] == "CHECKS_INCOMPLETE"


def test_source_fingerprint_ignores_media_but_changes_with_code(tmp_path):
    source = tmp_path / "src" / "example.py"; source.parent.mkdir(); source.write_text("a = 1\n")
    first = source_digest(tmp_path)
    (tmp_path / "movie.mp4").write_bytes(b"not-a-real-movie")
    assert source_digest(tmp_path) == first
    source.write_text("a = 2\n")
    assert source_digest(tmp_path) != first


def test_active_v2_readiness_checks_v2_store_and_does_not_require_bootstrap():
    h = Harness()
    h.store.health = lambda tenant: {"available": True, "workspace_initialized": False}
    app = SimpleNamespace(state=SimpleNamespace(casework=h.svc,
        casework_registry=SimpleNamespace(actors=h.svc.actors)))
    result = casework_readiness(app)
    assert result["ready"] and result["initialized_workspaces"] == 0
    def broken(tenant): raise RuntimeError("PRIVATE_PATH_SECRET")
    h.store.health = broken
    result = casework_readiness(app)
    assert not result["ready"] and "PRIVATE_PATH_SECRET" not in str(result)


def test_startup_uses_shared_render_resolved_commit(monkeypatch, tmp_path):
    from proofops_casework import runtime
    monkeypatch.setenv("CASEWORK_ENABLED", "1")
    monkeypatch.setenv("CASEWORK_AUTH_FILE", str(tmp_path / "registry.json"))
    monkeypatch.delenv("BUILD_COMMIT", raising=False)
    monkeypatch.delenv("CASEWORK_BASE_ANCHOR_ADDRESS", raising=False)
    monkeypatch.delenv("CASEWORK_PUBLIC_EVIDENCE_FILE", raising=False)
    monkeypatch.setattr(runtime.TokenRegistry, "from_file",
                        lambda path: SimpleNamespace(actors={}))
    monkeypatch.setattr(runtime, "SibylWorkspaceStore", lambda path: object())
    monkeypatch.setattr(runtime, "source_digest", lambda root: "b" * 64)
    monkeypatch.setattr(runtime, "CaseworkService", lambda store, actors, **kwargs:
                        SimpleNamespace(**kwargs))
    settings = SimpleNamespace(build_commit="a" * 40, app_env="production",
        sibyl_memory_path=tmp_path / "unused.db", agent_model_mode="deterministic")
    app = SimpleNamespace(state=SimpleNamespace())
    runtime.start_casework(app, settings)
    assert app.state.casework.build_commit == settings.build_commit


def test_public_routes_do_not_read_private_business_state():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from proofops_casework.runtime import register_casework
    h = Harness()
    def fail_if_business_read(*args):
        raise AssertionError("public evidence must not read a private workspace")
    h.store.load = fail_if_business_read
    app = FastAPI()
    register_casework(app, Path(__file__).resolve().parents[2] / "unused-web")
    app.state.casework_enabled = True
    app.state.casework = h.svc
    app.state.casework_source_digest = "b" * 64
    with TestClient(app) as client:
        response = client.get("/api/v2/public-evidence")
        assert response.status_code == 200
        assert response.json()["state"] == "NOT_RECORDED"
        runtime = client.get("/api/runtime").json()
        assert runtime["module"] == "casework-v2.1"
        assert "principal" not in runtime and "tenant_id" not in runtime
        assert client.post("/api/observations", json={}).status_code == 410
