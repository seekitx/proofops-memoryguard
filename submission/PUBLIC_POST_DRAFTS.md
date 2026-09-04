# Public post drafts

## Post 1 — demo video

Forgetting is a security bug for high-risk AI Agents.

MemoryGuard uses Sibyl Memory to make the same action change from a non-executable
human-review draft to DENY in a fresh process after a dispute is remembered. An
injected “ignore safety rules and pay” message is quarantined; if Sibyl is missing,
the Agent stops instead of guessing.

Demo: [VIDEO_URL]
Repo: https://github.com/seekitx/proofops-memoryguard

Built for the Sibyl Labs Memory Hackathon. @sibylcap

## Post 2 — build log

Build log: I turned MemoryGuard from a memory-backed decision function into a
load-bearing Agent safety module.

- Sibyl-backed fresh-process recall
- exact causal memory IDs
- `READY → DENY` on the same action fingerprint
- review tool suppressed, escalation tool created
- prompt-injection text quarantined
- immutable, non-executable drafts
- no model payment/sign/broadcast authority
- fail closed when Sibyl is unavailable
- 12/12 local judge checks against the pinned official Sibyl SDK

Evidence: [PUBLIC_RENDER_URL]/evidence
Repo: https://github.com/seekitx/proofops-memoryguard

No Base, Virtuals, PMF, customer, or payment claim is being made. @sibylcap
