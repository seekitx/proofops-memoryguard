import hashlib
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from proofops_casework.auth import TokenRegistry
from proofops_casework.runtime import register_casework
from .support import Harness


@pytest.fixture
def client():
    h = Harness()
    records = [{"token_sha256": hashlib.sha256((role + "_" + "TEST_ONLY_"*5).encode()).hexdigest(),
                "principal": actor.model_dump()} for role, actor in h.actors.items()]
    registry = TokenRegistry(records)
    app = FastAPI()
    app.state.casework = h.svc
    app.state.casework_registry = registry
    app.state.casework_enabled = True
    register_casework(app, Path(__file__).resolve().parents[2] / "apps" / "web")
    @app.post("/api/observations")
    def legacy(): return {"unsafe": "should not run"}
    with TestClient(app) as c:
        yield c, h


def headers(role="owner"):
    return {"Authorization": "Bearer " + role + "_" + "TEST_ONLY_"*5}


def test_authentication_required(client):
    c,h=client
    assert c.get("/api/v2/casework").status_code == 401
    response=c.get("/api/v2/casework", headers=headers())
    assert response.status_code == 200
    assert response.json()["principal"]["role"] == "owner"
    assert response.headers["cache-control"] == "no-store"


def test_legacy_anonymous_write_is_not_a_v2_bypass(client):
    c,h=client
    assert c.post("/api/observations",json={}).status_code == 410


def test_public_cannot_claim_trusted_role(client):
    c,h=client
    response=c.post("/api/v2/cases", headers=headers("viewer"), json={
        "scope":h.scope().model_dump(),"kind":"dispute","evidence_digest":"1"*64,
        **h.command().model_dump()})
    assert response.status_code == 403
    response=c.post("/api/v2/cases", headers=headers(), json={
        "scope":h.scope().model_dump(),"kind":"dispute","evidence_digest":"1"*64,
        **h.command().model_dump(),"role":"reviewer","evidence_mode":"base_mainnet"})
    assert response.status_code == 422


def test_chunked_body_cannot_bypass_limit(client):
    c,h=client
    response=c.post("/api/v2/notes",headers=headers(),content=(b"x"*10000 for _ in range(10)))
    assert response.status_code == 413
    assert response.json()["executable"] is False


def test_memory_failure_is_sanitized(client):
    c,h=client; h.store.available=False
    response=c.get("/api/v2/casework",headers=headers())
    assert response.status_code == 503
    assert response.json() == {"error":"MEMORY_BACKEND_UNAVAILABLE","executable":False}


def test_enabled_home_points_to_casework_not_disabled_legacy_form(client):
    c, h = client
    response = c.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/casework"
    assert c.get("/casework").status_code == 200
