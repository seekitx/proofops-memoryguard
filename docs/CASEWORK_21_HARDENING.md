# Casework 2.1 — release hardening and observable recovery

This is a source-level increment on commit `3ff9863dcab45ef4040506bab91492d5ee74575f`.
It is not a new contest entry, payment system, or a declaration that release gates passed.

## Changes

- `core.policy_result`: validate **every** ancestor's current decision, expiry and basis, not only direct parents.
- `core.ready_expiry`: clamp a READY proof to its required baseline/ancestor expiries.
- `core.decision_validity`: re-evaluate policy and time before calling a proof current; a hash match alone is insufficient.
- `core.recovery_plan`: read-only, dependency-first operator checklist; it does not auto-resolve or authorize anything.
- `service._decision`: persist a non-executable escalation artifact in the same workspace commit for DENY/NEEDS_HUMAN. The tool label alone is not counted as an execution receipt.
- `core.active_precedents`: only still-resolved, version-bound lessons may guide investigation. Reopening the source case withdraws the lesson from active retrieval.
- `investigation_basis`: include active precedent versions, including cases with zero associated tasks.
- `receipts.bound_receipt`: verify exact existing-model context hash, structured-output flags and bounded typed fields. This is not a provider-signed attestation.
- `store`: detect removal/replacement of the DB inode before using cached connections. This is not cross-restart anti-rollback protection.
- `runtime`: use `settings.build_commit` (including Render fallback); active v2 storage drives readiness. Storage readiness does not auto-bootstrap a workspace.
- `anchoring`: require transaction object/receipt identity consistency and reject zero roots. A prepared anchor binds one submitted transaction hash; exact idempotent replays do not call RPC again.
- UI: clear old operator state on role switches, discard in-flight responses from earlier credentials, show recovery order and effective policy state.

## New routes

| Route | Access | Behavior |
|---|---|---|
| `GET /api/v2/tasks/{task_id}/recovery` | scoped credentials | dependency-first read-only plan |
| `GET /casework/evidence` | public | no private workspace access |
| `GET /api/v2/public-evidence` | public | allowlisted exported synthetic evidence only |
| `GET /health/ready` with v2 enabled | public | active v2 storage readiness, sanitized counts |
| `GET /api/runtime` with v2 enabled | public | active module, commit, source fingerprint; no credentials |

`/api/v2/health` remains an authenticated initialized-workspace check. `/health/live`
is only process liveness. Optional model outage must not become security authority.

## Compatibility and migration

The persisted Workspace/Decision/Report models, their hash domains, and the v1 code
are not rewritten. Existing histories remain readable. Existing investigation reports
use the previous basis formula, so they must be investigated again before handoff or
resolution. This invalidation is intentional; do not "fix" it by overwriting hashes.

Pre-2.1 lessons lack a case version and resolved sequence. They remain stored as
historical records but are excluded from current precedent retrieval. New resolutions
produce version-bound lessons. No legacy lesson is silently upgraded to trusted data.

Existing decisions are historical until their live validity passes the new checks.
Existing READY proofs do not acquire payment authority. A copied database whose
entire history has been maliciously rewritten cannot be authenticated by unkeyed
hashes alone. Base anchors attest specific roots, not the truth of every fact.

A pending anchor transaction cannot be replaced with another hash on the same
anchor request. Gas-replacement handling is not automated; an operator must prepare
and review a separate audit request where necessary. Chain verification is an
observation at a stated time, not permanent finality.

## Explicit limitations

Single POSIX host / local persistent disk, bounded aggregate, configured roles (not
independent people by themselves), no automatic dispute detector, no payment execution,
no cumulative spending reservations, no complete SSO, no multi-node store, no Virtuals
integration in this increment. A model chooses bounded investigation tools; it does
not independently discover real-world truth or close cases.
