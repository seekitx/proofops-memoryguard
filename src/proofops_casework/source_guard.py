"""Durable source obligations: config removal is not evidence that risk disappeared.

The aggregate is still the only store. Legacy source heads/report bundles are read
conservatively; we never manufacture source proof when upgrading an old workspace.
"""
from .core import CaseworkError, digest


def obligations(state, case_id):
    ids, groups, configured = set(), 0, False
    for value in state.artifacts.values():
        if value.get("case_id") != case_id:
            continue
        kind = value.get("kind")
        if kind == "SOURCE_POLICY_GUARD":
            ids.update(value.get("required_sources", []))
            groups = max(groups, value.get("min_independence_groups", 0))
            configured = configured or value.get("configured_policy_required", False)
        elif kind in {"SOURCE_REQUEST", "SOURCE_HEAD", "SOURCE_RECEIPT"}:
            if value.get("source_id"):
                ids.add(value["source_id"])
        elif kind == "REPORT_EVIDENCE_BUNDLE":
            bundle = value.get("bundle", {})
            ids.update(bundle.get("required_sources", []))
            ids.update(r["source_id"] for r in bundle.get("receipts", []) if r.get("source_id"))
            recorded_floor = bundle.get("source_obligations", {})
            policy_required = recorded_floor.get("configured_policy_required",
                                                  bundle.get("resolution_requires_sources", False))
            if policy_required:
                configured = True
                # Legacy bundles did not store their threshold. One is the only
                # threshold inferable without inventing provenance. New optional
                # source reports must NOT invent a configured policy requirement.
                groups = max(groups, recorded_floor.get("min_independence_groups", 1 if ids else 0))
    return {"required_sources": sorted(ids), "min_independence_groups": groups,
            "configured_policy_required": configured}


def has_obligations(state, case_id):
    floor = obligations(state, case_id)
    return bool(floor["required_sources"] or floor["configured_policy_required"])


def effective_policy(state, case, policy):
    floor = obligations(state, case.case_id)
    if floor["configured_policy_required"] and policy is None:
        raise CaseworkError("SOURCE_POLICY_REMOVED", 409)
    guard = state.artifacts.get(digest("source-policy-guard", case.case_id), {})
    # Explicit configured requirements cannot be weakened with a config edit.
    if policy is not None and guard.get("configured_policy_required"):
        configured_ids = set(guard.get("configured_sources", []))
        if (not configured_ids <= set(policy.required_sources)
                or policy.min_independence_groups < guard.get("min_independence_groups", 0)):
            raise CaseworkError("SOURCE_POLICY_WEAKENED", 409)
    ids = set(floor["required_sources"])
    if policy:
        ids.update(policy.required_sources)
    return {"required_sources": sorted(ids),
            "min_independence_groups": max(floor["min_independence_groups"],
                                          policy.min_independence_groups if policy else 0),
            "configured_policy_required": bool(policy or floor["configured_policy_required"])}


def remember_policy(state, case, policy, source_ids=()):
    floor = effective_policy(state, case, policy)
    floor["required_sources"] = sorted(set(floor["required_sources"]) | set(source_ids))
    if not floor["required_sources"] and not floor["configured_policy_required"]:
        return
    key = digest("source-policy-guard", case.case_id)
    previous = state.artifacts.get(key, {})
    floor["configured_sources"] = sorted(set(previous.get("configured_sources", [])) |
                                         set(policy.required_sources if policy else []))
    state.artifacts[key] = {"kind": "SOURCE_POLICY_GUARD", "case_id": case.case_id,
                            **floor, "authority": False, "executable": False}


def require_desk(state, case_id, desk, report=None):
    source_report = report and any(t.get("tool") == "evidence.inspect" for t in report.trace)
    if desk is None and (source_report or has_obligations(state, case_id)):
        raise CaseworkError("SOURCE_GUARD_UNAVAILABLE", 503)
