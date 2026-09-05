"""Virtuals ACP v2 history reader, pinned to the reviewed CLI response contract.

Only `job history` is executable here. Creating/funding/completing a job stays in
an operator's terminal. A CLI observation is not an independent onchain receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import time

from ..core import CaseworkError, digest
from ..source_models import _validate_cli_home_path
from ..json_boundary import strict_json


def _validate_cli_home(raw_home: str) -> Path:
    """Require an existing, operator-only HOME on one trusted POSIX path.

    The ACP CLI receives this directory as both ``cwd`` and ``HOME``.  Checking
    every path component prevents a writable parent or a symlink swap from
    turning a pinned wrapper into an attacker-controlled configuration/module
    lookup.  The service only reads ACP history; this helper does not create or
    modify the directory.
    """
    try:
        return _validate_cli_home_path(raw_home, require_exists=True)
    except ValueError as exc:
        message = str(exc)
        code = ("ACP_CLI_HOME_NOT_OPERATOR_ONLY" if "not operator-only" in message
                else "ACP_CLI_HOME_UNSAFE_PARENT" if "group/world writable" in message
                else "ACP_CLI_HOME_INVALID")
        raise CaseworkError(code, 503) from exc


class ACPHistoryReader:
    def __init__(self, spec, *, runner=None):
        self.spec = spec
        self.runner = runner or self._execute

    def _execute(self, args):
        home = _validate_cli_home(self.spec.cli_home)
        executable = Path(self.spec.cli_executable)
        if (not executable.is_file() or executable.is_symlink()
                or executable.stat().st_mode & 0o022
                or hashlib.sha256(executable.read_bytes()).hexdigest() != self.spec.cli_sha256):
            raise CaseworkError("ACP_EXECUTABLE_PIN_FAILED",503)
        if os.name != "posix":
            raise CaseworkError("ACP_RUNNER_REQUIRES_POSIX",503)
        proc = None
        try:
            proc = subprocess.Popen([str(executable), *args], stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                cwd=str(home),
                env={"PATH":"/usr/local/bin:/usr/bin:/bin", "HOME":str(home),
                     "LANG":"C.UTF-8", "NO_COLOR":"1"})
            buffers = {"out":bytearray(), "err":bytearray()}
            with selectors.DefaultSelector() as sel:
                sel.register(proc.stdout, selectors.EVENT_READ, "out")
                sel.register(proc.stderr, selectors.EVENT_READ, "err")
                deadline = time.monotonic()+20
                while sel.get_map():
                    if time.monotonic()>deadline:
                        raise CaseworkError("ACP_QUERY_TIMEOUT",504)
                    for key,_ in sel.select(timeout=.2):
                        chunk=os.read(key.fileobj.fileno(),8192)
                        if not chunk:
                            sel.unregister(key.fileobj)
                            continue
                        buffers[key.data].extend(chunk)
                        if sum(map(len,buffers.values()))>512_000:
                            raise CaseworkError("ACP_OUTPUT_TOO_LARGE",502)
            code=proc.wait(timeout=2)
            if code:
                raise CaseworkError("ACP_QUERY_FAILED",502)
            return strict_json(bytes(buffers["out"]), max_bytes=512_000)
        except CaseworkError:
            raise
        except Exception as exc:
            raise CaseworkError("ACP_QUERY_UNAVAILABLE",502) from exc
        finally:
            if proc is not None:
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                for stream in (proc.stdout,proc.stderr):
                    if stream: stream.close()

    def history(self, job_id, requirements):
        if not re.fullmatch(r"[1-9][0-9]{0,29}",job_id):
            raise CaseworkError("ACP_JOB_ID_INVALID",422)
        data=self.runner(["job","history","--job-id",job_id,"--chain-id",str(self.spec.chain_id),"--json"])
        if (not isinstance(data,dict) or data.get("protocol")!="v2"
                or str(data.get("jobId"))!=job_id or data.get("chainId")!=self.spec.chain_id
                or data.get("status") not in {"open","budget_set","funded","submitted","completed","rejected","expired"}
                or not isinstance(data.get("entries"),list)
                or len(data["entries"])>1000 or type(data.get("entryCount")) is not int
                or data.get("entryCount")!=len(data["entries"])):
            raise CaseworkError("ACP_V2_HISTORY_CONTRACT_MISMATCH",502)
        phase_map = {"job.created":"open", "budget.set":"budget_set", "job.funded":"funded",
                     "job.submitted":"submitted", "job.completed":"completed",
                     "job.rejected":"rejected", "job.expired":"expired"}
        derived = "open"
        for entry in data["entries"]:
            if isinstance(entry, dict) and entry.get("kind") == "system":
                event = entry.get("event")
                if isinstance(event, dict) and event.get("type") in phase_map:
                    derived = phase_map[event["type"]]
        if derived != data["status"]:
            raise CaseworkError("ACP_STATUS_HISTORY_MISMATCH", 502)
        wanted=digest("acp-requirements",requirements)
        bound=False
        reviews=[]
        invalid_review=False
        for entry in data["entries"]:
            if not isinstance(entry,dict) or entry.get("kind")!="message": continue
            sender=str(entry.get("from","")).lower()
            content=entry.get("content")
            if not isinstance(content,str) or len(content)>32_000: continue
            try: message=strict_json(content, max_bytes=32_000)
            except ValueError: continue
            if not isinstance(message,dict): continue
            if (sender==self.spec.client_address.lower() and entry.get("contentType")=="requirement"
                    and digest("acp-requirements",message)==wanted):
                bound=True
            if sender==self.spec.provider_address.lower() and message.get("schema_version")=="memoryguard-review/1":
                if (set(message)!={"schema_version","request_hash","recommendation","finding_codes"}
                        or message["request_hash"]!=wanted
                        or message["recommendation"] not in {"KEEP_BLOCKED","MORE_EVIDENCE","REVIEW_COMPLETED"}
                        or not isinstance(message["finding_codes"],list)
                        or len(message["finding_codes"])>12
                        or any(not isinstance(x, str) or x not in {"SOURCE_CONFLICT","INSUFFICIENT_EVIDENCE","STALE_SOURCE",
                             "CONSISTENT_SNAPSHOTS","MANUAL_REVIEW_REQUIRED"} for x in message["finding_codes"])):
                    # Do not let an unrelated provider message mask the more
                    # fundamental missing customer/request binding.  Once the
                    # request is bound, malformed provider review data remains
                    # fail-closed below.
                    invalid_review=True
                    continue
                reviews.append(message)
        if not bound:
            raise CaseworkError("ACP_REQUIREMENTS_NOT_BOUND",409)
        if invalid_review:
            raise CaseworkError("ACP_REVIEW_PAYLOAD_INVALID",502)
        if len({digest("acp-review-message", item) for item in reviews}) > 1:
            raise CaseworkError("ACP_PROVIDER_REVIEW_CONFLICT", 409)
        return {"job_id":job_id,"chain_id":self.spec.chain_id,"protocol":"v2","status":data["status"],
                "request_hash":wanted,"history_digest":digest("acp-history",data),
                "provider_message_bound":bool(reviews),"review":reviews[-1] if reviews else None,
                "complete_review_observed":data["status"]=="completed" and bool(reviews),
                "cost_verified":False,"onchain_receipt_verified":False,
                "provenance":"ACP_CLI_HISTORY_BOUND","authoritative":False,"executable":False}
