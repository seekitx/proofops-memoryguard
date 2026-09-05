"""Authenticated source/mission/partner routes; separate signed incident ingress."""
from pathlib import Path
from typing import Annotated, Callable

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from .models import Actor, Command, Identifier
from .source_models import CollectCommand, MissionCommand, ReviewJobCommand
from .core import CaseworkError, authorize, ancestors


class PreparePartnerCommand(Command):
    report_id: Identifier


def build_integration_router(get_service: Callable, get_registry: Callable,
                             get_desk: Callable, get_partner: Callable,
                             get_ingress: Callable, web_root: Path):
    router=APIRouter(tags=["casework-evidence-integrations"])
    def principal(authorization: Annotated[str | None, Header()]=None):
        return get_registry().authenticate(authorization)
    Auth=Annotated[Actor,Depends(principal)]

    @router.get("/casework/sources",include_in_schema=False)
    def sources_page():
        return FileResponse(web_root/"casework-sources.html",headers={"Cache-Control":"no-store"})

    @router.get("/api/v2/integrations")
    def integrations(actor:Auth):
        return get_desk().catalog(actor)

    @router.get("/api/v2/cases/{case_id}/dossier")
    def dossier(case_id:Identifier,actor:Auth):
        return get_desk().dossier(actor,case_id)

    @router.get("/api/v2/reports/{report_id}/sources")
    def report_sources(report_id:Identifier,actor:Auth):
        return get_desk().export_report(actor,report_id)

    @router.post("/api/v2/cases/{case_id}/sources")
    def collect(case_id:Identifier,body:CollectCommand,actor:Auth):
        return get_desk().collect(actor,body,case_id)

    @router.post("/api/v2/cases/{case_id}/mission")
    def mission(case_id:Identifier,body:MissionCommand,actor:Auth):
        return get_desk().mission(actor,body,case_id)

    @router.post("/api/v2/cases/{case_id}/partner-review")
    def prepare(case_id:Identifier,body:PreparePartnerCommand,actor:Auth):
        return get_partner().prepare(actor,body,case_id,body.report_id)

    @router.get("/api/v2/partner-reviews/{plan_id}")
    def partner_review(plan_id:Identifier,actor:Auth):
        return get_partner().inspect(actor,plan_id)

    @router.post("/api/v2/partner-reviews/{plan_id}/verify")
    def verify_partner(plan_id:Identifier,body:ReviewJobCommand,actor:Auth):
        return get_partner().verify(actor,body,plan_id,body.job_id)

    @router.get("/api/v2/tasks/{task_id}/impact")
    def impact(task_id:Identifier,actor:Auth):
        svc=get_service()
        authorize(actor,{"owner","investigator","reviewer","viewer"})
        with svc.store.transaction(actor.tenant_id):
            state=svc._load(actor.tenant_id)
            svc._task(state,actor,task_id)
            closure=ancestors(state,task_id)
            # Every ancestor is subject checked, even for malformed persisted data.
            for key in closure: svc._task(state,actor,key)
            from .core import decision_validity
            return {"task_id":task_id,"revision":state.revision,
                "nodes":[{"task_id":key,**decision_validity(state,key,svc.clock())} for key in closure],
                "edges":[{"from":parent,"to":key} for key in closure for parent in state.tasks[key].depends_on],
                "executable":False}

    @router.post("/api/v2/integrations/incidents/{source_id}")
    async def incoming(source_id:Identifier,request:Request):
        raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>16384: raise CaseworkError("INCIDENT_TOO_LARGE",413)
        return await run_in_threadpool(get_ingress().handle,source_id,
            request.headers.get("X-MemoryGuard-Timestamp"),
            request.headers.get("X-MemoryGuard-Delivery"),
            request.headers.get("X-MemoryGuard-Signature"),bytes(raw))
    return router
