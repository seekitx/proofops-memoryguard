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

The fresh-process A/B behavior and fail-closed probe have now been observed. The
continuous video remains a separate publication gate.

```text
Deleting the persisted Sibyl state removes the recalled dispute, so the identical action can no longer produce the same causal DENY. If the official Sibyl SDK/Adapter is unavailable, production refuses to start and development decision/Agent endpoints return MEMORY_BACKEND_UNAVAILABLE with no JSON, browser, or process-memory fallback.
```

### Memory walkthrough

The official page asks for exactly three lines. These lines are now backed by the
local and public HTTPS A/B observations. The final video still needs to show the
restart continuously.

```text
Persist: trusted typed payment limits, disputes, and revocations as versioned Sibyl entities; instruction-like external text is quarantined and only its hash is retained.
Recall in a fresh session: after a full Agent/API restart on the same Sibyl database, exact entity lookup retrieves the prior dispute and its causal observation ID; no browser or session state is reused.
Changes the Agent's decision/action: the identical non-executable payment intent moves from READY + human_review.prepare to DENY/BLOCK_AND_ESCALATE + operator_escalation.create; the review tool is suppressed and no payment tool is registered.
```

### Memory primitives

Select only these; the required runtime evidence now exists:

- `recall`
- `entities`

Do not select `semantic search`, `temporal / time-travel`, `summarization`,
`reflection`, or `consolidation`. COLD audit events alone do not prove time-travel
recall.

## Save/ready order

1. Save the verified repo and memory fields after explicit action-time approval.
2. Publish the unedited demo video and two posts.
3. Recheck every URL and claim against the evidence.
4. Add the video/posts to the build page after explicit action-time approval.
5. The owner reviews the IP/feature license and marks the build ready before the UTC
   deadline.
