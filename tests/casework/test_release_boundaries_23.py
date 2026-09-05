"""Final increment regression sources. Not a record of execution.

All protocol responses here are synthetic; real HTTP/Sibyl is a separate gate.
"""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import threading
import pytest
import httpx

from proofops_casework.core import CaseworkError, digest, seal
from proofops_casework.json_boundary import strict_json, read_json_file
from proofops_casework.models import Command, ReopenCommand, ResolveCommand, OpenCaseCommand
from proofops_casework.observations import bounded_observation
from proofops_casework.source_models import ConnectorConfig, MissionCommand, CollectCommand, IncidentSpec
from proofops_casework.source_service import EvidenceDesk
from proofops_casework.source_state import current_receipts
from proofops_casework.incident_ingress import IncidentIngress
from proofops_casework.partner_review import PartnerReviewService
from proofops_casework.connectors.virtuals_cli import ACPHistoryReader
from proofops_casework.connectors.http_client import BoundedHTTP
from proofops_casework.service import CaseworkService
from proofops_casework.mcp_readonly import ReadOnlyMCP
from proofops_casework.release_evidence import public_release, NAMES
from .support import Harness
from .test_sources_22 import environment, collect, config, CountingIssues
from .test_incident_acp_22 import spec, history


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
    b'{"x":1e9999}', b'{"x":"\\ud800"}', b'{"x":', b'\xff'])
def test_ambiguous_json_is_rejected(raw):
    with pytest.raises((ValueError, UnicodeError)):
        strict_json(raw)


def test_deep_json_and_payload_limits():
    with pytest.raises(ValueError):
        strict_json('[' * 60 + '0' + ']' * 60)
    with pytest.raises(ValueError):
        strict_json('{"x":"long"}', max_bytes=5)
    assert strict_json('{"x":true}') == {"x": True}


def test_symlink_and_unsafe_private_file_rejected(tmp_path):
    target = tmp_path / "data.json"; target.write_text('{}'); target.chmod(0o644)
    with pytest.raises(ValueError): read_json_file(target, max_bytes=100, private=True)
    target.chmod(0o600)
    assert read_json_file(target, max_bytes=100, private=True)[0] == {}
    link = tmp_path / "link.json"; link.symlink_to(target)
    with pytest.raises((ValueError, OSError)): read_json_file(link, max_bytes=100)


def test_adapter_cannot_replace_case_or_expiry():
    value = CountingIssues().fetch(None, None, None, None)
    for key, extra in (("case_id", "case_other"), ("expires_at", "2099-01-01T00:00:00Z"), ("authoritative", True)):
        with pytest.raises(CaseworkError, match="SOURCE_ENVELOPE_INVALID"):
            bounded_observation({**value, key: extra})
    value["external_calls"] = True
    with pytest.raises(CaseworkError): bounded_observation(value)


def test_untrusted_http_duplicate_keys_never_arrive_as_facts():
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b'{"state":"open","state":"closed"}'))
    with pytest.raises(CaseworkError):
        BoundedHTTP(transport=transport).json("GET", "https://api.github.com/test")


def test_policy_removal_cannot_bypass_saved_source_obligation():
    h,d,a,c,_ = environment(); collect(h,d,c)
    report = h.investigate(c)["report"]
    EvidenceDesk(h.svc, ConnectorConfig())
    state = h.store.load("tenant_demo")
    with pytest.raises(CaseworkError, match="SOURCE_POLICY_REMOVED"):
        h.svc._valid_report(state, state.cases[c], report["report_id"])


def test_policy_is_remembered_at_case_open_even_before_first_read():
    h = Harness(); EvidenceDesk(h.svc,config(h))
    cid = h.risk()["case"]["case_id"]
    EvidenceDesk(h.svc,ConnectorConfig())
    with pytest.raises(CaseworkError,match="SOURCE_POLICY_REMOVED"):
        h.investigate(cid)


def test_disabling_desk_does_not_make_source_report_manual():
    h,d,a,c,_ = environment(); collect(h,d,c)
    report = h.investigate(c)["report"]
    h.svc.evidence_desk = None
    state = h.store.load("tenant_demo")
    with pytest.raises(CaseworkError,match="SOURCE_GUARD_UNAVAILABLE"):
        h.svc._valid_report(state,state.cases[c],report["report_id"])


def test_optional_sources_still_need_exact_resolution_bundle():
    h,d,a,c,_ = environment(required=False); collect(h,d,c)
    report = h.investigate(c)["report"]; hid = h.handoff(c,report["report_id"])
    with pytest.raises(CaseworkError,match="CURRENT_EVIDENCE_BUNDLE_REQUIRED"):
        h.svc.resolve(h.actors["reviewer"],h.command(ResolveCommand,handoff_id=hid,
            resolution="remediation_verified",evidence_digest="0"*64),c)


