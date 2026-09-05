from pathlib import Path
from typing import Annotated, Callable

from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse

from .auth import TokenRegistry
from .core import CaseworkError
from .models import (Actor, BaselineCommand, BootstrapCommand, Command, HandoffCommand,
                     Identifier, NoteCommand, OpenCaseCommand, ReopenCommand,
                     ResolveCommand, StrictModel, TaskCommand, AnchorCommand, VerifyAnchorCommand)
from .service import CaseworkService


class PrepareCommand(Command):
    decision_id: Identifier


def build_router(get_service: Callable[[], CaseworkService],
                 get_registry: Callable[[], TokenRegistry], web_root: Path) -> APIRouter:
    router = APIRouter(tags=["memoryguard-casework-v2"])

    def principal(authorization: Annotated[str | None, Header()] = None) -> Actor:
        return get_registry().authenticate(authorization)

    Auth = Annotated[Actor, Depends(principal)]
    # All handlers are synchronous: SQLite and file locks run in FastAPI's worker
    # pool, never on the event loop. The private actor dependency binds tenant/scope.

    @router.get("/casework", include_in_schema=False)
    def workbench():
        return FileResponse(web_root / "casework.html", headers={"Cache-Control": "no-store"})

    @router.get("/api/v2/casework")
    def overview(actor: Auth):
        return get_service().overview(actor)

    @router.get("/api/v2/health")
    def health(actor: Auth):
        data = get_service().overview(actor)
        return {key: data[key] for key in ("revision", "runtime_id", "build_commit", "memory_backend", "executable")}

    @router.get("/api/v2/tasks/{task_id}/recovery")
    def recovery(task_id: Identifier, actor: Auth):
        return get_service().recovery(actor, task_id)

    @router.get("/api/v2/cases/{case_id}/timeline")
    def timeline(case_id: Identifier, actor: Auth):
        return get_service().case_timeline(actor, case_id)

    @router.post("/api/v2/bootstrap")
    def bootstrap(body: BootstrapCommand, actor: Auth):
        return get_service().bootstrap(actor, body)

    @router.post("/api/v2/baselines")
    def baseline(body: BaselineCommand, actor: Auth):
        return get_service().set_baseline(actor, body)

    @router.post("/api/v2/tasks")
    def create_task(body: TaskCommand, actor: Auth):
        return get_service().register_task(actor, body)

    @router.post("/api/v2/tasks/{task_id}/evaluate")
    def evaluate(task_id: Identifier, body: Command, actor: Auth):
        return get_service().evaluate(actor, body, task_id)

    @router.post("/api/v2/tasks/{task_id}/reconsider")
    def reconsider(task_id: Identifier, body: Command, actor: Auth):
        return get_service().evaluate(actor, body, task_id, reconsider=True)

    @router.post("/api/v2/tasks/{task_id}/prepare-review")
    def prepare(task_id: Identifier, body: PrepareCommand, actor: Auth):
        return get_service().prepare_review(actor, body, task_id, body.decision_id)

    @router.get("/api/v2/tasks/{task_id}/replay")
    def replay(task_id: Identifier, actor: Auth):
        return get_service().replay(actor, task_id)

    @router.post("/api/v2/cases")
    def case(body: OpenCaseCommand, actor: Auth):
        return get_service().open_case(actor, body)

    @router.post("/api/v2/cases/{case_id}/reopen")
    def reopen(case_id: Identifier, body: ReopenCommand, actor: Auth):
        return get_service().reopen_case(actor, body, case_id)

    @router.post("/api/v2/cases/{case_id}/investigate")
    def investigate(case_id: Identifier, body: Command, actor: Auth):
        return get_service().investigate(actor, body, case_id)

    @router.post("/api/v2/cases/{case_id}/handoff")
    def handoff(case_id: Identifier, body: HandoffCommand, actor: Auth):
        return get_service().handoff(actor, body, case_id)

    @router.post("/api/v2/handoffs/{handoff_id}/accept")
    def accept(handoff_id: Identifier, body: Command, actor: Auth):
        return get_service().accept_handoff(actor, body, handoff_id)

    @router.post("/api/v2/cases/{case_id}/resolve")
    def resolve(case_id: Identifier, body: ResolveCommand, actor: Auth):
        return get_service().resolve(actor, body, case_id)

    @router.post("/api/v2/notes")
    def quarantine(body: NoteCommand, actor: Auth):
        return get_service().quarantine_note(actor, body)

    @router.post("/api/v2/tasks/{task_id}/anchors")
    def anchor(task_id: Identifier, body: AnchorCommand, actor: Auth):
        return get_service().prepare_anchor(actor, body, task_id, body.decision_id)

    @router.post("/api/v2/anchors/{anchor_id}/verify")
    def verify(anchor_id: Identifier, body: VerifyAnchorCommand, actor: Auth):
        return get_service().verify_anchor(actor, body, anchor_id, body.tx_hash)

    return router
