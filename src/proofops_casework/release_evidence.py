"""Public projection of an explicitly exported local gate, never private workspaces."""
from datetime import datetime, timezone
import re
from .json_boundary import read_json_file

NAMES = {"static", "official_sdk", "pytest", "fresh_process", "scenario_matrix", "source_experiment", "http_acceptance", "contracts"}
STATES = {"NOT_RUN", "PASSED", "FAILED", "BLOCKED", "TIMEOUT"}


def public_release(path, *, commit, source):
    result = {"state": "NOT_RECORDED", "current_build_commit": commit, "scope":
        "Local self-recorded gates only; not external integration, hosted restart, independent audit or contest readiness.",
        "local_release_ready": False, "contest_submission_ready": False, "partner_bonus_claimed": False}
    if path is None or not path.exists():
        return result
    try:
        value, _ = read_json_file(path, max_bytes=128_000)
        if (not isinstance(value, dict) or value.get("schema_version") != "memoryguard-release-gate/1"
                or value.get("mode") not in {"EXECUTED_LOCAL", "PREFLIGHT_ONLY"}
                or type(value.get("git_clean")) is not bool or type(value.get("source_stable")) is not bool
                or not isinstance(value.get("build_commit"), str) or not re.fullmatch("[a-f0-9]{40}", value["build_commit"])
                or not isinstance(value.get("source_digest"), str) or not re.fullmatch("[a-f0-9]{64}", value["source_digest"])):
            raise ValueError("invalid record")
        at = datetime.fromisoformat(value["captured_at"].replace("Z", "+00:00"))
        if at.tzinfo is None or at > datetime.now(timezone.utc):
            raise ValueError("invalid capture time")
        stages = value.get("stages")
        if (not isinstance(stages, list) or len(stages) != len(NAMES)
                or any(not isinstance(s, dict) for s in stages)
                or {s.get("name") for s in stages} != NAMES
                or any(s.get("state") not in STATES for s in stages)):
            raise ValueError("invalid stage table")
        current = (value["build_commit"] == commit and value["source_digest"] == source and
                   value["git_clean"] and value["source_stable"])
        ready = current and value["mode"] == "EXECUTED_LOCAL" and all(s["state"] == "PASSED" for s in stages)
        result.update(state="CURRENT_LOCAL_PASSED" if ready else "CURRENT_INCOMPLETE" if current else "HISTORICAL_OR_DIRTY",
            captured_build_commit=value["build_commit"], captured_at=at.isoformat(),
            stages=[{"name": s["name"], "state": s["state"]} for s in stages], local_release_ready=ready)
    except (OSError, ValueError, TypeError, KeyError):
        result["state"] = "INVALID_RECORD"
    return result
