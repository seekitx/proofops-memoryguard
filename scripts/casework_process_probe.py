#!/usr/bin/env python3
"""Actual official-SDK separate-process and disposable-store deletion probe.

No public service is restarted. No real/user DB is touched. Only a newly allocated
TemporaryDirectory is used; this output cannot substitute for the required video.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from proofops_casework.core import CaseworkError,new_id
from proofops_casework.models import *
from proofops_casework.service import CaseworkService
from proofops_casework.store import SibylWorkspaceStore


def worker(args):
    actor=Actor(actor_id="probe_owner",tenant_id="probe_tenant",role="owner",subjects=["probe_subject"])
    store=SibylWorkspaceStore(Path(args.db))
    svc=CaseworkService(store,{actor.actor_id:actor},build_commit=args.commit)
    def cmd(cls=Command,**kwargs):
        state=store.load(actor.tenant_id)
        return cls(idempotency_key=new_id("request"),session_id=new_id("session"),
                   expected_revision=state.revision if state else 0,**kwargs)
    try:
        if args.phase=="a":
            svc.bootstrap(actor,cmd(BootstrapCommand,confirmation="CREATE_CASEWORK_WORKSPACE"))
            scope=Scope(subject_id="probe_subject",target="0x"+"1"*40,method="transfer")
            svc.set_baseline(actor,cmd(BaselineCommand,scope=scope,limit_minor=500000,
                                      expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
            result=svc.register_task(actor,cmd(TaskCommand,intent=Intent(scope=scope,amount_minor=420000)))
            svc.open_case(actor,cmd(OpenCaseCommand,scope=scope,kind="dispute",evidence_digest="a"*64))
            print(json.dumps(result));return 0
        result=svc.evaluate(actor,cmd(),args.task);print(json.dumps(result));return 0
    except CaseworkError as exc:
        print(json.dumps({"error":exc.code,"status":exc.status,"executable":False}));return 2
    finally: store.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--phase",choices=["a","b"])
    parser.add_argument("--db");parser.add_argument("--task");parser.add_argument("--commit",default="local-uncommitted")
    parser.add_argument("--out",type=Path);args=parser.parse_args()
    if args.phase:return worker(args)
    if args.out is None:parser.error("--out is required")
    if importlib.util.find_spec("sibyl_memory_client") is None:
        raise SystemExit("UNRUN: official sibyl-memory-client is not installed; no fallback is allowed")
    with tempfile.TemporaryDirectory(prefix="memoryguard-official-probe-") as directory:
        db=Path(directory)/"temporary-sibyl.db"
        base=[sys.executable,str(Path(__file__).resolve()),"--db",str(db),"--commit",args.commit]
        a=subprocess.run(base+["--phase","a"],capture_output=True,text=True,check=True)
        first=json.loads(a.stdout);task=first["task"]["task_id"]
        b=subprocess.run(base+["--phase","b","--task",task],capture_output=True,text=True,check=True)
        second=json.loads(b.stdout);da,dbb=first["decision"],second["decision"]
        checks={"same_action":da["action_fingerprint"]==dbb["action_fingerprint"],
                "different_runtime":da["runtime_id"]!=dbb["runtime_id"],
                "different_pid":da["process_id"]!=dbb["process_id"],
                "same_build":da["build_commit"]==dbb["build_commit"],
                "ready_to_deny":da["verdict"]=="READY" and dbb["verdict"]=="DENY",
                "changed_tool":da["tool"]!=dbb["tool"],"causal_blocker":bool(dbb["active_blockers"])}
        # All workers have exited. Removal is confined to our disposable directory.
        for suffix in ["","-wal","-shm"]:Path(str(db)+suffix).unlink(missing_ok=True)
        deleted=subprocess.run(base+["--phase","b","--task",task],capture_output=True,text=True)
        deletion=json.loads(deleted.stdout)
        checks["deleted_memory_stops_core"]=deleted.returncode==2 and deletion.get("error")=="MEMORY_WORKSPACE_MISSING"
        report={"backend":"OFFICIAL_SIBYL","synthetic_data":True,"real_model":False,
                "public_deployment":False,"continuous_video":False,"checks":checks,
                "session_a":first,"session_b":second,"deletion":deletion}
        args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2))
        print(json.dumps(checks,indent=2));return 0 if all(checks.values()) else 1

if __name__=="__main__":raise SystemExit(main())
