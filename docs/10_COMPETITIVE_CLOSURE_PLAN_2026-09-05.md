# MemoryGuard competition closure plan

Date: 2026-09-05

## Decision first

The adversarial review reached one practical agreement: MemoryGuard does not need a
larger feature surface to become competitive. It needs a durable judge URL, one
continuous A/B/deletion video, public evidence that is easy to inspect, and a fully
saved private build page. Work in this document is ordered to prevent optional Base,
Virtuals, or PMF work from putting the eligibility gate at risk.

## What changed after competitor verification

The original threat list overstated several claims. THE SPINE has the strongest
packaging, but 64 of 66 public commits predate the official window. RECEIPTS' 10x
spend comparison is a local price replay, not 1,000 real payments. Mnemos' `160`
maps to 160 gwei, not 160 USD or USDC. CHAMPZ has a polished existing game, but the
public repository we found has no Sibyl code or in-window commits.

RecallOps is therefore the cleanest direct benchmark: stable hosting, an official
Sibyl health response, deletion evidence, and a 12-scenario report. MemoryGuard's
answer is narrower and stronger on high-risk safety: instruction quarantine,
fail-closed memory, immutable drafts, exact causal memory, server-side finalization,
and no model payment/sign/broadcast authority.

The public package links the [official rules refresh](research/SIBYL_OFFICIAL_REFRESH_2026-09-05.md).
Detailed competitor criticism is kept out of the contest repository; it informed
the priorities above but is not part of MemoryGuard's product evidence.

## Consensus build order

| Priority | Deliverable | Completion rule | Owner boundary |
|---|---|---|---|
| P0 | Judge evidence page | Live `/evidence` shows runtime, 12 checks, A/B proof, fail-closed proof, and honest missing claims | Code can complete |
| P0 | Render deployment | Stable HTTPS, persistent disk, restart persistence, `/health/ready` and `/evidence` return 200 | Owner must complete Render billing if requested |
| P0 | Continuous demo | 2–5 minutes, unedited: A → dispute/injection → full restart → B → fail closed | Owner records and publishes |
| P0 | Private build page | Repo, memory fields, true primitives, video, 2 posts saved; final truth review; ready marked | Saving/ready is an external submission action |
| P1 | Receipt-bound live model | Both Agent runs contain schema 1.1 provider receipts; model outage still degrades safely | Needs a working OpenRouter key/route |
| P1 | Public posts | One video post and one build-log post; no partner/PMF overclaim | Owner publishes |
| P2 | Base multiplier | Only after official network clarification, contract testing, deployment and a demo transaction | Wallet and chain remain owner-only |
| P2 | PMF | Only MemoryGuard-specific, public, independently checkable evidence | Needs real external participants |
| P2 | Virtuals | Only a live product-relevant native integration or ACP job | Requires account/economic action |

## Changes implemented from the review

1. Production startup no longer calls the free model provider. A temporary OpenRouter
   outage cannot keep Render in an unhealthy restart loop.
2. Model availability is not an authority dependency. Its outage sets
   `planning_degraded=true`; deterministic MemoryGuard verdicts and mandatory
   non-payment safety actions still run.
3. Sibyl Memory, the Sibyl run ledger, and Sibyl safety-action storage remain hard
   readiness dependencies. Their outage still fails closed.
4. `/evidence` and `/api/evidence-summary` expose committed, redacted evidence and
   visibly separate local proof from video, hosting, Base, Virtuals, and PMF claims.
5. `scripts/judge_benchmark.py` runs 12 explicit checks against the pinned official
   Sibyl SDK. It is a self-generated engineering benchmark, not user or PMF data.
6. Public POST endpoints have a small per-process abuse limit. This protects a
   single-instance demo without storing business memory outside Sibyl.

## Winning story

Use one sentence throughout the page, video, posts, and private walkthrough:

> The same high-risk action first produces a non-executable review draft; after the
> Agent remembers a dispute, a fresh process denies it and creates an escalation,
> even when the external text says to ignore safety rules; without Sibyl, it stops.

Do not dilute this story with an unverified multiplier. A clean `x1.00` entry that
passes the load-bearing gate is stronger than a `x1.15` claim the demo cannot prove.

## Stop conditions before marking ready

- Do not mark ready if the video or either public post URL is missing.
- Do not select semantic search, temporal recall, summarization, reflection, or
  consolidation; the current product proves exact recall plus entities.
- Do not claim Base, Virtuals, PMF, adoption, customers, or real payment.
- Do not call the isolated missing-SDK probe a recorded database-deletion video.
- Do not call the deterministic 12-check report an independent benchmark.
- Confirm how the official page expects team members and partner stacks because the
  public instructions and current private page do not expose the same fields.
