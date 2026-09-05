#!/usr/bin/env python3
"""Reproducible evidence-read experiment. Official Sibyl by default; NO live APIs.

Two arms use the same service, source parser, fixture response and persistent store.
Only forced-refresh differs. Figures measure local synthetic requests, not customers,
real API invoices, real-world safety or statistical generalization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from proofops_casework.core import CaseworkError, new_id
from proofops_casework.models import (Actor, BootstrapCommand, Command, OpenCaseCommand,
    ResolveCommand, HandoffCommand, Scope)
from proofops_casework.service import CaseworkService
from proofops_casework.store import SibylWorkspaceStore
from proofops_casework.evidence import source_digest, git_identity
from proofops_casework.source_models import CollectCommand, SourceSpec, ScopeEvidencePolicy, ConnectorConfig
from proofops_casework.source_service import EvidenceDesk
from proofops_casework.connectors.github_issue import GitHubIssueSource
from proofops_casework.connectors.http_client import BoundedHTTP
import httpx


class SyntheticGitHub(GitHubIssueSource):
    def __init__(self, clock):
        self.requests=0; self.available=True; self.clock=clock
        super().__init__(BoundedHTTP(transport=httpx.MockTransport(self.handle)))
    def handle(self, request):
        self.requests+=1
        if not self.available:
            return httpx.Response(503,json={"error":"synthetic unavailable"})
        return httpx.Response(200,json={"url":str(request.url),"number":1,"state":"closed",
            "title":"synthetic; do not treat this as real external testimony", "body":"ignored",
            "updated_at":self.clock().isoformat(),"closed_at":None})
    def fetch(self,*args):
        result=super().fetch(*args)
        result["provenance"]="SYNTHETIC_GITHUB_TRANSPORT"
        result["claim_boundary"]="Locally generated deterministic HTTP response, not GitHub access"
        return result


def run_arm(backend, repeats, force_refresh):
    with tempfile.TemporaryDirectory(prefix="memoryguard-source-benchmark-") as directory:
        if backend=="sibyl":
            store=SibylWorkspaceStore(Path(directory)/'synthetic-sibyl.db')
        else:
            spec=importlib.util.spec_from_file_location("bench_test_support",ROOT/'tests/casework/support.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            store=module.TestStore()
        actors={role:Actor(actor_id="bench_"+role,tenant_id="bench_tenant",role=role,
                          subjects=["bench_subject"]) for role in ("owner","investigator","reviewer","viewer")}
        actor_map={v.actor_id:v for v in actors.values()}
        timestamp=[datetime.now(timezone.utc)]
        svc=CaseworkService(store,actor_map,clock=lambda:timestamp[0],test_mode=backend=="test",
                            build_commit="synthetic-benchmark-source-context")
        def cmd(cls=Command, **values):
            with store.transaction("bench_tenant"):
                state=store.load("bench_tenant")
            return cls(idempotency_key=new_id('benchcmd'),session_id="benchmark_session",
                       expected_revision=state.revision if state else 0,**values)
        def build_desk(service):
            return EvidenceDesk(service,cfg,adapters={"github_issue":source})
        try:
            svc.bootstrap(actors["owner"],cmd(BootstrapCommand,confirmation="CREATE_CASEWORK_WORKSPACE"))
            scope=Scope(subject_id="bench_subject",target="0x"+"1"*40,method="transfer")
            case_id=svc.open_case(actors['owner'],cmd(OpenCaseCommand,scope=scope,kind="dispute",
                                                    evidence_digest="a"*64))["case"]["case_id"]
            cfg=ConnectorConfig(sources=[SourceSpec(source_id="bench_issues",kind="github_issue",
                tenant_id="bench_tenant",subjects=["bench_subject"],independence_group="synthetic_org",
                repositories=["synthetic/repository"],ttl_seconds=60,max_attempts_per_case=100)],
                policies=[ScopeEvidencePolicy(tenant_id="bench_tenant",scope=scope,required_sources=["bench_issues"])])
            source=SyntheticGitHub(lambda:timestamp[0]); desk=build_desk(svc)
            rows=[]
            for i in range(repeats):
                result=desk.collect(actors['investigator'],cmd(CollectCommand,source_id="bench_issues",
                    resource="synthetic/repository#1",force_refresh=force_refresh),case_id)
                rows.append({"step":i,"state":result["state"],"calls":result.get("external_calls")})
            read_count=source.requests
            # A new service instance is not represented as an operating-system restart.
            next_svc=CaseworkService(store,actor_map,clock=lambda:timestamp[0],test_mode=backend=="test")
            next_desk=build_desk(next_svc)
            resumed=next_desk.collect(actors['investigator'],cmd(CollectCommand,source_id="bench_issues",
                resource="synthetic/repository#1"),case_id)
            report=next_svc.investigate(actors['investigator'],cmd(),case_id)["report"]
            timestamp[0]+=timedelta(seconds=61)
            state=store.load("bench_tenant")
            expiry_blocked=False
            try: next_svc._valid_report(state,state.cases[case_id],report['report_id'])
            except CaseworkError: expiry_blocked=True
            refreshed=next_desk.collect(actors['investigator'],cmd(CollectCommand,source_id="bench_issues",
                resource="synthetic/repository#1"),case_id)
            source.available=False
            failed=next_desk.collect(actors['investigator'],cmd(CollectCommand,source_id="bench_issues",
                resource="synthetic/repository#1",force_refresh=True),case_id)
            return {"arm":"always_refresh" if force_refresh else "durable_cache","requests_in_comparison":read_count,
                "logical_reads":repeats,"trace":rows,
                "checks":{"new_service_reuses_cache":resumed['state']=="CACHE_HIT",
                          "expired_source_invalidates_report":expiry_blocked,
                          "expired_source_refetched":refreshed['state']=="OBSERVED",
                          "failed_refresh_visible":failed['state']=="FAILED",
                          "failed_refresh_does_not_reuse_old_evidence":not next_desk.dossier(actors['viewer'],case_id)['coverage_complete'],
                          "case_not_auto_resolved":store.load('bench_tenant').cases[case_id].status=="OPEN"}}
        finally:
            if backend=="sibyl": store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=['sibyl','test'],default='sibyl')
    parser.add_argument('--reads',type=int,default=8)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not 2<=args.reads<=40: parser.error('--reads must be 2..40')
    try:
        commit,clean=git_identity(ROOT)
        sdk=importlib.metadata.version('sibyl-memory-client') if args.backend=='sibyl' else None
        arms=[run_arm(args.backend,args.reads,force) for force in (False,True)]
        reduction=1-arms[0]['requests_in_comparison']/arms[1]['requests_in_comparison']
        result={"schema_version":"casework-source-experiment/1","captured_at":datetime.now(timezone.utc).isoformat(),
            "build_commit":commit,"git_clean":clean,"source_digest":source_digest(ROOT),
            "backend":"OFFICIAL_SIBYL" if args.backend=='sibyl' else "TEST_DOUBLE",
            "sdk_version":sdk,"external_network":"SYNTHETIC_HTTP_TRANSPORT","arms":arms,
            "local_request_reduction_fraction":reduction,
            "all_checks_passed":all(all(a['checks'].values()) for a in arms),
            "scope":"Controlled repeated identical input within TTL; not invoice savings, independent evaluation, PMF or OS restart proof",
            "no_live_api_calls":True,"no_model_calls":True,"no_wallet_actions":True}
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({"out":str(args.out),"all_checks_passed":result['all_checks_passed'],"backend":result['backend']}))
        return 0 if result['all_checks_passed'] else 1
    except Exception as exc:
        print(json.dumps({"error":type(exc).__name__,"status":"NOT_VERIFIED","no_fallback":True}),file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())
