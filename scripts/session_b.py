#!/usr/bin/env python3
"""Start a separate process and prove exact fresh-session recall."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from proofops_memoryguard.canonical import subject_ref

TARGET = "0x1111111111111111111111111111111111111111"


def get(base_url: str, path: str) -> dict[str, object]:
    with urlopen(f"{base_url.rstrip('/')}{path}", timeout=15) as response:
        return json.loads(response.read())


def runtime_evidence(runtime: dict[str, object]) -> dict[str, object]:
    memory = runtime.get("memory") or {}
    agent = runtime.get("agent") or {}
    if not isinstance(memory, dict):
        memory = {}
    if not isinstance(agent, dict):
        agent = {}
    return {
        "runtime_instance_id": agent.get("runtime_instance_id"),
        "sdk_distribution": memory.get("sdk_distribution"),
        "sdk_version": memory.get("sdk_version"),
        "sdk_version_expected": memory.get("sdk_version_expected"),
        "sdk_import_file_recorded_by_distribution": memory.get(
            "sdk_import_file_recorded_by_distribution"
        ),
        "sdk_import_file_hash_matches_record": memory.get("sdk_import_file_hash_matches_record"),
        "sdk_required_runtime_files_recorded": memory.get("sdk_required_runtime_files_recorded"),
        "sdk_runtime_file_hashes_match_record": memory.get("sdk_runtime_file_hashes_match_record"),
        "sdk_version_matches_pin": memory.get("sdk_version_matches_pin"),
        "sdk_identity_ready": memory.get("sdk_identity_ready"),
        "schema_version": memory.get("schema_version"),
        "schema_version_expected": memory.get("schema_version_expected"),
        "schema_compatible": memory.get("schema_compatible"),
        "production_eligible": memory.get("production_eligible"),
        "build_commit": runtime.get("build_commit"),
        "server_time_utc": runtime.get("server_time_utc"),
    }


def model_evidence(runtime: dict[str, object]) -> dict[str, object]:
    agent = runtime.get("agent") or {}
    if not isinstance(agent, dict):
        agent = {}
    model = agent.get("model") or {}
    return dict(model) if isinstance(model, dict) else {}


def has_successful_model_trace(run: dict[str, object]) -> bool:
    trace = run.get("tool_trace") or []
    return isinstance(trace, list) and any(
        isinstance(event, dict)
        and event.get("tool") == "model.plan"
        and event.get("phase") == "succeeded"
        for event in trace
    )


def remote_model_checks(run: dict[str, object]) -> bool:
    receipt = run.get("model_receipt") or {}
    trace = run.get("tool_trace") or []
    receipt_trace_bound = isinstance(trace, list) and any(
        isinstance(event, dict)
        and event.get("tool") == "model.receipt"
        and event.get("phase") == "succeeded"
        and isinstance(event.get("output_hash"), str)
        and len(str(event.get("output_hash"))) == 64
        for event in trace
    )
    return (
        run.get("schema_version") == "1.1"
        and run.get("model_kind") == "remote_structured_model"
        and run.get("planning_degraded") is False
        and has_successful_model_trace(run)
        and isinstance(receipt, dict)
        and receipt.get("live_call_verified") is True
        and receipt.get("structured_output_validated") is True
        and bool(receipt.get("resolved_model"))
        and bool(receipt.get("generation_id"))
        and isinstance(receipt.get("completion_sha256"), str)
        and len(str(receipt.get("completion_sha256"))) == 64
        and receipt_trace_bound
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--session-a-evidence", type=Path, required=True)
    parser.add_argument("--session-a-sha256", required=True)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--require-remote-model", action="store_true")
    args = parser.parse_args()
    session = f"cli-b-{uuid.uuid4()}"
    runtime = get(args.base_url, "/api/runtime")
    current_sibyl = runtime_evidence(runtime)
    before_bytes = args.session_a_evidence.read_bytes()
    manifest_digest_matches = (
        hashlib.sha256(before_bytes).hexdigest() == args.session_a_sha256.lower()
    )
    before = json.loads(before_bytes)
    before_manifest_run = before.get("agent_before") or {}
    before_sibyl = before.get("sibyl_runtime") or {}
    if not isinstance(before_manifest_run, dict):
        before_manifest_run = {}
    if not isinstance(before_sibyl, dict):
        before_sibyl = {}
    before_run_id = before_manifest_run.get("run_id")
    if not isinstance(before_run_id, str) or not before_run_id:
        raise SystemExit("Session A evidence has no run_id")
    before_run = get(args.base_url, f"/api/agent/runs/{before_run_id}")
    dispute = before.get("dispute") or {}
    if not isinstance(dispute, dict):
        dispute = {}
    dispute_id = dispute.get("observation_id")
    before_decision = before_run.get("decision") or {}
    if not isinstance(before_decision, dict):
        before_decision = {}
    before_intent = before_decision.get("intent") or {}
    if not isinstance(before_intent, dict):
        before_intent = {}
    fixed_action = before.get("fixed_action") or {}
    if not isinstance(fixed_action, dict):
        fixed_action = {}
    same_sibyl_sdk = all(
        before_sibyl.get(key) == current_sibyl.get(key)
        for key in ("sdk_distribution", "sdk_version", "schema_version")
    )
    stored_a_matches_manifest = all(
        before_run.get(key) == before_manifest_run.get(key)
        for key in (
            "run_id",
            "request_hash",
            "runtime_instance_id",
            "verdict",
            "state",
            "action_fingerprint",
            "proof_root",
        )
    )
    session_a_runtime_bound = before_sibyl.get("runtime_instance_id") == before_run.get(
        "runtime_instance_id"
    )
    different_runtime_before_session_b = bool(
        before_run.get("runtime_instance_id")
    ) and before_run.get("runtime_instance_id") != current_sibyl.get("runtime_instance_id")
    expected_subject_ref = subject_ref(args.subject)
    session_a_subject_bound = (
        before.get("subject_fingerprint") == hashlib.sha256(args.subject.encode()).hexdigest()
        and before_decision.get("subject_ref") == expected_subject_ref
        and before_intent.get("subject_id") == expected_subject_ref
    )
    session_a_action_bound = all(
        fixed_action.get(key) == before_intent.get(key)
        for key in ("chain_id", "target", "method", "amount_usd")
    )
    build_commit = before_sibyl.get("build_commit")
    same_build_commit = (
        isinstance(build_commit, str)
        and len(build_commit) == 40
        and all(character in "0123456789abcdef" for character in build_commit.lower())
        and build_commit == current_sibyl.get("build_commit")
    )
    preflight_passed = (
        manifest_digest_matches
        and before_run.get("verdict") == "ready"
        and before_run.get("state") == "await_finalize"
        and before_sibyl.get("sdk_identity_ready") is True
        and current_sibyl.get("sdk_identity_ready") is True
        and before_sibyl.get("schema_compatible") is True
        and current_sibyl.get("schema_compatible") is True
        and before_sibyl.get("production_eligible") is True
        and current_sibyl.get("production_eligible") is True
        and same_sibyl_sdk
        and stored_a_matches_manifest
        and session_a_runtime_bound
        and different_runtime_before_session_b
        and session_a_subject_bound
        and session_a_action_bound
        and same_build_commit
        and bool(dispute_id)
        and (not args.require_remote_model or remote_model_checks(before_run))
    )
    if not preflight_passed:
        print(
            json.dumps(
                {
                    "comparison_preflight_passed": False,
                    "session_b_run_created": False,
                    "manifest_digest_matches": manifest_digest_matches,
                    "stored_session_a_matches_manifest": stored_a_matches_manifest,
                    "session_a_runtime_bound": session_a_runtime_bound,
                    "different_runtime_before_session_b": different_runtime_before_session_b,
                    "session_a_subject_bound": session_a_subject_bound,
                    "session_a_action_bound": session_a_action_bound,
                    "same_sibyl_sdk_metadata": same_sibyl_sdk,
                    "same_build_commit": same_build_commit,
                },
                indent=2,
            )
        )
        raise SystemExit(1)

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
    with urlopen(request, timeout=90) as response:
        result = json.loads(response.read())
    runtime_after_agent = get(args.base_url, "/api/runtime")
    current_model = model_evidence(runtime_after_agent)
    session_b_remote_model_checks = remote_model_checks(result)
    result_decision = result.get("decision") or {}
    if not isinstance(result_decision, dict):
        result_decision = {}
    result_intent = result_decision.get("intent") or {}
    if not isinstance(result_intent, dict):
        result_intent = {}
    runtime_bound_to_runs = session_a_runtime_bound and current_sibyl.get(
        "runtime_instance_id"
    ) == result.get("runtime_instance_id")
    subject_bound_to_runs = (
        session_a_subject_bound
        and result_decision.get("subject_ref") == expected_subject_ref
        and result_intent.get("subject_id") == expected_subject_ref
    )
    action_bound_to_runs = all(
        fixed_action.get(key) == before_intent.get(key) == result_intent.get(key)
        for key in ("chain_id", "target", "method", "amount_usd")
    )
    dispute_memory_bound_to_recall = dispute.get("memory_root") == result_decision.get(
        "memory_root"
    ) and dispute.get("memory_version") == result_decision.get("memory_version")
    tool_trace = result.get("tool_trace") or []
    if not isinstance(tool_trace, list):
        tool_trace = []
    review_suppressed = any(
        isinstance(event, dict)
        and event.get("tool") == "human_review.prepare"
        and event.get("phase") == "suppressed"
        and event.get("reason_code") == "verdict_deny"
        for event in tool_trace
    )
    escalation_succeeded = any(
        isinstance(event, dict)
        and event.get("tool") == "operator_escalation.create"
        and event.get("phase") == "succeeded"
        for event in tool_trace
    )
    artifacts = result.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        artifacts = {}
    escalation_artifact = artifacts.get("operator_escalation.create") or {}
    if not isinstance(escalation_artifact, dict):
        escalation_artifact = {}
    non_executable_escalation = (
        result.get("executable") is False
        and result_decision.get("executable") is False
        and escalation_artifact.get("executable") is False
    )
    required = (
        preflight_passed
        and result.get("verdict") == "deny"
        and result.get("state") == "block_and_escalate"
        and result.get("cross_session") is True
        and dispute_id in result.get("causal_memory_ids", [])
        and before_run.get("action_fingerprint") == result.get("action_fingerprint")
        and before_run.get("runtime_instance_id") != result.get("runtime_instance_id")
        and before_intent.get("session_id") != result_intent.get("session_id")
        and runtime_bound_to_runs
        and subject_bound_to_runs
        and action_bound_to_runs
        and dispute_memory_bound_to_recall
        and review_suppressed
        and escalation_succeeded
        and non_executable_escalation
        and (not args.require_remote_model or session_b_remote_model_checks)
    )
    evidence = {
        "session": session,
        "transport": {
            "base_url": args.base_url.rstrip("/"),
            "public_https": args.base_url.startswith("https://"),
            "agent_run_id": result.get("run_id"),
        },
        "runtime_instance_id": result.get("runtime_instance_id"),
        "sibyl_runtime": current_sibyl,
        "action_fingerprint": result.get("action_fingerprint"),
        "comparison_checks_passed": required,
        "comparison_preflight_passed": preflight_passed,
        "session_b_run_created": True,
        "contest_gate_claimed": False,
        "remote_model_gate_required": args.require_remote_model,
        "remote_model_checks_passed": (
            remote_model_checks(before_run) and session_b_remote_model_checks
        ),
        "evidence_note": (
            "These checks bind two stored runs and detect manifest edits. The continuous "
            "recording remains required to prove the process restart and contest gate."
        ),
        "session_a_runtime_instance_id": before_run.get("runtime_instance_id"),
        "same_action_fingerprint": (
            before_run.get("action_fingerprint") == result.get("action_fingerprint")
        ),
        "different_runtime_instance": (
            before_run.get("runtime_instance_id") != result.get("runtime_instance_id")
        ),
        "exact_dispute_recalled": dispute_id in result.get("causal_memory_ids", []),
        "same_sibyl_sdk_metadata": same_sibyl_sdk,
        "stored_session_a_matches_manifest": stored_a_matches_manifest,
        "runtime_metadata_bound_to_runs": runtime_bound_to_runs,
        "subject_bound_to_runs": subject_bound_to_runs,
        "fixed_action_bound_to_runs": action_bound_to_runs,
        "dispute_memory_bound_to_recall": dispute_memory_bound_to_recall,
        "review_tool_suppressed": review_suppressed,
        "escalation_tool_succeeded": escalation_succeeded,
        "non_executable_escalation": non_executable_escalation,
        "agent_model_after_run": current_model,
        "same_build_commit": same_build_commit,
        "manifest_digest_matches": manifest_digest_matches,
        "agent_after": result,
    }
    rendered = json.dumps(evidence, indent=2)
    if args.evidence_out:
        args.evidence_out.write_text(rendered, encoding="utf-8")
        evidence["evidence_out"] = str(args.evidence_out)
        evidence["session_b_evidence_sha256"] = hashlib.sha256(rendered.encode()).hexdigest()
    print(json.dumps(evidence, indent=2))
    raise SystemExit(0 if required else 1)


if __name__ == "__main__":
    main()
