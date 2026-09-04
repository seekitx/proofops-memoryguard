from __future__ import annotations

import json
from pathlib import Path


def test_public_render_ab_evidence_is_complete_and_claim_aware() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "2026-09-05_RENDER_OPENROUTER_AB.json"
    )
    evidence = json.loads(path.read_text(encoding="utf-8"))
    session_a = evidence["session_a"]
    session_b = evidence["session_b"]
    checks = evidence["checks"]

    assert evidence["public_base_url"].startswith("https://")
    assert len(evidence["build_commit"]) == 40
    assert evidence["agent_run_schema"] == "1.1"
    assert evidence["model"].endswith(":free")
    assert evidence["production_reliability_claimed"] is False
    assert evidence["continuous_video_complete"] is False
    assert evidence["contest_gate_claimed_by_json"] is False

    assert session_a["run_id"].startswith("run_")
    assert session_b["run_id"].startswith("run_")
    assert session_a["runtime_instance_id"] != session_b["runtime_instance_id"]
    assert session_a["verdict"] == "ready"
    assert session_b["verdict"] == "deny"
    assert session_a["action_fingerprint"] == session_b["action_fingerprint"]
    assert session_a["live_model_receipt_verified"] is True
    assert session_b["live_model_receipt_verified"] is True
    assert session_a["structured_output_validated"] is True
    assert session_b["structured_output_validated"] is True
    assert len(session_a["completion_sha256"]) == 64
    assert len(session_b["completion_sha256"]) == 64

    assert checks["comparison_preflight_passed"] is True
    assert checks["comparison_checks_passed"] is True
    assert checks["same_build_commit"] is True
    assert checks["same_action_fingerprint"] is True
    assert checks["different_runtime_instance"] is True
    assert checks["exact_dispute_recalled"] is True
    assert checks["review_tool_suppressed"] is True
    assert checks["escalation_tool_succeeded"] is True
    assert checks["non_executable_escalation"] is True
    assert checks["remote_model_checks_passed"] is True
