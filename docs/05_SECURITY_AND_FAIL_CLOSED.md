# Security and fail-closed boundary

## Plain-language conclusion

MemoryGuard can stop an action; it cannot prove that a caller is who they claim to
be. This contest implementation safely demonstrates persistent memory and poisoned
input handling with synthetic fixtures. A real production integration must replace
the demo source with an authenticated identity/dispute feed.

## Trust model

| Input | Authority | Handling |
|---|---|---|
| `demo_fixture` typed fact | Trusted only inside the labeled contest demo | Accepted into Sibyl with its synthetic evidence label |
| `caller_supplied` typed fact | Unverified | Quarantined/review required; cannot create READY or DENY authority |
| Identity/Base verified typed fact | Model supports these evidence labels internally | Requires a future authenticated Adapter before public API exposure |
| External free text | Never authoritative | Pattern-scanned, domain-hashed, then discarded |
| Model explanation | Descriptive only | Never grants capability or changes policy |
| User wallet | Final human gate | Wallet displays and signs the fixed plan; no private key reaches the Agent |

## Invariants

1. Production `MemoryGuard` construction accepts only a Sibyl Memory Adapter.
2. Every subject has an append-style observation hash chain and memory root.
3. Every decision reload validates its action hash and decision proof root.
4. Source mode is machine-readable; demo evidence cannot silently become verified
   customer evidence.
5. Unknown fact fields and free text do not enter the authority path.
6. `decide` returns no transaction payload and always serializes
   `executable: false`.
7. `finalize` accepts only `decision_id` plus an optional transaction hash. Callers
   cannot submit a verdict, policy, memory root, intent, or proof root.
8. A Base receipt is verified against chain ID, status, contract, sender/event
   attester, event signature, indexed proof root, and memory version.
9. A pending or failed receipt is not “verified”.
10. Finalization state is monotonic: terminal local/verified/failed records cannot be
    downgraded by a later transaction hash; failed verification attempts are not
    persisted over a valid prior state.
11. No signing key is accepted, stored, or logged.

## Failure matrix

| Failure | Safe outcome | User impact |
|---|---|---|
| Official Sibyl client missing | Development 503; production startup refusal | No decision; no fallback |
| Sibyl operation fails | `503`, sanitized exception type | Retry later; no capability |
| Memory chain/root mismatch | `503 MEMORY_INTEGRITY_FAILED` | Manual investigation required |
| Concurrent subject version change | `409 MEMORY_CONFLICT` | Recall and decide again |
| Unknown/expired decision | `404` / `409` | A new decision is required |
| READY draft's memory or policy changed | `409 FINALIZATION_FAILED` | Recall and decide again |
| READY without Base Adapter | finalization `failed` | Cannot become executable |
| Wrong/reverted/pending Base receipt | `failed` / `pending` | No Base proof claim |
| Malicious vendor text | raw text quarantined and discarded | Trusted structured dispute remains active |

## Known limitations — do not hide these from judges

- The public demo lets a visitor submit `demo_fixture` data. This is useful for an
  isolated synthetic case, not real source authentication.
- The official local Sibyl SDK uses a local database. A hosted service therefore
  needs a persistent disk and single-writer deployment for this entry; horizontal
  multi-instance coordination is not claimed.
- Exact source authentication, key rotation, tenant administration, abuse rate
  limiting, and audit export require a production wrapper.
- The hash proves that committed bytes did not change; it does not prove the original
  real-world claim was true.
- No action execution Adapter exists. Even a verified READY proof remains
  non-executable in this repository.
- Base verification proves that the receipt sender and event attester are the same
  wallet. It does not yet bind that wallet to an authenticated customer identity.

## Deletion test

The deletion test should be recorded only after test execution is authorized:

1. Run the normal Session A/B story and capture causal DENY.
2. Remove or make the official Sibyl dependency unavailable in an isolated runtime.
3. Restart. In development, call `POST /api/decisions` and record the 503. In
   production, record the honest startup refusal instead of claiming an endpoint ran.
4. Confirm the absence of a JSON/in-memory fallback in either mode.
5. Restore the normal environment; do not edit the public demo to fake this state.