def test_reopened_case_cannot_drop_old_optional_sources():
    h,d,a,c,_ = environment(required=False); collect(h,d,c)
    report=h.investigate(c)["report"]; hid=h.handoff(c,report["report_id"])
    root=d.dossier(h.actors["reviewer"],c)["bundle_root"]
    h.svc.resolve(h.actors["reviewer"],h.command(ResolveCommand,handoff_id=hid,
        resolution="remediation_verified",evidence_digest=root),c)
    h.svc.reopen_case(h.actors["owner"],h.command(ReopenCommand,evidence_digest="e"*64),c)
    with pytest.raises(CaseworkError,match="SOURCE_COVERAGE_REQUIRED"):
        h.investigate(c)


def test_mission_continues_in_new_logical_session_without_refetch():
    h,d,a,c,_=environment()
    cmd=h.command(MissionCommand,queries=[{"source_id":"issues","resource":"seekitx/proofops-memoryguard#1"}],
                  reviewer_id=h.actors["reviewer"].actor_id)
    first=d.mission(h.actors["investigator"],cmd,c)
    fresh=CaseworkService(h.store,h.svc.actors,clock=lambda:h.time,test_mode=True)
    desk=EvidenceDesk(fresh,config(h),adapters={"github_issue":a})
    h.session="session_after_restart"
    result=desk.resume_mission(h.actors["investigator"],h.command(),first["mission_id"])
    assert result["stage"]=="HANDED_OFF" and a.calls==1
    assert result["logical_request_reused"] and result["resume_signal"]["session_changed"]
    assert desk.inspect_mission(h.actors["viewer"],first["mission_id"])["report_current"]
    assert h.store.load("tenant_demo").cases[c].status=="OPEN"


def test_mission_pending_attempt_is_visible_and_never_resent(monkeypatch):
    h,d,a,c,_=environment()
    # Simulate process interruption after reservation using BaseException, not a
    # normal HTTP failure handled and committed by the adapter boundary.
    def crash(*_): raise KeyboardInterrupt()
    monkeypatch.setattr(a,"fetch",crash)
    command=h.command(MissionCommand,queries=[{"source_id":"issues","resource":"seekitx/proofops-memoryguard#1"}])
    with pytest.raises(KeyboardInterrupt): d.mission(h.actors["investigator"],command,c)
    state=h.store.load("tenant_demo")
    mission=next(v for v in state.artifacts.values() if v.get("kind")=="EVIDENCE_MISSION")
    h.session="session_resume_pending"
    result=d.resume_mission(h.actors["investigator"],h.command(),mission["mission_id"])
    assert result["stage"]=="COLLECTION_INCOMPLETE"
    assert d.inspect_mission(h.actors["viewer"],mission["mission_id"])["steps"][0]["state"]=="PENDING"


def test_mission_legacy_identity_not_invented():
    h,d,a,c,_=environment()
    result=d.mission(h.actors["investigator"],h.command(MissionCommand,
        queries=[{"source_id":"issues","resource":"seekitx/proofops-memoryguard#1"}]),c)
    state=h.store.load("tenant_demo"); mission=state.artifacts[result["mission_id"]]
    del mission["origin_idempotency_key"]; del mission["origin_session_id"]
    seal(state);h.store.save("tenant_demo",state)
    with pytest.raises(CaseworkError,match="LEGACY_MISSION_REQUIRES_NEW_PLAN"):
        d.resume_mission(h.actors["investigator"],h.command(),result["mission_id"])


def test_hmac_key_reuse_across_sources_rejected(monkeypatch):
    h=Harness(); monkeypatch.setenv("INCIDENT_SECRET_A","s"*48);monkeypatch.setenv("INCIDENT_SECRET_B","s"*48)
    configs=[IncidentSpec(source_id="source_"+str(i),actor_id=h.actors["investigator"].actor_id,
        secret_env=env,scope=h.scope(i)) for i,env in [(1,"INCIDENT_SECRET_A"),(2,"INCIDENT_SECRET_B")]]
    with pytest.raises(ValueError,match="distinct HMAC secrets"):
        IncidentIngress(h.svc,ConnectorConfig(incidents=configs))


def test_acp_valid_but_conflicting_provider_reviews_stop():
    req={"request_id":"review_unique"}; cfg=spec(); data=history(req,cfg)
    other=copy.deepcopy(data["entries"][1]); value=json.loads(other["content"])
    value["recommendation"]="REVIEW_COMPLETED";other["content"]=json.dumps(value)
    data["entries"].insert(2,other);data["entryCount"]=4
    with pytest.raises(CaseworkError,match="ACP_PROVIDER_REVIEW_CONFLICT"):
        ACPHistoryReader(cfg,runner=lambda _:data).history("42",req)


