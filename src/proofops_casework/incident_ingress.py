"""Signed incident ingress. Authenticated sources may open risk, never resolve it."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time

from .core import CaseworkError, authorize, digest, new_id
from .models import Command, RiskCase
from .source_models import IncidentBody


class IncidentIngress:
    def __init__(self, service, config):
        self.svc = service
        self.specs = {s.source_id: s for s in config.incidents}
        configured_keys = []
        for spec in self.specs.values():
            actor = service.actors.get(spec.actor_id)
            if actor is None:
                raise ValueError("incident source actor missing")
            authorize(actor, {"owner", "investigator"}, spec.scope.subject_id)
            secret = os.environ.get(spec.secret_env, "")
            if len(secret) < 32:
                raise ValueError("incident HMAC secret must be independently configured, >=32 characters")
            if any(hmac.compare_digest(secret.encode(), old.encode()) for old in configured_keys):
                raise ValueError("incident sources require distinct HMAC secrets")
            configured_keys.append(secret)

    def handle(self, source_id, timestamp, delivery_id, signature, raw: bytes):
        spec = self.specs.get(source_id)
        if spec is None or len(raw) > 16_384:
            raise CaseworkError("INCIDENT_NOT_ACCEPTED", 403)
        if (not re.fullmatch(r"[0-9]{10}", timestamp or "")
                or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,80}", delivery_id or "")
                or not re.fullmatch(r"sha256=[0-9a-f]{64}", signature or "")):
            raise CaseworkError("INCIDENT_AUTHENTICATION_FAILED", 401)
        at = self.svc.clock()
        if abs(at.timestamp() - int(timestamp)) > spec.max_clock_skew_seconds:
            raise CaseworkError("INCIDENT_TIMESTAMP_EXPIRED", 401)
        signed = timestamp.encode() + b"." + delivery_id.encode() + b"." + raw
        secret = os.environ.get(spec.secret_env, "")
        if len(secret) < 32:
            raise CaseworkError("INCIDENT_SOURCE_UNAVAILABLE", 503)
        expected = "sha256=" + hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise CaseworkError("INCIDENT_AUTHENTICATION_FAILED", 401)
        try:
            from .json_boundary import strict_json
            body = IncidentBody.model_validate(strict_json(raw, max_bytes=16_384))
        except ValueError as exc:
            raise CaseworkError("INCIDENT_SCHEMA_INVALID", 422) from exc
        actor = self.svc.actors[spec.actor_id]
        key = "incident_" + digest("incident-key", [source_id,delivery_id])[:48]
        cmd = Command(idempotency_key=key, session_id="ingress_"+digest("incident-source",source_id)[:40],
                      expected_revision=0)
        payload = {"source_id":source_id, "delivery_id_hash":digest("delivery",delivery_id),
                   "scope":spec.scope.model_dump(mode="json"), **body.model_dump(mode="json"),
                   "payload_sha256":hashlib.sha256(raw).hexdigest()}
        def insert(state, seq):
            if len(state.cases) >= 500:
                raise CaseworkError("CASE_CAPACITY_REACHED",413)
            case = RiskCase(case_id=new_id("case"), scope=spec.scope, kind=body.kind,
                opened_by=actor.actor_id, opened_seq=seq, evidence_digest=body.evidence_digest)
            state.cases[case.case_id]=case
            state.case_history[case.case_id]=[case.model_copy(deep=True)]
            if self.svc.evidence_desk:
                self.svc.evidence_desk.remember_policy(state,case)
            affected=self.svc._invalidate(state,case.scope,f"case:{case.case_id}:v1","SIGNED_INCIDENT")
            record={"kind":"INCIDENT_RECEIPT","case_id":case.case_id,"source_id":source_id,
                    "source_actor":actor.actor_id,"received_at":at.isoformat(),
                    "payload_sha256":payload["payload_sha256"],"delivery_id_hash":payload["delivery_id_hash"],
                    "authentication":"HMAC_VERIFIED","truth_verified":False,"executable":False}
            state.artifacts[new_id("incident")]=record
            return {"case_id":case.case_id,"affected_tasks":affected,"receipt":record}
        for _ in range(4):
            with self.svc.store.transaction(actor.tenant_id):
                cmd.expected_revision=self.svc._load(actor.tenant_id).revision
            try:
                return self.svc._mutate(actor,cmd,"incident.ingest",payload,insert)
            except CaseworkError as exc:
                if exc.code!="REVISION_CONFLICT": raise
        raise CaseworkError("INCIDENT_CONTENTION",409)
