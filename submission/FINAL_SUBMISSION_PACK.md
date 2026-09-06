# MemoryGuard final submission pack


> Latest update, 2026-09-06: the initial degraded model attempt below is historical. A separate current-VPS request using `openai/gpt-4.1-mini` now passed with a real generation receipt on build `a4b216e`. See [public receipt](../output/final-release-20260906/new-vps/remote-model-receipt-public.json). Virtuals Job #76728 passed its deadline without funding or delivery; no completion is claimed. Current-VPS continuous video and public submission remain open.

This file contains copy-ready text. Replace placeholders only after the linked
artifact exists. Never paste the private build-page edit URL into the repository.

## Public repo URL

`https://github.com/seekitx/proofops-memoryguard`

Saved to the private build page on 2026-09-05.

## Public demo URL

`https://memoryguard.eyesonchain.xyz/`

The current VPS HTTPS endpoint, readiness check, runtime identity, and public-release
status were checked read-only on 2026-09-06 at candidate SHA
`a4b216e73f2eed86ef2e07e2fdece4b48728190c`. New VPS evidence also records a real
`memoryguard` container restart with synthetic cross-restart Sibyl recall: the same
action fingerprint changes from `READY` to `DENY`, related work stops, unrelated
work continues, and all decisions remain `executable=false`. This evidence does
not prove migrated private-data persistence. The initial remote investigation degraded. A separate request after switching to `openai/gpt-4.1-mini` passed with a validated live receipt. The former Render Starter run and its persistent-disk A/B remain
historical evidence, with the honest boundary recorded in
[`evidence/2026-09-05_RENDER_OPENROUTER_AB.md`](../evidence/2026-09-05_RENDER_OPENROUTER_AB.md).

## What breaks when memory is deleted?

Deleting or disconnecting Sibyl removes the trusted dispute that changes the fresh
Agent's tool path. MemoryGuard does not fall back to JSON or process state: the
decision path becomes unavailable and no executable capability is created.

## Memory walkthrough

MemoryGuard persists validated baselines, disputes, revocations, decisions, Agent
runs, and non-executable safety-action receipts as tenant-isolated Sibyl entities;
instruction-like external text is quarantined and only its hash is retained. A fresh
Agent process reads the subject entity synchronously through `SibylMemoryAdapter`
before deciding the same high-risk action. The recalled dispute changes the verdict
from `READY` to `DENY`, suppresses `human_review.prepare`, creates
`operator_escalation.create`, returns the exact causal memory ID, and never grants a
payment, signing, or broadcast tool.

## Memory primitives to select

- `recall`
- `entities`

These two primitives and the Memory text were saved to the private build page on
2026-09-05. The video, posts, and ready action were deliberately left untouched.

Do not select semantic search, temporal/time-travel, summarization, reflection, or
consolidation for this version.

## Demo video URL

`[OWNER_TO_ADD_AFTER_PUBLICATION]`

## Post URLs

```text
[OWNER_TO_ADD_VIDEO_POST]
[OWNER_TO_ADD_BUILD_LOG_POST]
```

## Copy-ready public posts

### Demo video post

Publish this draft only after the current VPS A/B evidence has been reviewed and
the continuous recording gate is complete. Do not describe the current degraded
remote investigation as a successful model receipt.

```text
MemoryGuard treats forgetting as an authorization bug. Same $4.2k demo intent: READY → fresh VPS service restart → DENY after @sibylcap Memory recalls the exact dispute. Injection text is quarantined; the model gets no pay/sign tool.

Demo: https://memoryguard.eyesonchain.xyz/
Video: [PASTE_VIDEO_URL]
```

### Build log post

```text
Built ProofOps MemoryGuard for @sibylcap: load-bearing recall, a Sibyl-backed Agent ledger, exact causal memory IDs, fail-closed 503 with no fallback, and a receipt-bound OpenRouter planning path (current VPS generation receipt plus separately recorded synthetic restart evidence).

Evidence: https://memoryguard.eyesonchain.xyz/casework/evidence
Repo: https://github.com/seekitx/proofops-memoryguard

Base, Virtuals, and PMF are not claimed.
```

Publish two distinct public URLs, one per line in the private build page. If a post
platform has a length limit, keep the claim boundary and move the second link into a
reply rather than deleting `@sibylcap`.

## Honest partner and PMF fields

- Base: do not claim unless a product-relevant deployment and executed onchain action
  are visible and independently verifiable.
- Virtuals: do not claim unless a live native integration or ACP job actually runs.
- PMF: use `0 / not claimed` unless a public MemoryGuard-specific artifact can be
  checked by a judge within five minutes.

## Final truth review before ready

- Current VPS HTTPS page, `/health/ready`, `/api/runtime`, and
  `/api/v2/public-release` work in a private browser.
- The current VPS synthetic restart preserves the Casework state needed for
  Session B; the former Render restart is historical evidence and cannot be used
  as current private-data migration proof.
- Any claimed current remote-model run must have a non-null receipt; the separate successful current-VPS request has that receipt; the initial degraded attempt remains recorded.
- Video is 2–5 minutes; its fresh-session recall segment is continuous and unedited, with commit hash/time visible.
- Video shows the same action fingerprint and different runtime instance IDs.
- Video shows the exact causal dispute, prompt text quarantine, changed tool path,
  and fail-closed behavior.
- Both post URLs are public and include `@sibylcap`.
- README, evidence page, build page, video, and posts use the same claims.
- Only after every item above: mark `ready for judging` before
  `2026-09-10 23:59 UTC` (`2026-09-11 07:59` Beijing time).
