# Release gates — no inferred completion

## Already in source

Scoped roles, integer limits, complete risk/resolve/reconsider state machine, transitive suspension, immutable historical decisions, bounded investigation, same-case review, non-authoritative precedents, UI, official-SDK adapter, test scripts and audit-anchor integration.

Source existence alone does not validate production.

## Must pass on the target repository before v2 publication

- [ ] Exact base overlay applies without overwriting other local work; review resulting diff.
- [x] Install pinned official Sibyl SDK; no substitute in runtime. The final local gate records the official SDK stage as `PASSED` (Sibyl client 0.7.0).
- [x] Full original repository tests AND new casework tests pass. The final local gate records 216 tests with 0 failures, 0 errors and 0 skipped.
- [x] SDK integration test executes, not skips. The official-SDK stage passed and the final pytest stage reports 0 skipped tests.
- [x] Default official-SDK24-scenario benchmark completes; report backend is official. The final scenario matrix is recorded as 24/24 passed against the official backend.
- [x] Two-process probe completes READY→DENY; temporary deletion yields missing-memory failure. The final `fresh_process` gate passed, and the accepted final-SHA take records the post-restart READY→DENY sequence with non-executable decisions.
- [x] Actual app stop/start on the current VPS retains the synthetic workspace and same finalbuild SHA. The public VPS evidence files record a real `memoryguard` container restart, different runtime IDs, same SHA `a4b216e73f2eed86ef2e07e2fdece4b48728190c`, and the Session A `READY` → Session B `DENY` safety change. The evidence is synthetic-only (`real_private_casework_touched=false`) and is not a private-data migration claim.
- [x] Temporary VPS owner/investigator credentials are revoked after the evidence run. The new-VPS evidence records both post-cleanup requests as HTTP 401 `INVALID_CREDENTIAL`; token values are not retained in the evidence.
- [ ] Legacy v1 writes are 410; historical v1 GET remains readable and labelled historical. The final deployment evidence proves the legacy POST is 410, but the current evidence index does not prove the historical GET half of this gate.
- [ ] Auth scopes, role switches and token redaction validated in browser and server logs. Role-scoped operations are recorded, but a complete browser/server-log token-redaction check is not in the current final evidence.
- [ ] Desktop/mobile browser walkthrough and errors pass; no localStorage/sessionStorage credentials.
- [x] New remote investigation receipt succeeds on finalbuild; outage visibly degrades. The initial VPS attempt degraded. A separate synthetic request after switching to `openai/gpt-4.1-mini` returned `REMOTE` with validated structured output and a generation ID on the same a4b216e build; see `../output/final-release-20260906/new-vps/remote-model-receipt-public.json`. Both results remain non-authoritative and non-executable.
- [x] Solidity compile and Hardhat tests succeed with reviewed dependency lock. The contract verification summary records Solidity 0.8.24, the reviewed lock install and four Hardhat tests passing.
- [x] Actual Keccak/ABI behavior verified, not only injected unit-test hash. The contract evidence records the ABI and Keccak selector/event cross-check against the deployed contract.
- [x] Base Sepolia deployment and product-relevant audit transaction verified and recorded as audit-only evidence; this does not claim payment authority or a partner multiplier. The partner evidence remains outside this public VPS evidence bundle.
- [ ] Same finalbuild evidence index points to videos, tests, reports and actual runtime records. The public whitelist intentionally contains only the redacted current-VPS files; internal release summaries, recording artifacts and partner evidence remain outside it. The current VPS remote receipt passed; current-VPS continuous capture remains open.
- [ ] Original local video reviewed; cold-start segment continuous and matches final code. Historical recording acceptance and the presentation candidate remain unpublished; audio owner review is also pending.
- [ ] Public posts/video URLs accessible; private page status checked by owner; ready before deadline.

## Keep NOT CLAIMED unless real external evidence exists

Virtuals native runtime or completed partner job (Job #76728 remains onchain `Open` with `budget=0`, its deadline elapsed without payment, delivery or completion), partner multiplier award, customers, PMF, monetary savings, mainnet payment, independent security audit and production multi-host scalability.

## Rollback

First stop public writes and isolate the deployment. Do not disable CASEWORK_ENABLED as a public production rollback: it reopens the legacy anonymous demo write surface. Older code may also ignore newly persisted source obligations. Preserve SDK disk and historical evidence, and review compatibility before restoring writes. See docs/SIBYL_FINAL_RELEASE.md. Installer source rollback does not touch business data and refuses to overwrite edits made after installation. Do not erase actual DB to make a failed test look clean; only isolated probes may delete their own temporary DB.
