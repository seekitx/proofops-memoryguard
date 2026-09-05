"""A real ACP history integration, without installing a server-side economic executor."""
from __future__ import annotations

import copy
from datetime import timedelta

from .core import CaseworkError, authorize, digest, new_id, investigation_basis, scope_key
from .models import Command
from .source_state import parsed_time
from .connectors.virtuals_cli import ACPHistoryReader


class PartnerReviewService:
    def __init__(self, service, config, *, reader=None):
        self.svc=service
        self.spec=config.virtuals
        self.reader=reader or (ACPHistoryReader(self.spec) if self.spec else None)

    def _allowed(self,actor,case):
        if (self.spec is None or actor.tenant_id!=self.spec.tenant_id
                or case.scope.subject_id not in self.spec.subjects
                or case.scope.subject_id not in actor.subjects):
            raise CaseworkError("ACP_REVIEW_NOT_CONFIGURED_FOR_SCOPE",403)

    def _current(self,state,case,plan):
        reasons=[]
        config_matches=plan.get("partner_spec_hash")==digest("virtuals-spec",self.spec.model_dump(mode="json"))
        if not config_matches: reasons.append("ACP_CONFIG_CHANGED")
        if parsed_time(plan["expires_at"])<=self.svc.clock(): reasons.append("ACP_PLAN_EXPIRED")
        if case.version!=plan["case_version"] or case.status!="OPEN": reasons.append("ACP_CASE_CHANGED")
        try:
            report=self.svc._valid_report(state,case,plan["report_id"])
            if report.basis_hash!=plan["basis_hash"]: reasons.append("ACP_BASIS_CHANGED")
        except CaseworkError as exc:
            reasons.append(exc.code)
        return not reasons,reasons,config_matches

    def prepare(self,actor,cmd,case_id,report_id):
        authorize(actor,{"investigator"})
        def build(state,seq):
            case=self.svc._case(state,actor,case_id)
            self._allowed(actor,case)
            report=self.svc._valid_report(state,case,report_id)
            if report.investigator_id!=actor.actor_id:
                raise CaseworkError("REPORT_OWNER_MISMATCH",403)
            existing=next((v for v in state.artifacts.values() if v.get("kind")=="ACP_REVIEW_PLAN"
                           and v.get("report_id")==report_id),None)
            if (existing and existing.get("partner_spec_hash") == digest("virtuals-spec", self.spec.model_dump(mode="json"))
                    and parsed_time(existing["expires_at"]) > self.svc.clock()):
                return {"plan":existing,"already_prepared":True}
            at=self.svc.clock()
            plan_id=new_id("acpreview")
            requirements={"schema_version":"memoryguard-review-request/1","request_id":plan_id,
                "case_version":case.version,"risk_kind":case.kind,"scope_digest":scope_key(case.scope),
                "report_root":report.report_root,"basis_hash":report.basis_hash,
                "evidence_digest":case.evidence_digest,"no_resolution_authority":True}
            if self.svc.evidence_desk:
                requirements["source_bundle_root"]=self.svc.evidence_desk.context(state,case_id,at)["bundle_root"]
            plan={"kind":"ACP_REVIEW_PLAN","plan_id":plan_id,"case_id":case_id,
                  "case_version":case.version,"report_id":report_id,"basis_hash":report.basis_hash,
                  "requirements":requirements,"request_hash":digest("acp-requirements",requirements),
                  "provider_address":self.spec.provider_address.lower(),"client_address":self.spec.client_address.lower(),
                  "chain_id":self.spec.chain_id,"offering_name":self.spec.offering_name,
                  "max_budget_micros":self.spec.max_budget_micros,
                  "budget_enforced_by_server":False,
                  "partner_spec_hash":digest("virtuals-spec",self.spec.model_dump(mode="json")),
                  "expires_at":(at+timedelta(seconds=self.spec.ttl_seconds)).isoformat(),
                  "state":"OPERATOR_ACTION_REQUIRED","bound_job_id":None,
                  "authority":False,"executable":False,"partner_bonus_claimed":False}
            state.artifacts[plan_id]=plan
            return {"plan":plan,"note":"Creating/funding/completing remains an explicit external operator action"}
        return self.svc._mutate(actor,cmd,"acp.prepare",{"case_id":case_id,"report_id":report_id},build)

    def inspect(self,actor,plan_id):
        authorize(actor,{"owner","investigator","reviewer","viewer"})
        with self.svc.store.transaction(actor.tenant_id):
            state=self.svc._load(actor.tenant_id)
            plan=state.artifacts.get(plan_id)
            if not plan or plan.get("kind")!="ACP_REVIEW_PLAN":
                raise CaseworkError("ACP_PLAN_NOT_FOUND",404)
            case=self.svc._case(state,actor,plan["case_id"])
            self._allowed(actor,case)
            current,reasons,config_matches=self._current(state,case,plan)
            return {"plan":copy.deepcopy(plan),"current":current,"invalid_reasons":reasons,"config_matches":config_matches,
                    "revision":state.revision,"executable":False}

    def verify(self,actor,cmd,plan_id,job_id):
        authorize(actor,{"investigator","reviewer"})
        snapshot=self.inspect(actor,plan_id)
        plan=snapshot["plan"]
        if not snapshot["config_matches"]:
            raise CaseworkError("ACP_CONFIG_CHANGED")
        if plan["bound_job_id"] and plan["bound_job_id"]!=job_id:
            raise CaseworkError("ACP_JOB_ALREADY_BOUND")
        # A successful old job remains auditable after case changes, but cannot be
        # represented as a current review; no action in this service resolves risks.
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            key = digest("idempotency-key", [actor.actor_id, cmd.idempotency_key])
            payload = {"case_id": plan["case_id"], "plan_id": plan_id, "job_id": job_id}
            request = {"command": "acp.verify", "actor": actor.actor_id,
                       "session": cmd.session_id, "payload": payload}
            previous = state.idempotency.get(key)
            if previous:
                if previous["request_hash"] != digest("command", request):
                    raise CaseworkError("IDEMPOTENCY_CONFLICT")
                return copy.deepcopy(previous["response"]) | {"replayed": True, "historical_only": True}
        if snapshot["revision"]!=cmd.expected_revision:
            raise CaseworkError("REVISION_CONFLICT")
        try:
            verification=self.reader.history(job_id,plan["requirements"])
        except CaseworkError as exc:
            verification={"job_id": job_id, "state": "QUERY_FAILED", "error": exc.code,
                          "complete_review_observed": False, "authoritative": False, "executable": False}
        def save(state,seq):
            record=state.artifacts.get(plan_id)
            if not record or record["request_hash"]!=plan["request_hash"]:
                raise CaseworkError("ACP_PLAN_CHANGED")
            if record["bound_job_id"] and record["bound_job_id"]!=job_id:
                raise CaseworkError("ACP_JOB_ALREADY_BOUND")
            # A second plan cannot claim the same external job for another purpose.
            if any(a.get("kind")=="ACP_REVIEW_PLAN" and a.get("bound_job_id")==job_id
                   and a.get("plan_id")!=plan_id and a.get("chain_id")==self.spec.chain_id
                   for a in state.artifacts.values()):
                raise CaseworkError("ACP_JOB_REUSED")
            if verification.get("state") != "QUERY_FAILED":
                record["bound_job_id"]=job_id
            record["state"]="QUERY_FAILED" if verification.get("state") == "QUERY_FAILED" else "HISTORY_OBSERVED"
            record.setdefault("observations",[]).append({**verification,"observed_at":self.svc.clock().isoformat()})
            case=self.svc._case(state,actor,record["case_id"])
            current,reasons,_=self._current(state,case,record)
            return {"verification":verification,"current":current,"invalid_reasons":reasons,"partner_bonus_claimed":False,
                    "case_status_unchanged":case.status,"resolution_performed":False}
        return self.svc._mutate(actor,cmd,"acp.verify",{"case_id":plan["case_id"],
                            "plan_id":plan_id,"job_id":job_id},save)
