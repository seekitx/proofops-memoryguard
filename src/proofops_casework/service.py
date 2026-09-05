from __future__ import annotations

import copy
import os
from datetime import timedelta
from typing import Any, Callable

from .core import (CaseworkError, affected_tasks, ancestors, authorize, digest,
                   investigation_basis, new_id, now, policy_result, scope_key,
                   seal, task_basis, validate_workspace)
from .models import (Actor, Baseline, BaselineCommand, BootstrapCommand, Command,
                     Decision, Handoff, HandoffCommand, NoteCommand, OpenCaseCommand,
                     ReopenCommand, Report, ResolveCommand, RiskCase, Task,
                     TaskCommand, Workspace)

OWNER = {"owner"}
OPERATORS = {"owner", "investigator"}
INVESTIGATORS = {"investigator"}
REVIEWERS = {"reviewer"}
READERS = {"owner", "investigator", "reviewer", "viewer"}


class CaseworkService:
    """One atomic aggregate per tenant; all decisions remain non-executable.

    No external side effect is performed inside a business mutation. Model planning
    is outside the lock and checked against a fresh relevant-memory basis on return.
    """

    def __init__(self, store: Any, actors: dict[str, Actor], *, model: Any = None,
                 build_commit: str = "local-uncommitted", clock: Callable = now,
                 test_mode: bool = False, anchor: Any = None):
        if not test_mode and getattr(store, "production_kind", None) != "official_sibyl_casework":
            raise ValueError("Only the official Sibyl store is allowed outside tests")
        self.store = store
        self.anchor = anchor
        self.actors = actors
        self.model = model
        self.build_commit = build_commit
        self.clock = clock
        self.runtime_id = new_id("runtime")
        self.process_id = os.getpid()

    def _load(self, tenant_id: str) -> Workspace:
        state = self.store.load(tenant_id)
        if state is None:
            raise CaseworkError("MEMORY_WORKSPACE_MISSING", 503)
        validate_workspace(state)
        if state.tenant_id != tenant_id:
            raise CaseworkError("TENANT_BINDING_FAILED", 503)
        return state

    def _mutate(self, actor: Actor, command: Command, name: str, payload: dict,
                mutate: Callable, *, bootstrap: bool = False,
                relevant_basis: tuple[str, str] | None = None) -> dict:
        # expected_revision is a precondition, not request identity. Its refresh
        # cannot turn an exact idempotent retry into a new command.
        request = {"command": name, "actor": actor.actor_id,
                   "session": command.session_id, "payload": payload}
        fingerprint = digest("command", request)
        key = digest("idempotency-key", [actor.actor_id, command.idempotency_key])
        with self.store.transaction(actor.tenant_id):
            state = self.store.load(actor.tenant_id)
            if state is None:
                if not bootstrap:
                    raise CaseworkError("MEMORY_WORKSPACE_MISSING", 503)
                state = Workspace(tenant_id=actor.tenant_id)
                seal(state)
            validate_workspace(state)
            if state.tenant_id != actor.tenant_id:
                raise CaseworkError("TENANT_BINDING_FAILED", 503)
            # Scope permissions are rechecked BEFORE returning an old response.
            if "task_id" in payload:
                self._task(state, actor, payload["task_id"])
            if "case_id" in payload:
                self._case(state, actor, payload["case_id"])
            if name == "handoff.accept":
                known_handoff = state.handoffs.get(payload["handoff_id"])
                if known_handoff is None or known_handoff.reviewer_id != actor.actor_id:
                    raise CaseworkError("HANDOFF_NOT_FOUND", 404)
                self._case(state, actor, known_handoff.case_id)
            previous = state.idempotency.get(key)
            if previous:
                if previous["request_hash"] != fingerprint:
                    raise CaseworkError("IDEMPOTENCY_CONFLICT")
                if name == "review.prepare":
                    task = self._task(state, actor, payload["task_id"])
                    decision = state.decisions.get(payload["decision_id"])
                    current, _, _, _ = policy_result(state, task.task_id, self.clock())
                    if (decision is None or task.current_decision_id != decision.decision_id
                            or current != "READY" or decision.expires_at <= self.clock()
                            or decision.basis_hash != task_basis(state, task.task_id)):
                        raise CaseworkError("STALE_OR_BLOCKED_REVIEW")
                return copy.deepcopy(previous["response"]) | {"replayed": True, "historical_only": True}
            if relevant_basis is None:
                if state.revision != command.expected_revision:
                    raise CaseworkError("REVISION_CONFLICT")
            else:
                case_id, expected_basis = relevant_basis
                if (case_id not in state.cases or
                        investigation_basis(state, case_id) != expected_basis):
                    raise CaseworkError("STALE_INVESTIGATION")
            if bootstrap and state.revision:
                raise CaseworkError("WORKSPACE_ALREADY_EXISTS")
            if state.revision >= 5000:
                raise CaseworkError("WORKSPACE_CAPACITY_REACHED", 413)
            next_seq = state.revision + 1
            result = mutate(state, next_seq)
            result = copy.deepcopy(result)
            state.revision = next_seq
            event = {
                "seq": next_seq, "at": self.clock().isoformat(),
                "actor_id": actor.actor_id, "role": actor.role,
                "command": name, "request_hash": fingerprint,
                "result_hash": digest("command-result", result),
                "previous_hash": state.audit[-1]["event_hash"] if state.audit else "0" * 64,
            }
            event["event_hash"] = digest("event", event)
            state.audit.append(event)
            response = result | {"revision": next_seq, "event_hash": event["event_hash"],
                                 "executable": False, "replayed": False}
            state.idempotency[key] = {"request_hash": fingerprint, "response": response}
            seal(state)
            self.store.save(actor.tenant_id, state)
            return response

    def bootstrap(self, actor: Actor, cmd: BootstrapCommand) -> dict:
        authorize(actor, OWNER)
        return self._mutate(actor, cmd, "bootstrap", {},
                            lambda state, seq: {"state": "INITIALIZED"}, bootstrap=True)

    def _task(self, state: Workspace, actor: Actor, task_id: str) -> Task:
        task = state.tasks.get(task_id)
        if task is None or task.intent.scope.subject_id not in actor.subjects:
            raise CaseworkError("TASK_NOT_FOUND", 404)
        return task

    def _case(self, state: Workspace, actor: Actor, case_id: str) -> RiskCase:
        case = state.cases.get(case_id)
        if case is None or case.scope.subject_id not in actor.subjects:
            raise CaseworkError("CASE_NOT_FOUND", 404)
        return case

    @staticmethod
    def _invalidate(state: Workspace, scope, token: str, reason: str) -> list[str]:
        impacted = affected_tasks(state, scope)
        for key in impacted:
            state.tasks[key].taints[token] = reason
            state.tasks[key].status = "SUSPENDED"
        return impacted

    def set_baseline(self, actor: Actor, cmd: BaselineCommand) -> dict:
        authorize(actor, OWNER, cmd.scope.subject_id)
        if cmd.expires_at <= self.clock():
            raise CaseworkError("BASELINE_MUST_EXPIRE_IN_FUTURE", 422)
        payload = cmd.model_dump(mode="json", exclude=set(Command.model_fields))

        def change(state, seq):
            key = scope_key(cmd.scope)
            previous = state.baselines.get(key)
            version = previous.version + 1 if previous else 1
            state.baselines[key] = Baseline(scope=cmd.scope, version=version,
                limit_minor=cmd.limit_minor, expires_at=cmd.expires_at,
                actor_id=actor.actor_id, event_seq=seq)
            state.baseline_history.setdefault(key, []).append(state.baselines[key].model_copy(deep=True))
            impacted = self._invalidate(state, cmd.scope, f"baseline:{key}:v{version}",
                                       "BASELINE_CHANGED_REVIEW_REQUIRED")
            return {"baseline_key": key, "version": version, "affected_tasks": impacted,
                    "source": "configured_operator_attestation"}
        return self._mutate(actor, cmd, "baseline.set", payload, change)

    def _decision(self, state: Workspace, task: Task, actor: Actor, cmd: Command,
                  revision: int, *, explicit_review: bool = False) -> Decision:
        at = self.clock()
        verdict, reasons, refs, blockers = policy_result(state, task.task_id, at,
                                                       explicit_review=explicit_review)
        decision = Decision(
            decision_id=new_id("decision"), task_id=task.task_id, verdict=verdict,
            reason_codes=reasons, causal_refs=sorted(set(refs)), active_blockers=blockers,
            action_fingerprint=digest("action", {"tenant_id": actor.tenant_id,
                                               **task.intent.model_dump(mode="json")}),
            basis_hash=task_basis(state, task.task_id), memory_revision=revision,
            session_id=cmd.session_id, runtime_id=self.runtime_id, process_id=self.process_id,
            build_commit=self.build_commit, created_at=at, expires_at=at + timedelta(minutes=10),
            tool="human_review.prepare" if verdict == "READY" else "operator_escalation.create",
        )
        decision.proof_root = digest("decision", decision.model_dump(mode="json", exclude={"proof_root"}))
        for blocker in blockers:
            task.taints[f"case:{blocker}:v{state.cases[blocker].version}"] = "OPEN_RISK"
        state.decisions[decision.decision_id] = decision
        task.current_decision_id = decision.decision_id
        task.status = verdict
        if explicit_review and verdict == "READY":
            task.taints.clear()
        return decision

    def register_task(self, actor: Actor, cmd: TaskCommand) -> dict:
        authorize(actor, OPERATORS, cmd.intent.scope.subject_id)
        payload = cmd.model_dump(mode="json", exclude=set(Command.model_fields))

        def change(state, seq):
            if len(state.tasks) >= 250:
                raise CaseworkError("TASK_CAPACITY_REACHED", 413)
            if len(cmd.depends_on) != len(set(cmd.depends_on)):
                raise CaseworkError("DUPLICATE_DEPENDENCY", 422)
            for parent_id in cmd.depends_on:
                parent = self._task(state, actor, parent_id)
                if parent.intent.scope.subject_id != cmd.intent.scope.subject_id:
                    raise CaseworkError("CROSS_SUBJECT_DEPENDENCY_FORBIDDEN", 403)
            task = Task(task_id=new_id("task"), intent=cmd.intent,
                        depends_on=sorted(cmd.depends_on))
            state.tasks[task.task_id] = task
            decision = self._decision(state, task, actor, cmd, seq)
            return {"task": task.model_dump(mode="json"), "decision": decision.model_dump(mode="json")}
        return self._mutate(actor, cmd, "task.register", payload, change)

    def evaluate(self, actor: Actor, cmd: Command, task_id: str, *, reconsider: bool = False) -> dict:
        authorize(actor, REVIEWERS if reconsider else OPERATORS | REVIEWERS)

        def change(state, seq):
            task = self._task(state, actor, task_id)
            old_id = task.current_decision_id
            decision = self._decision(state, task, actor, cmd, seq, explicit_review=reconsider)
            return {"decision": decision.model_dump(mode="json"), "supersedes": old_id,
                    "taints_remaining": sorted(task.taints)}
        return self._mutate(actor, cmd, "task.reconsider" if reconsider else "task.evaluate",
                            {"task_id": task_id}, change)

    def open_case(self, actor: Actor, cmd: OpenCaseCommand) -> dict:
        authorize(actor, OPERATORS, cmd.scope.subject_id)
        payload = cmd.model_dump(mode="json", exclude=set(Command.model_fields))

        def change(state, seq):
            if len(state.cases) >= 500:
                raise CaseworkError("CASE_CAPACITY_REACHED", 413)
            case = RiskCase(case_id=new_id("case"), scope=cmd.scope, kind=cmd.kind,
                            opened_by=actor.actor_id, opened_seq=seq,
                            evidence_digest=cmd.evidence_digest)
            state.cases[case.case_id] = case
            state.case_history[case.case_id] = [case.model_copy(deep=True)]
            impacted = self._invalidate(state, case.scope, f"case:{case.case_id}:v1", "NEW_RISK")
            return {"case": case.model_dump(mode="json"), "affected_tasks": impacted,
                    "authority": "configured_operator_attestation"}
        return self._mutate(actor, cmd, "case.open", payload, change)

    def reopen_case(self, actor: Actor, cmd: ReopenCommand, case_id: str) -> dict:
        authorize(actor, OPERATORS)

        def change(state, seq):
            case = self._case(state, actor, case_id)
            if case.status != "RESOLVED":
                raise CaseworkError("CASE_ALREADY_OPEN")
            case.status = "OPEN"
            case.version += 1
            case.opened_by = actor.actor_id
            case.opened_seq = seq
            case.evidence_digest = cmd.evidence_digest
            case.resolved_by = case.resolution = case.resolved_seq = None
            state.case_history[case_id].append(case.model_copy(deep=True))
            impacted = self._invalidate(state, case.scope, f"case:{case_id}:v{case.version}", "RISK_REOPENED")
            return {"case": case.model_dump(mode="json"), "affected_tasks": impacted}
        return self._mutate(actor, cmd, "case.reopen", {"case_id": case_id,
                           "evidence_digest": cmd.evidence_digest}, change)

    def quarantine_note(self, actor: Actor, cmd: NoteCommand) -> dict:
        authorize(actor, OPERATORS, cmd.scope.subject_id)
        # Neither the raw note nor model prose is stored. This is data isolation,
        # NOT a claim to detect all possible semantic prompt injections.
        payload = {"scope": cmd.scope.model_dump(mode="json"),
                   "text_hash": digest("untrusted-text", cmd.text)}
        return self._mutate(actor, cmd, "note.quarantine", payload,
            lambda state, seq: {"status": "QUARANTINED", "text_hash": payload["text_hash"],
                                "authority": False, "model_received_raw_text": False})

    def investigate(self, actor: Actor, cmd: Command, case_id: str) -> dict:
        authorize(actor, INVESTIGATORS)
        # Replay an already committed report without calling the provider again.
        request = {"command": "case.investigate", "actor": actor.actor_id,
                   "session": cmd.session_id, "payload": {"case_id": case_id}}
        idem = digest("idempotency-key", [actor.actor_id, cmd.idempotency_key])
        with self.store.transaction(actor.tenant_id):
            snapshot = self._load(actor.tenant_id)
            case = self._case(snapshot, actor, case_id)
            previous = snapshot.idempotency.get(idem)
            if previous:
                if previous["request_hash"] != digest("command", request):
                    raise CaseworkError("IDEMPOTENCY_CONFLICT")
                return copy.deepcopy(previous["response"]) | {"replayed": True, "historical_only": True}
            if snapshot.revision != cmd.expected_revision:
                raise CaseworkError("REVISION_CONFLICT")
            if case.status != "OPEN":
                raise CaseworkError("CASE_NOT_OPEN")
            basis = investigation_basis(snapshot, case_id)
        mandatory = ("case.inspect", "dependencies.trace")
        optional = ("precedent.lookup",)
        requested = optional
        receipt = None
        planner_status = "DETERMINISTIC"
        suppressed: list[str] = []
        if self.model is not None:
            context = {
                "verdict": "deny", "case_kind": case.kind, "case_id": case.case_id,
                "case_version": case.version, "evidence_digest": case.evidence_digest,
                "scope_digest": scope_key(case.scope),
                "affected_task_count": len(affected_tasks(snapshot, case.scope)),
                "non_authoritative_investigation": True,
            }
            try:
                plan = self.model.plan(context=context, allowed_tools=mandatory + optional)
                requested = tuple(str(name) for name in plan.requested_tools)
                suppressed = [digest("suppressed-tool", name) for name in requested
                              if name not in mandatory + optional]
                candidate = getattr(plan, "model_receipt", None)
                needed = {"generation_id", "completion_sha256", "model_context_hash", "resolved_model"}
                if (not isinstance(candidate, dict) or not needed.issubset(candidate)
                        or not all(candidate[k] for k in needed)
                        or candidate.get("live_call_verified") is not True):
                    raise ValueError("missing model receipt")
                allowed_receipt = needed | {"backend", "configured_model", "completed_at",
                                            "live_call_verified", "structured_output_validated"}
                receipt = {key: candidate[key] for key in allowed_receipt if key in candidate}
                planner_status = "REMOTE"
            except Exception:
                requested = ()
                receipt = None
                planner_status = "DEGRADED"
        tools = list(mandatory) + [name for name in optional if name in requested]
        impacted = affected_tasks(snapshot, case.scope)
        scopes = {scope_key(snapshot.tasks[key].intent.scope)
                  for root in impacted for key in ancestors(snapshot, root)}
        related_cases = sorted(key for key, item in snapshot.cases.items()
                               if item.status == "OPEN" and scope_key(item.scope) in scopes)
        precedents = sorted(key for key, item in snapshot.lessons.items()
                            if item["scope_key"] == scope_key(case.scope) and item["kind"] == case.kind)
        outputs = {"case.inspect": {"case_ids": related_cases or [case_id]},
                   "dependencies.trace": {"affected_tasks": impacted},
                   "precedent.lookup": {"precedent_ids": precedents}}
        trace = [{"tool": name, "phase": "SUCCEEDED",
                  "input_hash": digest("tool-input", {"case_id": case_id, "basis": basis}),
                  "output_hash": digest("tool-output", outputs[name]),
                  "result_count": len(next(iter(outputs[name].values())))} for name in tools]
        trace += [{"tool": "unregistered", "phase": "SUPPRESSED", "request_hash": item}
                  for item in suppressed]
        report = Report(report_id=new_id("report"), case_id=case_id, case_version=case.version,
                        investigator_id=actor.actor_id, basis_hash=basis,
                        case_refs=related_cases or [case_id], affected_tasks=impacted,
                        precedent_ids=precedents if "precedent.lookup" in tools else [],
                        trace=trace, model_receipt=receipt, planner_status=planner_status)
        report.report_root = digest("investigation", report.model_dump(mode="json", exclude={"report_root"}))

        def change(state, seq):
            state.reports[report.report_id] = report
            return {"report": report.model_dump(mode="json"),
                    "next_step": "REVIEW_PRIOR_REMEDIATION" if report.precedent_ids else "COLLECT_AND_REVIEW_EVIDENCE"}
        return self._mutate(actor, cmd, "case.investigate", {"case_id": case_id}, change,
                            relevant_basis=(case_id, basis))

    def _valid_report(self, state: Workspace, case: RiskCase, report_id: str) -> Report:
        report = state.reports.get(report_id)
        if report is None or report.case_id != case.case_id:
            raise CaseworkError("REPORT_NOT_FOUND", 404)
        if (report.case_version != case.version or case.status != "OPEN"
                or report.basis_hash != investigation_basis(state, case.case_id)):
            raise CaseworkError("STALE_INVESTIGATION")
        return report

    def handoff(self, actor: Actor, cmd: HandoffCommand, case_id: str) -> dict:
        authorize(actor, INVESTIGATORS)

        def change(state, seq):
            case = self._case(state, actor, case_id)
            report = self._valid_report(state, case, cmd.report_id)
            reviewer = self.actors.get(cmd.reviewer_id)
            if (reviewer is None or reviewer.tenant_id != actor.tenant_id or reviewer.role != "reviewer"
                    or case.scope.subject_id not in reviewer.subjects
                    or reviewer.actor_id in {actor.actor_id, case.opened_by}):
                raise CaseworkError("INDEPENDENT_REVIEWER_REQUIRED", 403)
            if report.investigator_id != actor.actor_id:
                raise CaseworkError("REPORT_OWNER_MISMATCH", 403)
            handoff = Handoff(handoff_id=new_id("handoff"), report_id=report.report_id,
                              case_id=case_id, case_version=case.version,
                              reviewer_id=reviewer.actor_id, investigator_id=actor.actor_id)
            state.handoffs[handoff.handoff_id] = handoff
            return {"handoff": handoff.model_dump(mode="json")}
        return self._mutate(actor, cmd, "case.handoff", {"case_id": case_id,
                           "report_id": cmd.report_id, "reviewer_id": cmd.reviewer_id}, change)

    def accept_handoff(self, actor: Actor, cmd: Command, handoff_id: str) -> dict:
        authorize(actor, REVIEWERS)

        def change(state, seq):
            handoff = state.handoffs.get(handoff_id)
            if handoff is None or handoff.reviewer_id != actor.actor_id:
                raise CaseworkError("HANDOFF_NOT_FOUND", 404)
            case = self._case(state, actor, handoff.case_id)
            self._valid_report(state, case, handoff.report_id)
            if handoff.case_version != case.version:
                raise CaseworkError("STALE_HANDOFF")
            handoff.accepted = True
            return {"handoff": handoff.model_dump(mode="json")}
        return self._mutate(actor, cmd, "handoff.accept", {"handoff_id": handoff_id}, change)

    def resolve(self, actor: Actor, cmd: ResolveCommand, case_id: str) -> dict:
        authorize(actor, REVIEWERS)

        def change(state, seq):
            case = self._case(state, actor, case_id)
            handoff = state.handoffs.get(cmd.handoff_id)
            if (handoff is None or handoff.case_id != case_id or not handoff.accepted
                    or handoff.reviewer_id != actor.actor_id
                    or actor.actor_id in {case.opened_by, handoff.investigator_id}):
                raise CaseworkError("ACKNOWLEDGED_INDEPENDENT_REVIEW_REQUIRED", 403)
            report = self._valid_report(state, case, handoff.report_id)
            if handoff.case_version != case.version:
                raise CaseworkError("STALE_HANDOFF")
            case.status = "RESOLVED"
            case.version += 1
            case.resolution = cmd.resolution
            case.resolved_by = actor.actor_id
            case.resolved_seq = seq
            state.case_history[case_id].append(case.model_copy(deep=True))
            impacted = affected_tasks(state, case.scope)
            for key in impacted:
                # Resolution does NOT revive a draft or clear other unresolved taints.
                state.tasks[key].taints[f"resolution:{case_id}:v{case.version}"] = "RECONSIDER_REQUIRED"
                observed_verdict, _, _, _ = policy_result(state, key, self.clock())
                state.tasks[key].status = "DENY" if observed_verdict == "DENY" else "NEEDS_HUMAN"
            lesson_id = new_id("lesson")
            state.lessons[lesson_id] = {"scope_key": scope_key(case.scope), "kind": case.kind,
                "case_id": case_id, "report_id": report.report_id, "resolution": cmd.resolution,
                "reviewer_id": actor.actor_id, "evidence_digest": cmd.evidence_digest,
                "authority": False}
            return {"case": case.model_dump(mode="json"), "affected_tasks": impacted,
                    "lesson_id": lesson_id, "requires_explicit_reconsideration": True}
        return self._mutate(actor, cmd, "case.resolve", {"case_id": case_id,
            "handoff_id": cmd.handoff_id, "resolution": cmd.resolution,
            "evidence_digest": cmd.evidence_digest}, change)

    def prepare_review(self, actor: Actor, cmd: Command, task_id: str, decision_id: str) -> dict:
        authorize(actor, OPERATORS | REVIEWERS)

        def change(state, seq):
            task = self._task(state, actor, task_id)
            decision = state.decisions.get(decision_id)
            if (decision is None or decision.task_id != task_id
                    or task.current_decision_id != decision_id):
                raise CaseworkError("DECISION_SUPERSEDED")
            current, _, _, _ = policy_result(state, task_id, self.clock())
            if (task.status != "READY" or decision.verdict != "READY" or current != "READY"
                    or decision.expires_at <= self.clock()
                    or decision.basis_hash != task_basis(state, task_id)):
                raise CaseworkError("STALE_OR_BLOCKED_REVIEW")
            artifact_id = digest("review-artifact", [task_id, decision_id])
            artifact = {"artifact_id": artifact_id, "task_id": task_id,
                        "decision_id": decision_id, "proof_root": decision.proof_root,
                        "type": "NON_EXECUTABLE_HUMAN_REVIEW", "executable": False}
            state.artifacts[artifact_id] = artifact
            return {"artifact": artifact}
        return self._mutate(actor, cmd, "review.prepare", {"task_id": task_id,
                           "decision_id": decision_id}, change)

    def overview(self, actor: Actor) -> dict:
        authorize(actor, READERS)
        with self.store.transaction(actor.tenant_id):
            state = self._load(actor.tenant_id)
            visible = {key: task for key, task in state.tasks.items()
                       if task.intent.scope.subject_id in actor.subjects}
            tasks = []
            for key, task in visible.items():
                item = task.model_dump(mode="json")
                previous = state.decisions.get(task.current_decision_id or "")
                item["current_proof_valid"] = bool(previous and previous.expires_at > self.clock()
                    and previous.basis_hash == task_basis(state, key)
                    and task.status == previous.verdict)
                tasks.append(item)
            case_ids = {key for key, case in state.cases.items() if case.scope.subject_id in actor.subjects}
            return {"revision": state.revision, "state_root": state.state_root,
                    "runtime_id": self.runtime_id, "process_id": self.process_id,
                    "build_commit": self.build_commit, "memory_backend": self.store.production_kind,
                    "principal": actor.model_dump(), "tasks": tasks,
                    "cases": [case.model_dump(mode="json") for key, case in state.cases.items() if key in case_ids],
                    "reports": [report.model_dump(mode="json") for report in state.reports.values()
                                if report.case_id in case_ids],
                    "handoffs": [handoff.model_dump(mode="json") for handoff in state.handoffs.values()
                                 if handoff.case_id in case_ids],
                    "anchor_evidence": [copy.deepcopy(item) for item in state.artifacts.values()
                        if item.get("kind") == "AUDIT_ANCHOR" and item.get("task_id") in visible],
                    "partners": {"base": "JUDGE_VERIFICATION_REQUIRED" if any(
                        item.get("kind") == "AUDIT_ANCHOR" and item.get("task_id") in visible
                        and item.get("verification", {}).get("state") == "VERIFIED"
                        for item in state.artifacts.values()) else "NOT_CLAIMED", "virtuals": "NOT_CLAIMED"},
                    "executable": False}

    def replay(self, actor: Actor, task_id: str) -> dict:
        authorize(actor, READERS)
        with self.store.transaction(actor.tenant_id):
            state = self._load(actor.tenant_id)
            task = self._task(state, actor, task_id)
            decisions = [item for item in state.decisions.values() if item.task_id == task_id]
            decisions.sort(key=lambda item: item.memory_revision)
            return {"task_id": task_id, "current_status": task.status,
                    "decisions": [item.model_dump(mode="json") for item in decisions],
                    "note": "Hash integrity is not proof of real-world truth or a signed model attestation.",
                    "executable": False}

    def case_timeline(self, actor: Actor, case_id: str) -> dict:
        authorize(actor, READERS)
        with self.store.transaction(actor.tenant_id):
            state = self._load(actor.tenant_id)
            self._case(state, actor, case_id)
            return {"case_id": case_id, "versions": [item.model_dump(mode="json")
                    for item in state.case_history[case_id]], "executable": False}

    def prepare_anchor(self, actor: Actor, cmd: Command, task_id: str, decision_id: str) -> dict:
        authorize(actor, REVIEWERS)
        if self.anchor is None:
            raise CaseworkError("BASE_AUDIT_ANCHOR_NOT_CONFIGURED", 503)
        def change(state, seq):
            task = self._task(state, actor, task_id)
            decision = state.decisions.get(decision_id)
            if decision is None or decision.task_id != task_id:
                raise CaseworkError("DECISION_NOT_FOUND", 404)
            plan = self.anchor.plan(decision.proof_root, decision.memory_revision, task.intent.scope.chain_id)
            anchor_id = new_id("anchor")
            record = {"anchor_id": anchor_id, "kind": "AUDIT_ANCHOR", "task_id": task_id,
                      "decision_id": decision_id, "plan": plan, "verification": {"state": "NOT_SUBMITTED"}}
            state.artifacts[anchor_id] = record
            return {"anchor": record, "audit_only": True, "payment_authorized": False}
        return self._mutate(actor, cmd, "anchor.prepare", {"task_id": task_id, "decision_id": decision_id}, change)

    def verify_anchor(self, actor: Actor, cmd: Command, anchor_id: str, tx_hash: str) -> dict:
        authorize(actor, REVIEWERS)
        if self.anchor is None:
            raise CaseworkError("BASE_AUDIT_ANCHOR_NOT_CONFIGURED", 503)
        with self.store.transaction(actor.tenant_id):
            snapshot = self._load(actor.tenant_id)
            artifact = snapshot.artifacts.get(anchor_id)
            if artifact is None or artifact.get("kind") != "AUDIT_ANCHOR":
                raise CaseworkError("ANCHOR_REQUEST_NOT_FOUND", 404)
            self._task(snapshot, actor, artifact["task_id"])
            plan = copy.deepcopy(artifact["plan"])
        verified = self.anchor.verify(plan, tx_hash)  # public RPC reads, outside store lock
        def change(state, seq):
            record = state.artifacts.get(anchor_id)
            if record is None or record["plan"] != plan:
                raise CaseworkError("ANCHOR_REQUEST_CHANGED")
            record["verification"] = verified
            task = state.tasks[record["task_id"]]
            decision = state.decisions[record["decision_id"]]
            return {"anchor": record,
                    "historical_proof": (task.current_decision_id != decision.decision_id
                                          or decision.basis_hash != task_basis(state, task.task_id)),
                    "audit_only": True, "payment_authorized": False}
        return self._mutate(actor, cmd, "anchor.verify", {"task_id": artifact["task_id"],
                            "anchor_id": anchor_id, "tx_hash": tx_hash}, change)
