# MemoryGuard final submission pack

This file contains copy-ready text. Replace placeholders only after the linked
artifact exists. Never paste the private build-page edit URL into the repository.

## Public repo URL

`https://github.com/seekitx/proofops-memoryguard`

Saved to the private build page on 2026-09-05.

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

## Honest partner and PMF fields

- Base: do not claim unless a product-relevant deployment and executed onchain action
  are visible and independently verifiable.
- Virtuals: do not claim unless a live native integration or ACP job actually runs.
- PMF: use `0 / not claimed` unless a public MemoryGuard-specific artifact can be
  checked by a judge within five minutes.

## Final truth review before ready

- Stable HTTPS page and `/health/ready` work in a private browser.
- Render restart preserves Session A memory for Session B.
- Video is one continuous, unedited 2–5 minute capture and shows commit hash/time.
- Video shows the same action fingerprint and different runtime instance IDs.
- Video shows the exact causal dispute, prompt text quarantine, changed tool path,
  and fail-closed behavior.
- Both post URLs are public and include `@sibylcap`.
- README, evidence page, build page, video, and posts use the same claims.
- Only after every item above: mark `ready for judging` before
  `2026-09-10 23:59 UTC` (`2026-09-11 07:59` Beijing time).
