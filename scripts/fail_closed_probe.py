#!/usr/bin/env python3
"""Capture a fail-closed API response from an isolated runtime without Sibyl.

Start a separate development API environment where the official Sibyl dependency is
intentionally unavailable, then point this script at that API. This script does not
remove packages or mutate the normal demo environment.
"""

from __future__ import annotations

import argparse
import json
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TARGET = "0x1111111111111111111111111111111111111111"


def request_json(request: Request) -> tuple[int, dict[str, object]]:
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--subject", default=f"deletion-{uuid.uuid4()}")
    args = parser.parse_args()

    health_status, health = request_json(
        Request(f"{args.base_url.rstrip('/')}/health/ready", method="GET")
    )
    payload = {
        "subject_id": args.subject,
        "session_id": f"deletion-{uuid.uuid4()}",
        "chain_id": 84532,
        "target": TARGET,
        "method": "payInvoice",
        "amount_usd": 4200,
        "evidence_mode": "demo_fixture",
        "idempotency_key": f"deletion-{uuid.uuid4()}",
    }

    def post(path: str) -> tuple[int, dict[str, object]]:
        return request_json(
            Request(
                f"{args.base_url.rstrip('/')}{path}",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        )

    decision_status, decision = post("/api/decisions")
    run_status, run = post("/api/agent/runs")
    memory = health.get("memory") or {}
    if not isinstance(memory, dict):
        memory = {}
    fail_closed_response_observed = (
        health_status == 503
        and health.get("status") == "degraded"
        and memory.get("backend") == "sibyl_unavailable"
        and memory.get("production_eligible") is False
        and decision_status == 503
        and decision.get("error") == "MEMORY_BACKEND_UNAVAILABLE"
        and decision.get("executable") is False
        and run_status == 503
        and run.get("error") == "MEMORY_BACKEND_UNAVAILABLE"
        and run.get("executable") is False
    )
    print(
        json.dumps(
            {
                "fail_closed_response_observed": fail_closed_response_observed,
                "deletion_gate_claimed": False,
                "evidence_note": (
                    "This output proves only that the observed runtime failed closed while "
                    "its Sibyl Adapter was unavailable. A continuous recording of the isolated "
                    "environment setup is still required for the contest deletion test."
                ),
                "health_status": health_status,
                "health": health,
                "decision_status": decision_status,
                "decision": decision,
                "run_status": run_status,
                "run": run,
            },
            indent=2,
        )
    )
    raise SystemExit(0 if fail_closed_response_observed else 1)


if __name__ == "__main__":
    main()
