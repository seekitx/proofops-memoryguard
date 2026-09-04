# Render HTTPS + OpenRouter fresh-session evidence

## Outcome

On 2026-09-05, the public Render service completed a strict Session A/B run on the
same deployed build with a real service restart in between. Both Agent runs used the
pinned OpenRouter free model and stored a schema `1.1` receipt inside the Sibyl Agent
ledger.

- Public demo: <https://proofops-memoryguard.onrender.com>
- Readiness: <https://proofops-memoryguard.onrender.com/health/ready>
- Evidence dashboard: <https://proofops-memoryguard.onrender.com/evidence>
- Git build: [`5ae0861f96277bba37deae32165139821151e5dc`](https://github.com/seekitx/proofops-memoryguard/commit/5ae0861f96277bba37deae32165139821151e5dc)
- Model: `nvidia/nemotron-3-super-120b-a12b:free`
- Service tier: `free_experimental`; production reliability is not claimed.

## Bound comparison

| Check | Session A | Session B |
|---|---|---|
| Stored run | [`run_dd3d78f34f4d5630103a`](https://proofops-memoryguard.onrender.com/api/agent/runs/run_dd3d78f34f4d5630103a) | [`run_d703e9eaaa0204a87f9f`](https://proofops-memoryguard.onrender.com/api/agent/runs/run_d703e9eaaa0204a87f9f) |
| Runtime instance | `runtime_ca49668ad6704289be9c` | `runtime_3ebf506298474c8595eb` |
| Verdict / state | `READY / await_finalize` | `DENY / block_and_escalate` |
| Action fingerprint | `8b32ebe81cb548c47c07385296faa70bc9cdf49acf41f7728015670818427cc3` | same |
| Live model receipt | passed | passed |
| Structured output validated | true | true |

Session A stored dispute observation `obs_d3af641d7ba34a088b68` after the READY run.
Session B recalled that exact observation after the Render restart. The comparison
script also verified:

- the Session A manifest digest before Session B;
- the same build commit and official Sibyl SDK metadata;
- different runtime and session IDs;
- the same subject and fixed action bound into both stored runs;
- the same action fingerprint;
- exact causal dispute recall and matching memory root/version;
- `human_review.prepare` suppressed under `DENY`;
- `operator_escalation.create` succeeded;
- the escalation remained non-executable; and
- both receipt-bound OpenRouter checks passed.

The local comparison manifests had these SHA-256 digests at capture time:

- Session A: `846427e18d476de52c3aa74049f2b3078b584d65f2b4829a788fd9db31c5887c`
- Session B: `ef84c559c0fd3ff6ae333369df54234579437a2bc6ef34017cdc58861a37ed98`

## Evidence boundary

The Render restart command was issued from the authenticated dashboard and the
runtime ID changed before Session B. The public Sibyl ledger records and comparison
checks are judge-checkable, but JSON alone cannot prove the operator's continuous
screen sequence. The required unedited video remains a separate manual gate.

The facts are labelled `demo_fixture`. This run is not customer adoption, an
identity-verified dispute, a payment, a Base transaction, a Virtuals integration, or
PMF evidence. No Base or partner multiplier is claimed.

Before pinning the model, the generic `openrouter/free` router produced one invalid
JSON response and one HTTP failure during DENY-side retries. MemoryGuard still
returned `DENY`, ran the mandatory escalation, and marked planning degraded. The
final captured A/B pins a free model that had already produced a valid structured
receipt, reducing routing variance without changing the deterministic authority
boundary.
