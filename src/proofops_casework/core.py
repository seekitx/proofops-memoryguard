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
    body = {
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
    }

    links = {key: value for key, value in state.artifacts.items()
             if value.get("kind") == "CASE_RESOLUTION_PROOF"
             and value.get("case_id") in body["cases"]}
    if links:
        body["resolution_evidence"] = links
    return digest("task-basis", body)


def active_precedents(state: Workspace, case_id: str) -> list[str]:
    """Only version-bound, still-resolved lessons can guide (never authorize) work.

    Pre-2.1 lessons have no case_version. They stay in the audit store but are
    intentionally not treated as current precedents; do not invent provenance.
    """
    current = state.cases[case_id]
    result = []
    for key, lesson in state.lessons.items():
        source = state.cases.get(lesson.get("case_id", ""))
        if (source is not None and source.case_id != case_id
                and source.status == "RESOLVED"
                and lesson.get("case_version") == source.version
                and lesson.get("resolved_seq") == source.resolved_seq
                and lesson.get("scope_key") == scope_key(current.scope)
                and lesson.get("kind") == current.kind):
            result.append(key)
    return sorted(result)


def investigation_basis(state: Workspace, case_id: str) -> str:
    case = state.cases[case_id]
    tasks = affected_tasks(state, case.scope)
    body = {
        "case": case.model_dump(mode="json"),
        "affected": {key: task_basis(state, key) for key in tasks},
        "precedents": {key: state.lessons[key] for key in active_precedents(state, case_id)},
    }
    from .source_state import evidence_basis
    external = evidence_basis(state, case_id)
    if external:
        body["external_evidence"] = external
    return digest("investigation-basis", body)


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
    for parent_id in (key for key in closure if key != task_id):
        parent = state.tasks[parent_id]
        previous = state.decisions.get(parent.current_decision_id or "")
        if (parent.status != "READY" or parent.taints or previous is None
                or previous.verdict != "READY" or previous.task_id != parent_id or previous.expires_at <= at
                or previous.basis_hash != task_basis(state, parent_id)):
            return "NEEDS_HUMAN", ["DEPENDENCY_REVIEW_REQUIRED"], causal, []
    if task.taints and not explicit_review:
        return "NEEDS_HUMAN", ["EXPLICIT_RECONSIDERATION_REQUIRED"], causal, []
    return "READY", ["CURRENT_POLICY_PASSED", "HUMAN_CONFIRMATION_STILL_REQUIRED"], causal, []


def decision_validity(state: Workspace, task_id: str, at: datetime) -> dict:
    """Re-evaluate time AND policy; a hash check alone is not a live capability."""
    task = state.tasks[task_id]
    decision = state.decisions.get(task.current_decision_id or "")
    verdict, reasons, _, blockers = policy_result(state, task_id, at)
    invalid = []
    if decision is None:
        invalid.append("DECISION_MISSING")
    else:
        if decision.expires_at <= at:
            invalid.append("DECISION_EXPIRED")
        if decision.basis_hash != task_basis(state, task_id):
            invalid.append("MEMORY_BASIS_CHANGED")
        if task.status != decision.verdict:
            invalid.append("TASK_STATUS_CHANGED")
        if decision.verdict != verdict or sorted(decision.reason_codes) != sorted(reasons):
            invalid.append("CURRENT_POLICY_CHANGED")
    return {"current_proof_valid": not invalid,
            "review_preparable": not invalid and verdict == "READY",
            "effective_verdict": verdict, "effective_reason_codes": reasons,
            "active_blockers": blockers, "proof_invalid_reasons": invalid}


def ready_expiry(state: Workspace, task_id: str, at: datetime, default_expiry: datetime) -> datetime:
    """A child's proof cannot outlive a required baseline or ancestor's proof."""
    limits = [default_expiry]
    for key in ancestors(state, task_id):
        baseline = state.baselines.get(scope_key(state.tasks[key].intent.scope))
        if baseline is not None:
            limits.append(baseline.expires_at)
        if key != task_id:
            decision = state.decisions.get(state.tasks[key].current_decision_id or "")
            if decision is not None:
                limits.append(decision.expires_at)
    result = min(limits)
    if result <= at:
        raise CaseworkError("READY_BASIS_EXPIRED")
    return result


def recovery_plan(state: Workspace, task_id: str, at: datetime) -> dict:
    """Read-only topological checklist, not an optimizer or a batch permission."""
    closure = ancestors(state, task_id)
    rows = []
    for key in closure:
        task = state.tasks[key]
        validity = decision_validity(state, key, at)
        if validity["review_preparable"]:
            step = "NO_REVIEW_NEEDED"
        elif validity["active_blockers"]:
            step = "INVESTIGATE_AND_RESOLVE_EACH_CASE"
        elif any(x in validity["effective_reason_codes"] for x in
                 ("BASELINE_MISSING", "BASELINE_EXPIRED", "LIMIT_EXCEEDED")):
            step = "OWNER_REVIEW_BASELINE_OR_REQUEST"
        elif "DEPENDENCY_REVIEW_REQUIRED" in validity["effective_reason_codes"]:
            step = "REVIEW_ANCESTORS_FIRST"
        else:
            step = "EXPLICIT_RECONSIDERATION"
        rows.append({"task_id": key, "required_predecessors": list(task.depends_on),
                     "next_step": step, **validity})
    return {"task_id": task_id, "memory_revision": state.revision,
            "basis_hash": task_basis(state, task_id), "as_of": at.isoformat(),
            "ordered_steps": rows, "read_only": True, "executable": False,
            "note": "Refresh after each command. This checklist never resolves risks or grants authority."}
