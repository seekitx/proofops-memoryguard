from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from .models import Actor, Decision, Scope, Workspace


class CaseworkError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code = code
        self.status = status
        super().__init__(code)


def digest(domain: str, payload: object) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")
    return hashlib.sha256(b"memoryguard-casework/v2\0" + domain.encode() + b"\0" + data).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def now() -> datetime:
    return datetime.now(timezone.utc)


def scope_key(scope: Scope) -> str:
    return digest("scope", scope.model_dump(mode="json"))


def authorize(actor: Actor, roles: set[str], subject: str | None = None) -> None:
    if actor.role not in roles or (subject is not None and subject not in actor.subjects):
        raise CaseworkError("FORBIDDEN", 403)


def state_payload(state: Workspace) -> dict:
    return state.model_dump(mode="json", exclude={"state_root"})


def seal(state: Workspace) -> None:
    state.state_root = digest("workspace", state_payload(state))


def validate_workspace(state: Workspace) -> None:
    if state.state_root != digest("workspace", state_payload(state)):
        raise CaseworkError("MEMORY_INTEGRITY_FAILED", 503)
    previous = "0" * 64
    for sequence, event in enumerate(state.audit, 1):
        body = {k: v for k, v in event.items() if k != "event_hash"}
        if (event.get("seq") != sequence or event.get("previous_hash") != previous
                or event.get("event_hash") != digest("event", body)):
            raise CaseworkError("AUDIT_INTEGRITY_FAILED", 503)
        previous = event["event_hash"]
    if len(state.audit) != state.revision:
        raise CaseworkError("MEMORY_REVISION_INVALID", 503)
    for key, case in state.cases.items():
        history = state.case_history.get(key, [])
        if (not history or history[-1] != case
                or [item.version for item in history] != list(range(1, case.version + 1))):
            raise CaseworkError("CASE_HISTORY_INTEGRITY_FAILED", 503)
    for key, baseline in state.baselines.items():
        history = state.baseline_history.get(key, [])
        if (not history or history[-1] != baseline
                or [item.version for item in history] != list(range(1, baseline.version + 1))):
            raise CaseworkError("BASELINE_HISTORY_INTEGRITY_FAILED", 503)
    for key, decision in state.decisions.items():
        if (key != decision.decision_id or decision.proof_root != digest(
                "decision", decision.model_dump(mode="json", exclude={"proof_root"}))):
            raise CaseworkError("DECISION_INTEGRITY_FAILED", 503)
    for key, report in state.reports.items():
        if key != report.report_id or report.report_root != digest(
                "investigation", report.model_dump(mode="json", exclude={"report_root"})):
            raise CaseworkError("REPORT_INTEGRITY_FAILED", 503)


def ancestors(state: Workspace, task_id: str) -> list[str]:
    """Full transitive closure, no two-hop cutoff. Fail on missing nodes/cycles."""
    visited: set[str] = set()
    visiting: set[str] = set()
    ordered: list[str] = []

    def walk(key: str) -> None:
        if key in visiting:
            raise CaseworkError("DEPENDENCY_CYCLE", 503)
        if key in visited:
            return
        task = state.tasks.get(key)
        if task is None:
            raise CaseworkError("DEPENDENCY_MISSING", 503)
        visiting.add(key)
        for parent in sorted(task.depends_on):
            walk(parent)
        visiting.remove(key)
        visited.add(key)
        ordered.append(key)

    walk(task_id)
    return ordered


def affected_tasks(state: Workspace, scope: Scope) -> list[str]:
    # Fixed point propagation over exact scoped edges; unrelated scopes remain untouched.
    wanted = scope_key(scope)
    result = {key for key, task in state.tasks.items() if scope_key(task.intent.scope) == wanted}
    while True:
        added = {key for key, task in state.tasks.items()
                 if key not in result and any(parent in result for parent in task.depends_on)}
        if not added:
            return sorted(result)
        result.update(added)


def task_basis(state: Workspace, task_id: str) -> str:
    closure = ancestors(state, task_id)
    scopes = {scope_key(state.tasks[key].intent.scope) for key in closure}
    return digest("task-basis", {
        "tasks": {key: {
            "intent": state.tasks[key].intent.model_dump(mode="json"),
            "depends_on": state.tasks[key].depends_on,
            # The task's own latest decision is deliberately excluded to avoid self-reference.
            "parent_decision": (state.tasks[key].current_decision_id if key != task_id else None),
            "parent_status": (state.tasks[key].status if key != task_id else None),
        } for key in closure},
        "baselines": {key: item.model_dump(mode="json")
                      for key, item in state.baselines.items() if key in scopes},
        "cases": {key: item.model_dump(mode="json")
                  for key, item in state.cases.items() if scope_key(item.scope) in scopes},
    })


def investigation_basis(state: Workspace, case_id: str) -> str:
    case = state.cases[case_id]
    tasks = affected_tasks(state, case.scope)
    return digest("investigation-basis", {
        "case": case.model_dump(mode="json"),
        "affected": {key: task_basis(state, key) for key in tasks},
    })


def policy_result(state: Workspace, task_id: str, at: datetime,
                  *, explicit_review: bool = False) -> tuple[str, list[str], list[str], list[str]]:
    task = state.tasks[task_id]
    closure = ancestors(state, task_id)
    scopes = {scope_key(state.tasks[key].intent.scope) for key in closure}
    blockers = sorted(key for key, item in state.cases.items()
                      if item.status == "OPEN" and scope_key(item.scope) in scopes)
    causal = [f"case:{key}:v{state.cases[key].version}" for key in blockers]
    # Resolved facts remain causal provenance; no event is erased.
    causal += sorted(f"resolution:{key}:v{item.version}" for key, item in state.cases.items()
                     if item.status == "RESOLVED" and scope_key(item.scope) in scopes)
    if blockers:
        return "DENY", ["OPEN_RISK_RECALLED"], causal, blockers
    for key in closure:
        candidate = state.tasks[key]
        baseline = state.baselines.get(scope_key(candidate.intent.scope))
        if baseline is None:
            return "NEEDS_HUMAN", ["BASELINE_MISSING"], causal, []
        causal.append(f"baseline:{scope_key(baseline.scope)}:v{baseline.version}")
        if baseline.expires_at <= at:
            return "NEEDS_HUMAN", ["BASELINE_EXPIRED"], causal, []
        if candidate.intent.amount_minor > baseline.limit_minor:
            return "NEEDS_HUMAN", ["LIMIT_EXCEEDED"], causal, []
    for parent_id in task.depends_on:
        parent = state.tasks[parent_id]
        previous = state.decisions.get(parent.current_decision_id or "")
        if (parent.status != "READY" or previous is None or previous.expires_at <= at
                or previous.basis_hash != task_basis(state, parent_id)):
            return "NEEDS_HUMAN", ["DEPENDENCY_REVIEW_REQUIRED"], causal, []
    if task.taints and not explicit_review:
        return "NEEDS_HUMAN", ["EXPLICIT_RECONSIDERATION_REQUIRED"], causal, []
    return "READY", ["CURRENT_POLICY_PASSED", "HUMAN_CONFIRMATION_STILL_REQUIRED"], causal, []
