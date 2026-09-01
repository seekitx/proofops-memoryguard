# Sibyl private build-page draft

## Safety boundary

This file contains only public submission copy. It intentionally does not contain
the private team URL, edit token, email address, wallet information, API key, or any
other account secret.

The private page was inspected read-only on 2026-09-01. At that time all four
milestones were empty: public repo, demo video, two posts, and memory fields. Nothing
was saved and the build was not marked ready.

## Field-by-field draft

### Public repo URL

```text
https://github.com/seekitx/proofops-memoryguard
```

This public URL is ready to save after action-time approval.

### Demo video URL

Leave empty until a public, unedited 2–5 minute video exists. A hosted product URL or
an edited montage is not a substitute.

### Post URLs

Leave empty until two distinct public X or Farcaster posts exist. Put one URL per
line. One post should contain the demo; the other should be a build log. Use the
current official tags at publication time.

### What breaks when memory is deleted?

Do not submit this as a verified claim until the fresh-process and deletion captures
have actually passed.

```text
Without Sibyl Memory, the Agent cannot recall the persisted dispute or revocation that changes the same non-executable payment intent from READY review to BLOCK_AND_ESCALATE in a fresh process. Production refuses to start, and development returns MEMORY_BACKEND_UNAVAILABLE with no JSON, browser, or process-memory fallback.
```

### Memory walkthrough

The official page asks for exactly three lines. Do not submit them as verified until
the real A/B capture has passed.

```text
Persist: trusted typed payment limits, disputes, and revocations as versioned Sibyl entities; instruction-like external text is quarantined and only its hash is retained.
Recall in a fresh session: after a full Agent/API restart on the same Sibyl database, exact entity lookup retrieves the prior dispute and its causal observation ID; no browser or session state is reused.
Changes the Agent's decision/action: the identical non-executable payment intent moves from READY + human_review.prepare to DENY/BLOCK_AND_ESCALATE + operator_escalation.create; the review tool is suppressed and no payment tool is registered.
```

### Memory primitives

Select only these after the runtime evidence exists:

- `recall`
- `entities`

Do not select `semantic search`, `temporal / time-travel`, `summarization`,
`reflection`, or `consolidation`. COLD audit events alone do not prove time-travel
recall.

## Save/ready order

1. Complete the official SDK runtime, fresh-process, and deletion evidence.
2. Publish the unedited demo video and two posts.
3. Recheck every URL and claim against the evidence.
4. Save the build-page fields after explicit action-time approval.
5. The owner reviews the IP/feature license and marks the build ready before the UTC
   deadline.
