#!/usr/bin/env python3
"""Start a separate process and prove exact fresh-session recall."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from urllib.request import Request, urlopen

TARGET = "0x1111111111111111111111111111111111111111"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()
    session = f"cli-b-{uuid.uuid4()}"
    request = Request(
        f"{args.base_url.rstrip('/')}/api/decisions",
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
    required = (
        result.get("verdict") == "deny"
        and result.get("cross_session") is True
        and bool(result.get("causal_memory_ids"))
    )
    print(
        json.dumps(
            {"session": session, "fresh_session_gate_passed": required, "decision": result},
            indent=2,
        )
    )
    raise SystemExit(0 if required else 1)


if __name__ == "__main__":
    main()
