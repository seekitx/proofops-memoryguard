import copy
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from proofops_casework.core import CaseworkError, new_id
from proofops_casework.models import *
from proofops_casework.service import CaseworkService


class TestStore:
    __test__ = False
    production_kind = "TEST_DOUBLE_NOT_SIBYL"

    def __init__(self):
        self.states = {}
        self.available = True
        self.fail_save = False
        self.lock = threading.RLock()

    @contextmanager
    def transaction(self, tenant_id):
        with self.lock:
            if not self.available:
                raise CaseworkError("MEMORY_BACKEND_UNAVAILABLE", 503)
            yield

    def load(self, tenant_id):
        if not self.available:
            raise CaseworkError("MEMORY_BACKEND_UNAVAILABLE", 503)
        return copy.deepcopy(self.states.get(tenant_id))

    def save(self, tenant_id, state):
        if self.fail_save:
            raise CaseworkError("MEMORY_WRITE_UNCERTAIN", 503)
        self.states[tenant_id] = copy.deepcopy(state)


class Harness:
    def __init__(self, store=None, model=None):
        self.store = store or TestStore()
        self.time = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
        self.actors = {role: Actor(actor_id=f"actor_{role}", tenant_id="tenant_demo",
                       role=role, subjects=["subject_demo"]) for role in
                       ("owner", "investigator", "reviewer", "viewer")}
        self.svc = CaseworkService(self.store, {a.actor_id: a for a in self.actors.values()},
            model=model, clock=lambda: self.time, test_mode=True, build_commit="test-fixture-not-a-git-commit")
        self.session = "session_alpha"
        self.svc.bootstrap(self.actors["owner"], self.command(
            BootstrapCommand, confirmation="CREATE_CASEWORK_WORKSPACE", revision=0))

    def command(self, cls=Command, revision=None, key=None, **kwargs):
        if revision is None:
            revision = self.store.load("tenant_demo").revision
        return cls(idempotency_key=key or new_id("request"), session_id=self.session,
                   expected_revision=revision, **kwargs)

    @staticmethod
    def scope(number=1):
        return Scope(subject_id="subject_demo", target="0x" + f"{number:040x}", method="transfer")

    def baseline(self, number=1, limit=500000, **extra):
        return self.svc.set_baseline(self.actors["owner"], self.command(BaselineCommand,
            scope=self.scope(number), limit_minor=limit,
            expires_at=extra.get("expires_at", self.time + timedelta(days=1))))

    def task(self, number=1, amount=420000, depends=None):
        return self.svc.register_task(self.actors["owner"], self.command(TaskCommand,
            intent=Intent(scope=self.scope(number), amount_minor=amount), depends_on=depends or []))

    def risk(self, number=1, kind="dispute"):
        return self.svc.open_case(self.actors["owner"], self.command(OpenCaseCommand,
            scope=self.scope(number), kind=kind, evidence_digest="1" * 64))

    def investigate(self, case_id):
        return self.svc.investigate(self.actors["investigator"], self.command(), case_id)

    def handoff(self, case_id, report_id):
        response = self.svc.handoff(self.actors["investigator"], self.command(HandoffCommand,
            report_id=report_id, reviewer_id=self.actors["reviewer"].actor_id), case_id)
        hid = response["handoff"]["handoff_id"]
        self.svc.accept_handoff(self.actors["reviewer"], self.command(), hid)
        return hid

    def resolve(self, case_id):
        report_id = self.investigate(case_id)["report"]["report_id"]
        handoff_id = self.handoff(case_id, report_id)
        return self.svc.resolve(self.actors["reviewer"], self.command(ResolveCommand,
            handoff_id=handoff_id, resolution="remediation_verified", evidence_digest="2" * 64), case_id)

    def evaluate(self, task_id, review=False):
        return self.svc.evaluate(self.actors["reviewer" if review else "owner"],
                                 self.command(), task_id, reconsider=review)["decision"]
