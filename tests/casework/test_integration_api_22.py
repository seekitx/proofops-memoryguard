"""HTTP wiring tests, using only explicit local test doubles; unexecuted in delivery."""
import hashlib
import importlib.util
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from proofops_casework.api import build_router
from proofops_casework.auth import TokenRegistry
from proofops_casework.core import CaseworkError
from proofops_casework.integration_api import build_integration_router
from proofops_casework.incident_ingress import IncidentIngress
from proofops_casework.partner_review import PartnerReviewService
from proofops_casework.source_models import ConnectorConfig
from proofops_casework.source_public import public_source_experiment
from .test_sources_22 import environment, collect


def client():
    h,d,a,c,t=environment()
    tokens={role:(role+'x'*40) for role in h.actors}
    registry=TokenRegistry([{"token_sha256":hashlib.sha256(tokens[role].encode()).hexdigest(),
                            "principal":actor.model_dump()} for role,actor in h.actors.items()])
    app=FastAPI()
    @app.exception_handler(CaseworkError)
    def error(_,exc): return JSONResponse(status_code=exc.status,content={"error":exc.code,"executable":False})
    web=Path(__file__).resolve().parents[2]/'apps/web'
    partner=PartnerReviewService(h.svc,ConnectorConfig())
    ingress=IncidentIngress(h.svc,ConnectorConfig())
    app.include_router(build_router(lambda:h.svc,lambda:registry,web))
    app.include_router(build_integration_router(lambda:h.svc,lambda:registry,lambda:d,
                       lambda:partner,lambda:ingress,web))
    return TestClient(app),h,d,a,c,t,{r:{"Authorization":"Bearer "+v} for r,v in tokens.items()}


def test_private_reads_need_authentication():
    cli,h,d,a,c,t,headers=client()
    assert cli.get(f'/api/v2/cases/{c}/dossier').status_code==401
    result=cli.get(f'/api/v2/cases/{c}/dossier',headers=headers['viewer'])
    assert result.status_code==200 and result.json()['coverage_complete'] is False


def test_viewer_cannot_collect():
    cli,h,d,a,c,t,headers=client()
    payload={'idempotency_key':'request_001','session_id':'session_001',
             'expected_revision':h.store.load('tenant_demo').revision,'source_id':'issues',
             'resource':'seekitx/proofops-memoryguard#1'}
    result=cli.post(f'/api/v2/cases/{c}/sources',headers=headers['viewer'],json=payload)
    assert result.status_code==403 and a.calls==0


def test_client_cannot_send_url_or_authority():
    cli,h,d,a,c,t,headers=client()
    payload={'idempotency_key':'request_001','session_id':'session_001',
             'expected_revision':h.store.load('tenant_demo').revision,'source_id':'issues',
             'resource':'seekitx/proofops-memoryguard#1','rpc_url':'http://localhost','authority':True}
    assert cli.post(f'/api/v2/cases/{c}/sources',headers=headers['investigator'],json=payload).status_code==422
    assert a.calls==0


def test_report_exports_exact_historical_bundle(tmp_path):
    cli,h,d,a,c,t,headers=client(); collect(h,d,c)
    report=h.investigate(c)['report']
    response=cli.get(f"/api/v2/reports/{report['report_id']}/sources",headers=headers['viewer'])
    assert response.status_code==200
    value=response.json()
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('report_verify',root/'scripts/casework_verify_report.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.verify(value)['trace_bound'] is True
    value['source_snapshot']['bundle']['coverage_complete']=False
    with pytest.raises(ValueError): module.verify(value)


def test_no_public_record_does_not_become_passed():
    result=public_source_experiment(None,commit='a'*40,source_digest='b'*64)
    assert result['state']=='NOT_RECORDED' and not result['partner_bonus_claimed']


def test_arbitrary_json_cannot_be_exposed_by_public_summary(tmp_path):
    path=tmp_path/'export.json';path.write_text(json.dumps({'token':'must-not-leak'}))
    result=public_source_experiment(path,commit='a'*40,source_digest='b'*64)
    assert result['state']=='INVALID_EXPORT' and 'must-not-leak' not in json.dumps(result)
