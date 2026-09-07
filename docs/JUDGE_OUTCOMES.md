# What MemoryGuard demonstrably changes

Runtime commit: `a4b216e73f2eed86ef2e07e2fdece4b48728190c`.
These are synthetic risk scenarios with recorded verification, not customer results.
No new model calls or test runs were used to compile this table.

| Scenario | Recorded outcome | What is still required | Evidence |
|---|---|---|---|
| Same action, fresh process, two open risks | READY becomes DENY; same fingerprint, different runtime | Resolve both risks and obtain valid review | Accepted Render take; separate VPS A/B |
| Work depends on the blocked action | Dependent task SUSPENDED | Resolve blockers and recover through valid workflow | Render task table; VPS task outcomes |
| Work has no dependency on those risks | Unrelated task remains READY | READY still grants no execution capability | Render task table; VPS task outcomes |
| Only one risk resolved | DENY remains; the other risk is cited | Resolve the remaining risk | Render replay; isolated official-SDK capture |
| Both risks resolved | NEEDS_HUMAN; no automatic READY | Explicit authorized reconsideration | Render replay; isolated official-SDK capture |
| Explicit reviewer reconsideration | New READY decision and different proof root | Finalization gates still apply; executable=false | Render replay |
| Missing Sibyl memory | Core stops instead of substituting memory | Restore legitimate memory dependency | Separate isolated official-SDK probe, not live deletion |
| External Gloria news | Seven quarantine events observed at revisions 74–80 | News is not trusted fact, review or authority | Prior successful production read; not a task-status comparison |

## Evidence boundaries

[Machine-readable outcomes](../submission/evidence/outcomes-a4b216e.json) contains
checks extracted from existing reports and SHA-256 digests of the source files.
[Public VPS evidence](../output/final-release-20260906/new-vps/public-safe-evidence.json)
includes an actual service restart. Session A was recovered through read-only
inspection after a recorder timeout; it is not a continuous VPS recording.
The film's continuous section comes from the earlier Render take of the same build.
The later successful remote model receipt is separately recorded in
[the model evidence](../output/final-release-20260906/new-vps/remote-model-receipt-public.json).

READY means eligible to proceed to the next configured review gate, never money
sent. This table claims neither financial savings nor independent customer usage.
