# Sibyl Labs Hackathon official research

Status captured on 2026-08-31 at approximately 17:10 UTC. Dates and public counts
can change; re-check the official pages before final submission.

## Executive finding

This is a memory competition, not a generic agent or blockchain competition. The
first gate is binary: Sibyl Memory must be load-bearing. A fresh session must recall
previously written state and use it to change a decision, action, or result. If the
Sibyl layer is removed and the claimed product still works, the project is rejected
before scoring.

At capture time registration was still open until 2026-08-31 23:59 UTC. The build
window is 2026-09-01 through 2026-09-10, judging is September 11–12, and winners are
announced September 13–15. All deadlines are UTC.

## Official requirements

Source: [Sibyl Hackathon rules](https://hack.sibyllabs.org/rules), accessed
2026-08-31.

- Gate: persist context, recall it in a genuinely fresh session, and make that
  recall change behavior.
- Rubric: load-bearing memory 40, innovation 25, technical execution 20, pitch 15.
- PMF bonus: up to 10 points, but only for public evidence a judge can verify.
- Partner multiplier: first verified stack adds 15%, second adds 10%, capped at
  1.25. Sibyl is mandatory and is not a multiplier.
- Base: deployment is the floor; an exercised wallet operation, x402 payment, B20
  read, or contract interaction can qualify. The rule text does not clearly say
  whether Base Sepolia always receives the multiplier, so that must be confirmed in
  the partner workshop.
- Virtuals: a real ACP job, registered or transacting Agent, or another exercised
  Virtuals-native integration can qualify.
- Submission: public MIT/Apache repository with real history, a 2–5 minute demo with
  an unedited fresh-session recall moment, a README with the memory critical path and
  Prior Work declaration, plus two public posts.

Source: [Sibyl submission page](https://hack.sibyllabs.org/submissions), accessed
2026-08-31.

- Only registered teams can submit.
- Submission happens through the private build-page link received after registration.
- The build page needs repository, video, team/partner stacks, and a memory note.

## Current leaderboard and “past winners” boundary

Source: [Sibyl leaderboard](https://hack.sibyllabs.org/leaderboard), accessed
2026-08-31.

The page showed 348 registered teams and no scores. It says standings appear after
judging closes on September 12. Therefore there are no verifiable past Sibyl
Hackathon winners to copy at this time. Any document claiming otherwise would be
fabricated.

For a legitimate adjacent comparison, the official Base article
[Onchain Summer Buildathon winners](https://blog.base.org/announcing-the-onchain-summer-buildathon-winners)
describes repeated winning criteria: the product works, offers a creative answer to
a real problem, is usable, has clear UX, and shows credible growth potential. Those
are patterns from a partner ecosystem, not winners of this Sibyl event.

The useful synthesis is:

1. show one complete, repeatable loop rather than many shallow integrations;
2. make the memory-caused behavior change visually undeniable;
3. keep the first use simple enough for a judge to reproduce;
4. attach public evidence to every partner or adoption claim;
5. preserve a credible path beyond the demo.

## Sibyl Memory implementation facts

Sources:

- [Sibyl Memory official repository](https://github.com/Sibyl-Labs/Sibyl-Memory)
- [Sibyl Memory documentation](https://docs.sibyllabs.org/)
- Official repository HEAD observed locally as commit
  `63a5ea940245461bdb8b55538043c98f685b23f0`; its client package declared version
  `0.7.0` at research time.

The official Python SDK is `sibyl-memory-client`. Its documented entry point is:

```python
from sibyl_memory_client import MemoryClient

memory = MemoryClient.local(".data/sibyl-memory.db", tenant_id="tenant-id")
memory.set_entity("vendor-risk", "vendor/acme", {"dispute_status": "open"})
record = memory.get_entity("vendor-risk", "vendor/acme")
memory.write_event(acted=["vendor dispute opened"])
```

The useful storage tiers are:

- HOT state for replaceable current-session state;
- WARM entities for the single current truth about a vendor, policy, or subject;
- COLD journal for append-only observations and decisions;
- REFERENCE for static policy documents;
- ARCHIVE for retired records.

MemoryGuard should use exact WARM entity lookup for authorization. Full-text search
may help explanation, but fuzzy hits must never grant authority.

## Product decision derived from the evidence

MemoryGuard will make Sibyl load-bearing by refusing to produce an actionable
decision when the production Memory Adapter is missing or invalid. Session A stores
a trusted dispute/revocation and quarantines a malicious instruction. A new Session B
recalls the trusted fact, then changes the same payment intent from a non-executable
READY draft to DENY. Base anchoring makes the proof externally reviewable, but it
cannot replace the mandatory Sibyl fresh-session loop.

## Items still requiring a human

- Confirm that the team registered before 2026-08-31 23:59 UTC and retained the
  private build-page link.
- Ask the Base workshop whether the intended network must be mainnet for multiplier
  credit.
- Complete an actual Base wallet confirmation and independent receipt readback before
  claiming the Base stack.
- Collect public PMF evidence before claiming any PMF bonus.
- Record the final unedited 2–5 minute fresh-session video and publish both posts.
