#!/usr/bin/env python3
"""Print an inspected ACP v2 create command; never execute it or fund a job.

Save the authenticated partner-review plan JSON, then:
python scripts/casework_acp_handoff.py --plan /private/plan.json
"""
import argparse
import json
from pathlib import Path
import shlex
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from proofops_casework.core import digest
from proofops_casework.source_state import parsed_time
from proofops_casework.core import now


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",type=Path,required=True)
    args=p.parse_args()
    if args.plan.stat().st_size>64_000: raise SystemExit("Plan too large")
    obj=json.loads(args.plan.read_text())
    plan=obj.get("plan",obj)
    required={"requirements","request_hash","provider_address","offering_name","chain_id","expires_at"}
    if not required.issubset(plan) or plan.get("kind")!="ACP_REVIEW_PLAN": raise SystemExit("Invalid plan")
    import re
    if (not re.fullmatch(r"0x[0-9a-fA-F]{40}",plan["provider_address"])
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{1,95}",plan["offering_name"])
        or plan["chain_id"] not in {8453,84532}
        or parsed_time(plan["expires_at"])<=now()
        or plan["request_hash"]!=digest("acp-requirements",plan["requirements"])):
        raise SystemExit("Expired or malformed plan")
    argv=["acp","client","create-job","--provider",plan["provider_address"],
          "--offering-name",plan["offering_name"],"--chain-id",str(plan["chain_id"]),
          "--requirements",json.dumps(plan["requirements"],separators=(",",":")),"--json"]
    print("NOT EXECUTED. Review offering price/subscriptions/wallet/network in the official CLI first.")
    print("The local budget field does NOT enforce third-party spending. Do not fund above your limit.")
    print(shlex.join(argv))
    print("Provider reply schema (request_hash must match):")
    print(json.dumps({"schema_version":"memoryguard-review/1","request_hash":plan["request_hash"],
        "recommendation":"MORE_EVIDENCE","finding_codes":["MANUAL_REVIEW_REQUIRED"]},indent=2))
    print("The provider must send this structured JSON as an ACP message and submit the deliverable.")
    print("Creation, funding, completion and signing are separate human actions. Server only queries job history.")

if __name__=="__main__": main()
