# Casework v2 security and failure model

## Authority != provenance != display label

A server-controlled credential grants a role and explicit tenant/subject scope. The operator may attest baseline or risk facts only within that scope. Neither a Base transaction nor an `identity_verified` text label establishes factual truth or customer identity. No client-supplied authority mode is accepted by the v2 schemas.

The credential file must be owner-only0600; raw bearer credentials must never be committed, uploaded or recorded. Tokens are high entropy, SHA256-indexed and checked with constant-time comparison. The built-in mechanism is a small operator registry, not OAuth, SSO, KYC, federated identity or key rotation service. Restart after registry changes; deploy behind HTTPS and appropriate edge abuse limits.

## Permission separation

Owner sets baseline. Owner/investigator opens/reopens risk. Investigator creates report and handoff. A different configured reviewer must accept and resolve. Ordinary calls, wrong scope, old case version, stale basis and caller-provided role/verdict are rejected. One operator controlling all demo tokens is not real-world separation of duties; production operators should be independently controlled.

## Unsafe paths excluded

- No payment/sign/broadcast function is registered on server or model.
- Every decision and review result carries executable=false.
- A raw note is hashed and discarded, regardless of whether regex recognizes an attack. This is authority isolation, not universal prompt-injection detection.
- External model prose is not persisted as instructions, not shown as trusted operating advice, and cannot resolve a case.
- Resolved precedent is non-authoritative; matching an old case never clears a current blocker.
- One resolved case cannot clear other disputes/revocations.
- Case reopening invalidates prior reports and handoffs by version/basis.
- Old READY proofs are audit records, never auto-restored authorization.

## Ordering and money

Server command sequence defines order. Client timestamps cannot reorder revocations or restores. `expected_revision` is an optimistic precondition; distinct concurrent commands conflict rather than lose updates. Exact retries return prior receipts, clearly historical, but time-sensitive review preparation rechecks current policy before returning even a cached receipt.

Amounts are strict integer **USD valuation cents**, not token units or USDC smallest units. Floats, bools and numeric strings are rejected. Latest baseline is exclusive; older broad permission cannot override a later narrow one. There is no cumulative cash balance/accounting subsystem in this increment; do not claim budget-spend reconciliation.

## Persistence and integrity

Official Sibyl SDK is mandatory outside tests. A tenant-scoped POSIX lock plus in-process lock serializes one aggregate load/check/save operation. Both reads and writes participate. Disk/SDK exceptions and uncertain writes stop the path. No subprocess/JSON fallback reconstructs business state.

SHA256 roots detect accidental corruption and payload tampering when roots are not also replaced. These are **not digital signatures** and do not prevent a database administrator rewriting all data and recalculating roots. Optional externally anchored roots offer an independently timestamped commitment for a particular proof, not general tamper-proof storage or truth verification.

The adapter's exact serialization, transaction and close behavior must be verified against pinned sibyl-memory-client0.7.0 on the deployment platform. Local test substitutes do not prove that contract. Locks assume a single POSIX machine and local disk; do not deploy this design as multi-host high availability.

## Model concurrency and availability

Planning is outside DB lock, then relevant basis is rechecked. A provider outage yields explicitly DEGRADED investigation with deterministic mandatory reads; Sibyl failure halts. Replaying a committed investigation avoids another provider call. The final candidate persists an INVESTIGATION_ATTEMPT before a remote model call. Concurrent identical logical commands return IN_PROGRESS_OR_UNCERTAIN rather than initiating another attempt. A crash keeps that uncertainty visible; a new command is an explicit new attempt. External-provider billing exactly-once is NOT promised. See docs/SIBYL_FINAL_RELEASE.md.

## Base audit path

`MemoryCaseworkAnchor` namespaces roots by attester, rejects empty/zero-version data, and treats exact retries idempotently. The backend fixes contract, chain, root, version, value0 and attester; verifies actual transaction calldata, successful receipt, matching event, canonical block hash and minimum confirmations.

Audit anchoring may record a historical DENY proof. It cannot turn it into a payment permit. Wallet signing is an explicit user action in browser or operator deployment tooling. No private key enters v2 API/model. Confirmations reduce reorg exposure; they are not a finality guarantee. Explorer hyperlinks are not verification sources.

## Publication and test limitations

Never publish bearer tokens, private customer incident notes, model credentials or local SDK databases. Publicly share only reviewed redacted evidence. The workbench displays synthetic IDs and redacted hashes, but actor/task lists are still scoped authenticated business information.

Before production use: independent security review, real identity/operational controls, stronger abuse defense, storage scale/recovery tests and reliable external side-effect semantics are required. This is a contest-oriented safety prototype, not a custody or payments system.
