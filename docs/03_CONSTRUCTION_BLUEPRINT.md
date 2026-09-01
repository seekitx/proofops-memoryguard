# MemoryGuard construction blueprint

## Target product

ProofOps MemoryGuard is a persistent decision firewall for high-risk Agent actions.
It remembers trusted disputes and revocations, rejects memory pollution, and explains
which earlier fact changed a decision in a fresh session.

## Module layout

```text
src/proofops_memoryguard/
  models.py                 typed observations, intents, drafts, proofs
  canonical.py              domain-separated canonical hashes and redaction
  policy.py                 pure fail-closed decision kernel
  ports.py                  internal Memory and Anchor seams
  module.py                 observe / decide / finalize Interface
  adapters/
    sibyl.py                contest production Memory Adapter
    memory_fake.py          test-only Adapter
    base_anchor.py          Base plan and receipt verification Adapter
  http.py                   thin FastAPI request/response mapping
```

## Dependency categories

- In-process: normalization, injection detection, policy, hashes, state transitions.
- Local-substitutable: proof/draft store; production uses SQLite transactions and
  tests may use temporary storage.
- True external, local-first: Sibyl SDK behind the Memory Seam.
- True external: Base RPC and user wallet behind the Anchor Seam.

## Phase 1 — contest critical path

1. Define immutable models and verdict states.
2. Implement canonical hashing with a `proofops-memoryguard/v1` domain.
3. Implement deterministic quarantine and source precedence.
4. Implement `SibylMemoryAdapter` with exact WARM entity lookup, COLD journal append,
   and REFERENCE policy metadata. Browser session state remains ephemeral and is not
   treated as authoritative memory.
5. Implement `MemoryGuard.observe` and `MemoryGuard.decide`.
6. Missing Sibyl must yield `MEMORY_UNAVAILABLE`; production wiring rejects the
   in-memory Adapter.

Acceptance: Session A writes, a new Module instance in Session B reads, the same
intent changes, and the response includes causal memory IDs and hashes.

## Phase 2 — proof finalization

1. Store decision drafts server-side with version, nonce, expiry, intent hash,
   memory root, policy hash, and verdict.
2. `finalize(decision_id)` returns either a final local DENY proof or a fixed Base
   wallet transaction plan.
3. `finalize(decision_id, tx_hash)` reloads the draft and verifies chain, contract,
   event, and proof root.
4. Never let HTTP callers submit a verdict or replacement proof root.

Acceptance: tampering, unknown IDs, expired drafts, wrong chains, wrong contracts,
wrong events, and wrong roots all fail closed.

## Phase 3 — judge interface

Use a forensic operations-console aesthetic: near-black field, paper-white evidence
cards, safety orange for quarantine, and acid green only for verified states. The
single page must show:

- Session A and Session B IDs;
- exact identical payment intent;
- accepted structured dispute versus quarantined malicious note;
- READY → DENY causal diff;
- Sibyl write and recall locations;
- local/pending/Base-verified proof state;
- no raw private text or wallet key.

## Phase 4 — Base winning scope

1. Add a minimal `MemoryProofAnchor` contract that emits a proof-root event.
2. Add Base Sepolia and Base mainnet configuration without committed private keys.
3. Browser requests a fixed plan, then the user's wallet signs.
4. Backend independently verifies the receipt.
5. Claim the Base multiplier only after the real demo and partner rule are confirmed.

## Phase 5 — submission artifacts

- README with two-minute code pointers and Prior Work declaration.
- Unedited 2–5 minute video with timestamp or commit hash.
- Public demo post and build-log post tagging the required accounts.
- Public proof endpoint with redacted inputs.
- Manual gate checklist for registration, hosting persistence, Base receipt, PMF,
  video, posts, and private build-page submission.

## Explicitly deferred

- Virtuals until a real native action exists.
- Automatic money movement.
- Generic chat, multiple chains, marketplaces, trading strategies, and reputation
  scoring that do not strengthen the one fresh-session story.

## Verification policy for this implementation turn

Per the user's global rule, this turn may add tests but will not compile, build, or
run them unless explicitly requested. Static checks may verify imports, paths,
configuration structure, diff scope, and absence of stale contest claims.