def test_acp_plan_not_current_when_source_ttl_expires():
    h,d,a,c,_=environment();collect(h,d,c);report=h.investigate(c)["report"]
    partner=PartnerReviewService(h.svc,ConnectorConfig(virtuals=spec()),reader=object())
    plan=partner.prepare(h.actors["investigator"],h.command(),c,report["report_id"])["plan"]
    assert partner.inspect(h.actors["viewer"],plan["plan_id"])["current"]
    h.time+=timedelta(seconds=61)
    after=partner.inspect(h.actors["viewer"],plan["plan_id"])
    assert after["current"] is False and "SOURCE_REPORT_STALE" in after["invalid_reasons"]


def test_receipt_resource_cannot_differ_from_reserved_request():
    h,d,a,c,_=environment();res=collect(h,d,c);state=h.store.load("tenant_demo")
    receipt=state.artifacts[res["receipt"]["receipt_id"]]
    receipt["resource"]="seekitx/proofops-memoryguard#2"
    receipt["receipt_root"]=digest("source-receipt",{k:v for k,v in receipt.items() if k!="receipt_root"})
    accepted,rejected=current_receipts(state,c,h.time,d.specs)
    assert not accepted and rejected[0]["reason"]=="SOURCE_REQUEST_BINDING_INVALID"


def test_mcp_invalid_method_does_not_crash_process():
    mcp=ReadOnlyMCP("http://127.0.0.1:8000","x"*40)
    response=mcp.dispatch({"jsonrpc":"2.0","id":1,"method":{"malformed":True}})
    assert response["error"]["code"]==-32600


def test_local_release_forged_ready_field_is_not_trusted(tmp_path):
    at=datetime.now(timezone.utc)
    payload={"schema_version":"memoryguard-release-gate/1","mode":"EXECUTED_LOCAL",
        "captured_at":at.isoformat(),"build_commit":"a"*40,"source_digest":"b"*64,
        "git_clean":True,"source_stable":True,"local_release_ready":True,
        "stages":[{"name":name,"state":"PASSED" if name!="contracts" else "NOT_RUN"} for name in sorted(NAMES)]}
    path=tmp_path/"release.json";path.write_text(json.dumps(payload))
    result=public_release(path,commit="a"*40,source="b"*64)
    assert result["state"]=="CURRENT_INCOMPLETE" and not result["local_release_ready"]
    assert not result["contest_submission_ready"]
    payload["captured_at"]=(at+timedelta(days=2)).isoformat();path.write_text(json.dumps(payload))
    assert public_release(path,commit="a"*40,source="b"*64)["state"]=="INVALID_RECORD"


def test_concurrent_same_investigation_has_one_model_attempt():
    # The first model blocks while a second request attempts the SAME logical
    # command. Real remote charges are never produced by this test.
    class Model:
        def __init__(self):
            self.entered=threading.Event();self.release=threading.Event();self.calls=0
        def plan(self,**kwargs):
            self.calls+=1;self.entered.set()
            if not self.release.wait(5):raise RuntimeError("test timeout")
            raise RuntimeError("synthetic provider unavailable")
    model=Model();h=Harness(model=model);case=h.risk()["case"]["case_id"]
    command=h.command();results=[];errors=[]
    def first():
        try:results.append(h.svc.investigate(h.actors["investigator"],command,case))
        except BaseException as exc:errors.append(exc)
    worker=threading.Thread(target=first);worker.start()
    try:
        assert model.entered.wait(5)
        with pytest.raises(CaseworkError,match="INVESTIGATION_IN_PROGRESS_OR_UNCERTAIN"):
            h.svc.investigate(h.actors["investigator"],command,case)
    finally:
        model.release.set();worker.join(6)
    assert not worker.is_alive() and not errors and model.calls==1
    assert results[0]["report"]["planner_status"]=="DEGRADED"


@pytest.mark.parametrize("media", ["application/json", "application/vnd.example+json"])
def test_api_rejects_ambiguous_json_before_pydantic(media):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from proofops_casework.request_limit import CaseworkBodyLimit
    app=FastAPI();app.add_middleware(CaseworkBodyLimit)
    @app.post("/api/v2/echo")
    def echo(body:dict): return body
    with TestClient(app) as client:
        result=client.post("/api/v2/echo",content='{"x":1,"x":2}',headers={"Content-Type":media})
        assert result.status_code==422
        assert result.json()["error"]=="AMBIGUOUS_OR_INVALID_JSON"


def test_new_session_can_discover_mission_without_browser_storage():
    h,d,a,c,_=environment()
    result=d.mission(h.actors["investigator"],h.command(MissionCommand,
        queries=[{"source_id":"issues","resource":"seekitx/proofops-memoryguard#1"}]),c)
    h.session="session_new_browser"
    saved=d.list_missions(h.actors["investigator"])["missions"]
    assert saved[0]["mission_id"]==result["mission_id"]
    assert "origin_idempotency_key" not in json.dumps(saved)
    other=h.actors["viewer"].model_copy(update={"subjects":["another_subject"]})
    assert d.list_missions(other)["missions"]==[]
