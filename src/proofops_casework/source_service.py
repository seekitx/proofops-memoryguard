"""Durable evidence acquisition, bounded missions and case-specific resolution gates.

Network reads happen outside the aggregate lock. A persisted request prevents silent
retry after crash/uncertain network outcomes. This is at-most-one attempt per command,
not an exactly-once guarantee for remote services. No money is moved.
"""
from __future__ import annotations

import copy
from datetime import timedelta

from .core import CaseworkError, authorize, digest, new_id, scope_key
from .models import Command, HandoffCommand
from .source_models import CollectCommand, ConnectorConfig, MissionCommand
from .source_guard import effective_policy, has_obligations, remember_policy
from .source_state import (current_receipts, evidence_basis, evidence_heads, parsed_time,
                            source_conflicts, source_key)
from .connectors.github_issue import GitHubIssueSource
from .connectors.base_transaction import BaseTransactionSource


class EvidenceDesk:
    def __init__(self, service, config: ConnectorConfig, *, adapters=None):
        self.svc = service
        self.config = config
        self.specs = {s.source_id: s for s in config.sources}
        self.adapters = adapters or {"github_issue": GitHubIssueSource(), "base_transaction": BaseTransactionSource()}
        self.config_hash = digest("connectors-config", config.model_dump(mode="json"))
        service.evidence_desk = self

    def _spec(self, actor, source_id, scope):
        spec = self.specs.get(source_id)
        if (spec is None or spec.tenant_id != actor.tenant_id
                or scope.subject_id not in actor.subjects or scope.subject_id not in spec.subjects):
            raise CaseworkError("SOURCE_NOT_ALLOWED", 403)
        return spec

    def policy(self, state, case):
        return next((p for p in self.config.policies if p.tenant_id == state.tenant_id
                     and scope_key(p.scope) == scope_key(case.scope)), None)

    def remember_policy(self, state, case, source_ids=()):
        remember_policy(state, case, self.policy(state, case), source_ids)

    def context(self, state, case_id, at):
        case = state.cases[case_id]
        policy = self.policy(state, case)
        floor = effective_policy(state, case, policy)
        receipts, rejected = current_receipts(state, case_id, at, self.specs)
        conflicts = source_conflicts(receipts)
        got = {x["source_id"] for x in receipts}
        required = set(floor["required_sources"])
        relevant = [r for r in receipts if r["source_id"] in required] if required else receipts
        groups = {r["independence_group"] for r in relevant}
        # Complete coverage means every current head is usable and mutually
        # consistent.  A stale/failed head or conflicting claim is never allowed
        # to proceed as merely "optional" evidence after it entered the case.
        ready = (not rejected and not conflicts and not (required - got)
                 and len(groups) >= floor["min_independence_groups"])
        signals = []
        for r in receipts:
            facts = r["facts"]
            if facts.get("state") == "open":
                signals.append({"source_id": r["source_id"], "code": "ISSUE_REMAINS_OPEN"})
            if facts.get("transaction_succeeded") is False:
                signals.append({"source_id": r["source_id"], "code": "TRANSACTION_REVERTED"})
        signals += [{"source_id": key, "code": "MISSING_REQUIRED_SOURCE"} for key in sorted(required-got)]
        signals += [{"source_id": item["source_id"], "code": item["reason"]} for item in rejected]
        signals += [{"source_id": item["source_ids"][0], "code": "SOURCE_CONFLICT",
                     "conflict_id": digest("source-conflict", item)} for item in conflicts]
        result = {"case_id": case_id, "case_version": case.version,
            "review_signals": signals,
            "required_sources": sorted(required), "missing_sources": sorted(required - got),
            "declared_independence_groups": len(groups), "coverage_complete": ready,
            "source_conflicts": conflicts,
            "resolution_requires_sources": bool(required or policy),
            "source_obligations": floor,
            "policy_hash": digest("scope-evidence-policy", policy.model_dump(mode="json") if policy else {}),
            "receipts": [{"receipt_id": r["receipt_id"], "source_id": r["source_id"],
                          "receipt_root": r["receipt_root"], "facts": r["facts"],
                          "expires_at": r["expires_at"], "provenance": r["provenance"]}
                         for r in receipts], "rejected": rejected,
            "authority": False,
            "scope": "Configured groups are declarations, not proof of independent people or fact truth"}
        result["bundle_root"] = digest("evidence-bundle", result)
        return result

    def report_context(self, state, case_id, at):
        # Preserve old no-source reports in explicitly manual scopes. Once a source
        # is used, its current head enters the basis even if it subsequently fails.
        if not self.policy(state, state.cases[case_id]) and not has_obligations(state, case_id):
            return None
        return self.context(state, case_id, at)

    def validate_report(self, state, case, report, at):
        value = self.report_context(state, case.case_id, at)
        if value is None:
            return
        events = [e for e in report.trace if e.get("tool") == "evidence.inspect"]
        if (len(events) != 1 or events[0].get("output_hash") != digest("tool-output", value)):
            raise CaseworkError("SOURCE_REPORT_STALE")
        if value["source_conflicts"]:
            raise CaseworkError("SOURCE_CONFLICT")
        if not value["coverage_complete"]:
            raise CaseworkError("SOURCE_COVERAGE_REQUIRED")

    def resolution(self, state, case, evidence_digest, at):
        value = self.report_context(state, case.case_id, at)
        if value is None:
            return
        if value["source_conflicts"]:
            raise CaseworkError("SOURCE_CONFLICT")
        if not value["coverage_complete"] or evidence_digest != value["bundle_root"]:
            raise CaseworkError("CURRENT_EVIDENCE_BUNDLE_REQUIRED")

    def dossier(self, actor, case_id):
        authorize(actor, {"owner", "investigator", "reviewer", "viewer"})
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            self.svc._case(state, actor, case_id)
            result = self.context(state, case_id, self.svc.clock())
            attempts = [a for a in state.artifacts.values() if a.get("kind") == "SOURCE_REQUEST"
                        and a.get("case_id") == case_id]
            return result | {"revision": state.revision, "acquisition_attempts": len(attempts),
                "request_states": [{"request_id": a["request_id"], "state": a["state"],
                                    "source_id": a["source_id"]} for a in attempts],
                "executable": False}

    def export_report(self, actor, report_id):
        """Explicit authenticated export; no automatic public publication."""
        authorize(actor, {"owner", "investigator", "reviewer", "viewer"})
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            report = state.reports.get(report_id)
            if report is None:
                raise CaseworkError("REPORT_NOT_FOUND", 404)
            case = self.svc._case(state, actor, report.case_id)
            bundle = state.artifacts.get(digest("report-sources-key", report_id))
            current = True
            try:
                self.svc._valid_report(state, case, report_id)
            except CaseworkError:
                current = False
            return {"schema_version": "casework-report-export/1", "report": report.model_dump(mode="json"),
                    "source_snapshot": copy.deepcopy(bundle), "current": current,
                    "scope": "Hashes verify internal consistency, not external truth or independently authenticated authorship",
                    "executable": False}

    def catalog(self, actor):
        authorize(actor, {"owner", "investigator", "reviewer", "viewer"})
        visible = [s for s in self.specs.values() if s.tenant_id == actor.tenant_id
                   and set(s.subjects) & set(actor.subjects)]
        return {"sources": [{"source_id": s.source_id, "kind": s.kind,
                    "independence_group": s.independence_group, "ttl_seconds": s.ttl_seconds,
                    "max_attempts_per_case": s.max_attempts_per_case} for s in visible],
                "virtuals_configured": bool(self.config.virtuals and
                    self.config.virtuals.tenant_id == actor.tenant_id and
                    set(self.config.virtuals.subjects) & set(actor.subjects)),
                "read_only_connectors": True, "partner_bonus_claimed": False, "executable": False}

    def collect(self, actor, cmd: CollectCommand, case_id):
        authorize(actor, {"owner", "investigator"})
        with self.svc.store.transaction(actor.tenant_id):
            snapshot = self.svc._load(actor.tenant_id)
            case = self.svc._case(snapshot, actor, case_id).model_copy(deep=True)
        spec = self._spec(actor, cmd.source_id, case.scope)
        adapter = self.adapters[spec.kind]
        resource = adapter.resource(spec, cmd.resource, case.scope)
        payload = {"case_id": case_id, "source_id": spec.source_id,
                   "resource": resource, "force_refresh": cmd.force_refresh}
        request_id = "fetch_" + digest("fetch-id", [actor.tenant_id, actor.actor_id, cmd.idempotency_key])[:32]
        spec_hash = digest("source-spec", spec.model_dump(mode="json"))

        def reserve(state, seq):
            current = self.svc._case(state, actor, case_id)
            if current.status != "OPEN" or current.version != case.version:
                raise CaseworkError("SOURCE_CASE_CHANGED")
            self.remember_policy(state, current, [spec.source_id])
            receipts, _ = current_receipts(state, case_id, self.svc.clock(), self.specs)
            cached = next((r for r in receipts if r["source_id"] == spec.source_id and r["resource"] == resource), None)
            if cached and not cmd.force_refresh:
                return {"request_id": request_id, "state": "CACHE_HIT", "receipt": cached,
                        "external_calls": 0, "memory_saved_fetch": True}
            count = sum(a.get("kind") == "SOURCE_REQUEST" and a.get("case_id") == case_id
                        and a.get("source_id") == spec.source_id for a in state.artifacts.values())
            if count >= spec.max_attempts_per_case:
                raise CaseworkError("SOURCE_READ_BUDGET_EXHAUSTED", 429)
            item = {"kind": "SOURCE_REQUEST", "request_id": request_id, "case_id": case_id,
                    "case_version": current.version, "source_id": spec.source_id,
                    "source_spec_hash": spec_hash, "resource": resource,
                    "state": "PENDING", "reserved_at": self.svc.clock().isoformat(), "actor_id": actor.actor_id}
            state.artifacts[request_id] = item
            state.artifacts[source_key(case_id, spec.source_id)] = {
                "kind": "SOURCE_HEAD", "case_id": case_id, "case_version": current.version,
                "source_id": spec.source_id, "request_id": request_id, "state": "PENDING"}
            return {"request_id": request_id, "state": "PENDING", "external_calls": 0}

        reservation = self.svc._mutate(actor, cmd, "source.reserve", payload, reserve)
        if reservation["state"] == "CACHE_HIT":
            return reservation
        if reservation.get("replayed"):
            # No blind resend. A crash leaves a visible PENDING record. Use a new
            # command to refresh after inspection, never claim the old read failed.
            with self.svc.store.transaction(actor.tenant_id):
                state = self.svc._load(actor.tenant_id)
                self.svc._case(state, actor, case_id)
                item = copy.deepcopy(state.artifacts[request_id])
                receipt = state.artifacts.get(item.get("receipt_id", ""))
                return {"request": item, "receipt": copy.deepcopy(receipt), "replayed": True,
                        "historical_only": True, "revision": state.revision, "executable": False}
        observed, error = None, None
        try:
            from .observations import bounded_observation
            observed = bounded_observation(adapter.fetch(spec, resource, case.scope, self.svc.clock()))
        except CaseworkError as exc:
            error = exc.code
        except Exception:
            error = "SOURCE_READ_FAILED"
        finished = self.svc.clock()
        finish_cmd = Command(idempotency_key="done_" + request_id[6:], session_id=cmd.session_id,
                             expected_revision=reservation["revision"])
        def finish(state, seq):
            pending = state.artifacts.get(request_id)
            if pending is None or pending["state"] != "PENDING":
                raise CaseworkError("SOURCE_REQUEST_NOT_PENDING")
            current = self.svc._case(state, actor, case_id)
            head = state.artifacts.get(source_key(case_id, spec.source_id), {})
            stale = (current.version != case.version or current.status != "OPEN"
                     or head.get("request_id") != request_id)
            pending["state"] = "STALE" if stale else "FAILED" if error else "OBSERVED"
            pending["finished_at"] = finished.isoformat()
            pending["error"] = error
            receipt = None
            if not error:
                receipt_id = new_id("source")
                receipt = {"kind": "SOURCE_RECEIPT", "receipt_id": receipt_id,
                    "case_id": case_id, "case_version": case.version, "source_id": spec.source_id,
                    "source_spec_hash": spec_hash, "independence_group": spec.independence_group,
                    "resource": resource, "fetched_at": finished.isoformat(),
                    "expires_at": (finished + timedelta(seconds=spec.ttl_seconds)).isoformat(),
                    **observed, "authoritative": False, "executable": False}
                receipt["receipt_root"] = digest("source-receipt", receipt)
                state.artifacts[receipt_id] = receipt
                pending["receipt_id"] = receipt_id
            if head.get("request_id") == request_id:
                head["state"] = pending["state"]
                if receipt:
                    head["receipt_id"] = receipt["receipt_id"]
            return {"request_id": request_id, "state": pending["state"], "error": error,
                    "receipt": receipt, "external_calls": observed["external_calls"] if observed else None,
                    "no_external_retry": True}
        # Finish the reserved read against current workspace, not the global revision
        # observed before a slow network call. A case-specific stale check lives above.
        for _ in range(4):
            with self.svc.store.transaction(actor.tenant_id):
                fresh = self.svc._load(actor.tenant_id)
                finish_cmd.expected_revision = fresh.revision
            try:
                return self.svc._mutate(actor, finish_cmd, "source.finish", {"case_id": case_id,
                    "request_id": request_id, "result_digest": digest("source-result", [observed,error])}, finish)
            except CaseworkError as exc:
                if exc.code != "REVISION_CONFLICT":
                    raise
        raise CaseworkError("SOURCE_FINISH_CONTENTION", 409)

    def mission(self, actor, cmd, case_id):
        """Bounded resumable operator-triggered sequence, NOT autonomous risk resolution."""
        authorize(actor, {"investigator"})
        if len({q.source_id for q in cmd.queries}) != len(cmd.queries):
            raise CaseworkError("MISSION_DUPLICATE_SOURCE", 422)
        payload = {"case_id": case_id, "queries": [q.model_dump(mode="json") for q in cmd.queries],
                   "reviewer_id": cmd.reviewer_id}
        mission_id = "mission_" + digest("mission-id", [actor.tenant_id, actor.actor_id,
                                                       cmd.idempotency_key])[:40]
        def plan(state, seq):
            case = self.svc._case(state, actor, case_id)
            if case.status != "OPEN":
                raise CaseworkError("CASE_NOT_OPEN")
            hashes = {}
            for query in cmd.queries:
                spec = self._spec(actor, query.source_id, case.scope)
                self.adapters[spec.kind].resource(spec, query.resource, case.scope)
                hashes[spec.source_id] = digest("source-spec", spec.model_dump(mode="json"))
            if cmd.reviewer_id:
                reviewer = self.svc.actors.get(cmd.reviewer_id)
                if (reviewer is None or reviewer.actor_id in {actor.actor_id, case.opened_by}
                        or reviewer.tenant_id != actor.tenant_id or reviewer.role != "reviewer"
                        or case.scope.subject_id not in reviewer.subjects):
                    raise CaseworkError("MISSION_REVIEWER_NOT_ALLOWED", 403)
            self.remember_policy(state, case, hashes)
            record = {"kind": "EVIDENCE_MISSION", "mission_id": mission_id,
                      "origin_session_id": cmd.session_id,
                      "origin_idempotency_key": cmd.idempotency_key,
                      "case_id": case_id, "case_version": case.version, "created_seq": seq,
                      "planned_queries": payload["queries"], "reviewer_id": cmd.reviewer_id,
                      "source_policy_hashes": hashes, "operator_id": actor.actor_id,
                      "executable": False, "resolution_performed": False}
            state.artifacts[mission_id] = record
            return {"mission": record}
        self.svc._mutate(actor, cmd, "mission.plan", payload, plan)
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            case = self.svc._case(state, actor, case_id)
            record = state.artifacts[mission_id]
            if case.status != "OPEN" or case.version != record["case_version"]:
                raise CaseworkError("MISSION_CASE_CHANGED")
            for source_id, spec_hash in record["source_policy_hashes"].items():
                spec = self._spec(actor, source_id, case.scope)
                if digest("source-spec", spec.model_dump(mode="json")) != spec_hash:
                    raise CaseworkError("MISSION_SOURCE_POLICY_CHANGED")
            revision = state.revision
        # Step keys and the plan are durably bound to exact input. A changed query
        # list/reviewer requires a new mission key, not a silent continuation.
        outputs = []
        for index, query in enumerate(cmd.queries):
            subkey = "mission_" + digest("mission-step", [cmd.idempotency_key, index])[:40]
            with self.svc.store.transaction(actor.tenant_id):
                state = self.svc._load(actor.tenant_id)
                self.svc._case(state, actor, case_id)
                revision = state.revision if outputs else revision
            result = self.collect(actor, CollectCommand(idempotency_key=subkey, session_id=cmd.session_id,
                expected_revision=revision, source_id=query.source_id, resource=query.resource), case_id)
            outputs.append(result)
            receipt = result.get("receipt")
            ok = result.get("state") in {"OBSERVED", "CACHE_HIT"} or result.get("request",{}).get("state") == "OBSERVED"
            if not ok or not receipt:
                return {"mission_id": mission_id, "stage": "COLLECTION_INCOMPLETE", "steps": outputs,
                        "executable": False, "resolution_performed": False}
            revision = result["revision"]
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            receipts, _ = current_receipts(state, case_id, self.svc.clock(), self.specs)
            if not {q.source_id for q in cmd.queries} <= {r["source_id"] for r in receipts}:
                return {"stage": "SOURCES_STALE", "mission_id": mission_id, "steps": outputs,
                        "resolution_performed": False, "executable": False}
        # Fresh read is deliberate: investigate rechecks a relevant memory basis.
        revision = self.svc.overview(actor)["revision"]
        report = self.svc.investigate(actor, Command(idempotency_key="mission_" + digest("mission-report",cmd.idempotency_key)[:40],
            session_id=cmd.session_id, expected_revision=revision), case_id)
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            case = self.svc._case(state, actor, case_id)
            try:
                self.svc._valid_report(state, case, report["report"]["report_id"])
            except CaseworkError:
                return {"mission_id": mission_id, "stage": "REPORT_STALE", "steps": outputs, "report": report,
                        "resolution_performed": False, "executable": False,
                        "next_step": "Inspect changes and start a new mission idempotency key"}
        handoff = None
        if cmd.reviewer_id:
            revision = self.svc.overview(actor)["revision"]
            handoff = self.svc.handoff(actor, HandoffCommand(idempotency_key="mission_"+digest("mission-handoff",cmd.idempotency_key)[:40],
                session_id=cmd.session_id, expected_revision=revision,
                report_id=report["report"]["report_id"], reviewer_id=cmd.reviewer_id), case_id)
        return {"mission_id": mission_id, "stage": "HANDED_OFF" if handoff else "INVESTIGATED", "steps": outputs,
                "report": report, "handoff": handoff, "resolution_performed": False, "executable": False}


    def list_missions(self, actor):
        authorize(actor, {"owner", "investigator", "reviewer", "viewer"})
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            plans = [value for value in state.artifacts.values()
                     if value.get("kind") == "EVIDENCE_MISSION"
                     and value.get("case_id") in state.cases
                     and state.cases[value["case_id"]].scope.subject_id in actor.subjects]
            plans.sort(key=lambda p: (p.get("created_seq", 0), p["mission_id"]), reverse=True)
            return {"missions": [{"mission_id": p["mission_id"], "case_id": p["case_id"],
                    "operator_id": p["operator_id"], "case_version": p["case_version"],
                    "resume_supported": bool(p.get("origin_idempotency_key"))} for p in plans],
                    "revision": state.revision, "executable": False}

    def inspect_mission(self, actor, mission_id):
        authorize(actor, {"owner", "investigator", "reviewer", "viewer"})
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            record = state.artifacts.get(mission_id)
            if not record or record.get("kind") != "EVIDENCE_MISSION":
                raise CaseworkError("MISSION_NOT_FOUND", 404)
            case = self.svc._case(state, actor, record["case_id"])
            steps = []
            origin = record.get("origin_idempotency_key")
            for index, query in enumerate(record["planned_queries"]):
                if origin:
                    subkey = "mission_" + digest("mission-step", [origin, index])[:40]
                    fetch_id = "fetch_" + digest("fetch-id", [actor.tenant_id, record["operator_id"], subkey])[:32]
                    request = state.artifacts.get(fetch_id)
                    idem = state.idempotency.get(digest("idempotency-key", [record["operator_id"], subkey]))
                    stage = request.get("state") if request else (idem["response"].get("state") if idem else "NOT_STARTED")
                else:
                    stage = "LEGACY_IDENTITY_UNAVAILABLE"
                steps.append({"index": index, "source_id": query["source_id"], "state": stage})
            same_case = case.version == record["case_version"] and case.status == "OPEN"
            config_matches = all(sid in self.specs and
                digest("source-spec", self.specs[sid].model_dump(mode="json")) == value
                for sid, value in record["source_policy_hashes"].items())
            report = None
            attempt = None
            if origin:
                report_key = "mission_" + digest("mission-report", origin)[:40]
                attempt = state.artifacts.get("investigation_" + digest("investigation-attempt", [record["operator_id"], report_key])[:40])
                row = state.idempotency.get(digest("idempotency-key", [record["operator_id"], report_key]))
                if row:
                    report = row["response"].get("report")
            report_current = False
            if report:
                try:
                    self.svc._valid_report(state, case, report["report_id"])
                    report_current = True
                except CaseworkError:
                    pass
            safe_plan = {k: copy.deepcopy(v) for k, v in record.items()
                         if k not in {"origin_session_id", "origin_idempotency_key"}}
            return {"mission": safe_plan, "steps": steps, "case_current": same_case,
                    "config_matches": config_matches, "report_id": report["report_id"] if report else None,
                    "report_current": report_current, "revision": state.revision,
                    "resume_supported": bool(origin and record.get("origin_session_id")),
                    "investigation_state": attempt.get("state") if attempt else "NO_RESERVED_MODEL_ATTEMPT",
                    "executable": False, "resolution_performed": False}

    def resume_mission(self, actor, cmd, mission_id):
        authorize(actor, {"investigator"})
        with self.svc.store.transaction(actor.tenant_id):
            state = self.svc._load(actor.tenant_id)
            record = copy.deepcopy(state.artifacts.get(mission_id))
            if not record or record.get("kind") != "EVIDENCE_MISSION":
                raise CaseworkError("MISSION_NOT_FOUND", 404)
            self.svc._case(state, actor, record["case_id"])
            if record["operator_id"] != actor.actor_id:
                raise CaseworkError("MISSION_OWNER_MISMATCH", 403)
            if not record.get("origin_idempotency_key") or not record.get("origin_session_id"):
                raise CaseworkError("LEGACY_MISSION_REQUIRES_NEW_PLAN", 409)
        def signal(current, seq):
            live = current.artifacts.get(mission_id)
            if live != record:
                raise CaseworkError("MISSION_PLAN_CHANGED", 409)
            case = self.svc._case(current, actor, record["case_id"])
            if case.status != "OPEN" or case.version != record["case_version"]:
                raise CaseworkError("MISSION_CASE_CHANGED", 409)
            return {"mission_id": mission_id, "resume_signal_recorded": True,
                    "session_changed": cmd.session_id != record["origin_session_id"],
                    "no_restart_claim": True}
        resumed = self.svc._mutate(actor, cmd, "mission.resume",
                    {"case_id": record["case_id"], "mission_id": mission_id}, signal)
        revision = self.svc.overview(actor)["revision"]
        original = MissionCommand(session_id=record["origin_session_id"],
            idempotency_key=record["origin_idempotency_key"], expected_revision=revision,
            queries=record["planned_queries"], reviewer_id=record["reviewer_id"])
        result = self.mission(actor, original, record["case_id"])
        return result | {"resume_signal": resumed, "logical_request_reused": True}
