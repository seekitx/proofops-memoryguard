#!/usr/bin/env python3
"""Start a separate process and prove exact fresh-session recall."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

TARGET = "0x1111111111111111111111111111111111111111"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--session-a-evidence", type=Path, required=True)
    args = parser.parse_args()
    session = f"cli-b-{uuid.uuid4()}"
    request = Request(
        f"{args.base_url.rstrip('/')}/api/agent/runs",
        data=json.dumps(
            {
                "subject_id": args.subject,
                "session_id": session,
                "chain_id": 84532,
                "target": TARGET,
                "method": "payInvoice",
                "amount_usd": 4200,
                "evidence_mode": "demo_fixture",
                "idempotency_key": (
                    "cli-after_"
                    + hashlib.sha256(f"{args.subject}:{session}".encode()).hexdigest()[:32]
                ),
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:  # noqa: S310 - operator-supplied demo URL
        result = json.loads(response.read())
    before = json.loads(args.session_a_evidence.read_text(encoding="utf-8"))
    before_run = before.get("agent_before") or {}
    dispute_id = (before.get("dispute") or {}).get("observation_id")
    required = (
        before_run.get("verdict") == "ready"
        and before_run.get("state") == "await_finalize"
        and result.get("verdict") == "deny"
        and result.get("cross_session") is True
        and bool(dispute_id)
        and dispute_id in result.get("causal_memory_ids", [])
        and before.get("action_fingerprint") == result.get("action_fingerprint")
        and before.get("runtime_instance_id") != result.get("runtime_instance_id")
        and before.get("session") != session
    )
    print(
        json.dumps(
            {
                "session": session,
                "runtime_instance_id": result.get("runtime_instance_id"),
                "action_fingerprint": result.get("action_fingerprint"),
                "fresh_session_gate_passed": required,
                "session_a_runtime_instance_id": before.get("runtime_instance_id"),
                "same_action_fingerprint": (
                    before.get("action_fingerprint") == result.get("action_fingerprint")
                ),
                "different_runtime_instance": (
                    before.get("runtime_instance_id") != result.get("runtime_instance_id")
                ),
                "exact_dispute_recalled": dispute_id in result.get("causal_memory_ids", []),
                "agent_after": result,
            },
            indent=2,
        )
    )
    raise SystemExit(0 if required else 1)


if __name__ == "__main__":
    main()
