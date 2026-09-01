#!/usr/bin/env python3
"""Static, claim-aware preflight. This does not build, test, deploy, or submit."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "submission" / "status.json"
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "src/proofops_memoryguard/module.py",
    "src/proofops_memoryguard/adapters/sibyl.py",
    "contracts/src/MemoryProofAnchor.sol",
    "apps/web/index.html",
    "docs/04_PRIOR_WORK.md",
    "docs/07_MANUAL_COMPLETION_GATES.md",
)
BLOCKING_CLAIMS = (
    "registration_confirmed",
    "repository_head_pushed",
    "prior_work_boundary_reviewed",
    "contest_period_implementation",
    "real_agent_behavior",
    "fresh_session_runtime",
    "deletion_test",
    "public_deployment",
    "demo_video",
    "public_posts",
    "contest_submission",
)


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    claims = status["claims"]
    blocked = {name: claims[name]["state"] for name in BLOCKING_CLAIMS if claims[name]["state"] != "verified"}

    result = {
        "static_files_present": not missing,
        "missing_files": missing,
        "submission_ready": not missing and not blocked,
        "blocking_manual_or_runtime_gates": blocked,
        "note": "This preflight does not install, test, compile, deploy, publish, or submit.",
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["submission_ready"] else 1)


if __name__ == "__main__":
    main()
