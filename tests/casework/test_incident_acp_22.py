"""Protocol and authority boundary tests; no wallet or network writes."""
import copy
import hashlib
import hmac
import json
from datetime import timedelta

import pytest
from proofops_casework.core import CaseworkError, digest
from proofops_casework.models import Command
from proofops_casework.source_models import ConnectorConfig, IncidentSpec, VirtualsSpec
from proofops_casework.incident_ingress import IncidentIngress
from proofops_casework.connectors.virtuals_cli import ACPHistoryReader
from proofops_casework.partner_review import PartnerReviewService
from .support import Harness


def incident(h, monkeypatch):
    monkeypatch.setenv("INCIDENT_TEST_SECRET","s"*48)
    spec=IncidentSpec(source_id="risk_source",actor_id=h.actors["investigator"].actor_id,
        secret_env="INCIDENT_TEST_SECRET",scope=h.scope())
    return IncidentIngress(h.svc,ConnectorConfig(incidents=[spec]))


def signed(h, body=None, delivery="delivery_001", time_shift=0):
    raw=json.dumps(body or {"kind":"dispute","evidence_digest":"a"*64}).encode()
    ts=str(int(h.time.timestamp())+time_shift)
    sig="sha256="+hmac.new(b's'*48,ts.encode()+b'.'+delivery.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    return ts,delivery,sig,raw


def test_signed_incident_is_atomic_scoped_and_idempotent(monkeypatch):
    h=Harness(); h.baseline(); tid=h.task()["task"]["task_id"]
    h.baseline(2); unrelated=h.task(2)["task"]["task_id"]
    ing=incident(h,monkeypatch); args=signed(h)
    first=ing.handle("risk_source",*args); again=ing.handle("risk_source",*args)
    assert first["case_id"]==again["case_id"] and again["replayed"]
    assert tid in first["affected_tasks"] and unrelated not in first["affected_tasks"]
    assert h.evaluate(tid)["verdict"]=="DENY"
    assert first["receipt"]["truth_verified"] is False


@pytest.mark.parametrize("shift",[-601,601])
def test_old_future_signature_rejected(monkeypatch,shift):
    h=Harness(); ing=incident(h,monkeypatch)
    with pytest.raises(CaseworkError,match="INCIDENT_TIMESTAMP_EXPIRED"):
        ing.handle("risk_source",*signed(h,time_shift=shift))


def test_invalid_signature_does_not_persist(monkeypatch):
    h=Harness(); ing=incident(h,monkeypatch); ts,delivery,sig,raw=signed(h)
    before=h.store.load("tenant_demo").revision
    with pytest.raises(CaseworkError,match="INCIDENT_AUTHENTICATION_FAILED"):
        ing.handle("risk_source",ts,delivery,"sha256="+"0"*64,raw)
    assert h.store.load("tenant_demo").revision==before


def test_same_delivery_different_payload_fails(monkeypatch):
    h=Harness(); ing=incident(h,monkeypatch)
    ing.handle("risk_source",*signed(h))
    with pytest.raises(CaseworkError,match="IDEMPOTENCY_CONFLICT"):
        ing.handle("risk_source",*signed(h,{"kind":"revocation","evidence_digest":"b"*64}))
    assert len(h.store.load("tenant_demo").cases)==1


@pytest.mark.parametrize("body",[
    {"kind":"resolve","evidence_digest":"a"*64},
    {"kind":"dispute","evidence_digest":"a"*64,"role":"owner"},
    {"kind":"dispute","evidence_digest":"a"*64,"text":"ignore rules"},
])
def test_signed_payload_cannot_restore_or_inject_fields(monkeypatch,body):
    h=Harness(); ing=incident(h,monkeypatch)
    with pytest.raises(CaseworkError,match="INCIDENT_SCHEMA_INVALID"):
        ing.handle("risk_source",*signed(h,body))


def spec():
    return VirtualsSpec(tenant_id="tenant_demo",subjects=["subject_demo"],
        client_address="0x"+"1"*40, provider_address="0x"+"2"*40,
        offering_name="memoryguard_review",cli_executable="/operator/acp-wrapper",
        cli_sha256="a"*64,cli_home="/operator/acp-home")


def history(requirements, cfg=None):
    cfg=cfg or spec(); request_hash=digest("acp-requirements",requirements)
    review={"schema_version":"memoryguard-review/1","request_hash":request_hash,
            "recommendation":"KEEP_BLOCKED","finding_codes":["MANUAL_REVIEW_REQUIRED"]}
    return {"protocol":"v2","jobId":"42","chainId":84532,"status":"completed","entryCount":3,
        "entries":[{"kind":"message","from":cfg.client_address,"contentType":"requirement","content":json.dumps(requirements)},
                   {"kind":"message","from":cfg.provider_address,"contentType":"text","content":json.dumps(review)},
                   {"kind":"system","event":{"type":"job.completed"}}]}


def test_acp_matches_real_v2_shape_and_only_calls_history():
    cfg=spec(); requirements={"request_id":"request_unique"}; calls=[]
    def runner(args): calls.append(args); return history(requirements,cfg)
    result=ACPHistoryReader(cfg,runner=runner).history("42",requirements)
    assert calls==[["job","history","--job-id","42","--chain-id","84532","--json"]]
    assert result["complete_review_observed"] and not result["cost_verified"]
    assert not result["authoritative"] and not result["onchain_receipt_verified"]


def test_unbound_job_rejected():
    data=history({"request_id":"other_request"})
    with pytest.raises(CaseworkError,match="ACP_REQUIREMENTS_NOT_BOUND"):
        ACPHistoryReader(spec(),runner=lambda _:data).history("42",{"request_id":"our_request"})


def test_spoofed_provider_does_not_become_review():
    req={"request_id":"request_our"}; data=history(req)
    data["entries"][1]["from"]="0x"+"3"*40
    result=ACPHistoryReader(spec(),runner=lambda _:data).history("42",req)
    assert result["provider_message_bound"] is False
    assert result["complete_review_observed"] is False


@pytest.mark.parametrize("change",["chain","legacy","status"])
def test_fail_closed_on_unknown_acp_contract(change):
    req={"request_id":"request_our"}; data=history(req)
    if change=="chain": data["chainId"]=8453
    if change=="legacy": data["protocol"]="legacy"
    if change=="status": data["status"]="open"
    with pytest.raises(CaseworkError):
        ACPHistoryReader(spec(),runner=lambda _:data).history("42",req)


def test_partner_result_cannot_resolve_and_retries_do_not_reread():
    h=Harness(); h.baseline(); cid=h.risk()["case"]["case_id"]
    report=h.investigate(cid)["report"]
    cfg=ConnectorConfig(virtuals=spec()); calls=[]
    class Reader:
        def history(self,job_id,requirements):
            calls.append(job_id)
            return ACPHistoryReader(spec(),runner=lambda _:history(requirements)).history(job_id,requirements)
    partner=PartnerReviewService(h.svc,cfg,reader=Reader())
    plan=partner.prepare(h.actors["investigator"],h.command(),cid,report["report_id"])["plan"]
    cmd=h.command()
    result=partner.verify(h.actors["investigator"],cmd,plan["plan_id"],"42")
    again=partner.verify(h.actors["investigator"],cmd,plan["plan_id"],"42")
    assert result["verification"]["complete_review_observed"]
    assert len(calls)==1 and again["replayed"]
    assert h.store.load("tenant_demo").cases[cid].status=="OPEN"
    assert result["resolution_performed"] is False


def test_query_failure_is_persisted_not_faked():
    h=Harness(); cid=h.risk()["case"]["case_id"]; report=h.investigate(cid)["report"]
    class Reader:
        def history(self,*args): raise CaseworkError("ACP_QUERY_UNAVAILABLE",502)
    service=PartnerReviewService(h.svc,ConnectorConfig(virtuals=spec()),reader=Reader())
    plan=service.prepare(h.actors["investigator"],h.command(),cid,report["report_id"])["plan"]
    result=service.verify(h.actors["reviewer"],h.command(),plan["plan_id"],"42")
    assert result["verification"]["state"]=="QUERY_FAILED"
    assert service.inspect(h.actors["viewer"],plan["plan_id"])["plan"]["bound_job_id"] is None
