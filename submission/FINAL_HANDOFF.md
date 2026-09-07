# MemoryGuard submission handoff

## Judge links

- Project: https://memoryguard.eyesonchain.xyz/
- Video: https://memoryguard.eyesonchain.xyz/assets/memoryguard-demo.mp4
- Evidence: https://memoryguard.eyesonchain.xyz/casework/evidence
- Source: https://github.com/seekitx/proofops-memoryguard (MIT)
- Team: ProofOps Labs
- Builder: [@reslibadsi28525](https://x.com/reslibadsi28525) (public entrant identity)

## Pitch

MemoryGuard remembers risk across sessions, stops only the work that depends on
it, and refuses to resume until the evidence and authority are valid again.
Same action. Fresh process. Remembered risk. Different authority.

## Memory note

Persist: scoped risks, task dependencies, immutable decisions, resolutions and
review records in the official Sibyl workspace store. Untrusted instructions are
quarantined as fingerprints, not added to authority-bearing prompts.

Recall: the fresh server process reloads the durable workspace before evaluating
the same action. The film shows an actual Docker restart, different runtime IDs,
an unchanged business commit and the same action fingerprint.

Change: READY becomes DENY. Dependent work stops; unrelated work remains READY.
Resolving one risk is insufficient. Resolving both still requires explicit human
reconsideration. A new READY proof remains non-executable.

Without this memory, durable risk and review context cannot be recovered. The
workflow fails closed instead of silently switching to another business store.

## Film

- 1920 × 1080; 189.717 seconds; English narration.
- Core: 00:16.46–01:21.46, continuous and normal speed, no internal cuts.
- Full raw recording retained locally; the final film selects raw seconds 0–65.
- Eleven recording checks passed; three real, structured remote-model receipts.
- Isolated webpage capture; no bookmarks or personal browser profile.
- Word-timestamp subtitles follow the identical audio delays and speed factors.
- Previously approved voice; the owner should listen once to the new assembly.

- Closing card: MemoryGuard and ProofOps Labs. No narration-source credit.
- Recorded READY response and corrected captions; core footage and timing unchanged.

## Verified outcomes

| Situation | Observed result | Recovery requirement |
|---|---|---|
| Same action before risks | READY, non-executable | Finalization remains separate |
| Same action after actual restart | DENY with two causal risks | Resolve both risks |
| Dependent task | SUSPENDED, effective policy DENY | Valid recovery evidence |
| Unrelated task | READY, non-executable | Its own gates still apply |
| Only one risk resolved | DENY | Resolve remaining risk |
| Both risks resolved | Needs human reconsideration | Explicit reviewer action |
| Explicit reconsideration | New READY proof | Still no execution authority |

These are synthetic scenarios on a real hosted Sibyl workspace. They are not
customer adoption, private-data migration proof or an independent security audit.
See [the recording record](evidence/heritage-4692b42.json).

## Partner scope

Base: previously verified Sepolia audit-anchor transaction
`0xc518b7b197ddd2b9c4d30a3a61846a0773489b9082bdd96b287ce82758b3704b`.
The film displays the dated transaction proof; it does not send a new transaction.

Virtuals: native ACP job **77243** with **Otto AI - Market Alpha Agent** is
**COMPLETED**, including buyer self-evaluation and independently checked Base
mainnet transaction receipts. Actual price: **0.01 USDC**. See
[full receipt](evidence/virtuals-otto-77243.json). The film now includes two clearly
labelled recorded-receipt cards for this completed purchase. The original
MemoryGuard wallet is both buyer and evaluator. This is external-news delivery,
not an independent safety review; news cannot resolve a risk or approve a task.
Gloria job 1003558157 remains separate historical evidence with pending settlement.

PMF and partner multipliers are not claimed as awarded results.

## Submission and deadline

Official requirements: https://hack.sibyllabs.org/submissions and
https://hack.sibyllabs.org/rules . Deadline: September 10, 2026 at 23:59 UTC
(September 11, 07:59 in China). The private portal is authoritative for Ready.
Do not publish its private editing link.

Two owner-published post URLs:
- https://x.com/reslibadsi28525/status/2096832643967172716
- https://x.com/reslibadsi28525/status/2096832605652144230

Live Chrome inspection verified both post texts and all three tags on September 7.
The demo post links to a historical release. The build-log post links to the
now-excluded docs/JUDGE_OUTCOMES.md. The owner has confirmed publishing a link correction; its reply URL has not been
independently rechecked. Internal docs are not reintroduced.

Correction wording provided to the owner (owner reports posted):

> Updated MemoryGuard demo and evidence: https://memoryguard.eyesonchain.xyz/casework/evidence — same action, real service restart, remembered risk, explicit human reconsideration. The old docs link has moved here. @sibylcap @base @virtuals_io

The official private portal was reloaded after saving: all four artifact
milestones are checked and **Marked ready for judging** is enabled. It points to
the hosted film URL (updated from 2:58 to 3:10 with the Otto receipt). The owner can revise/unmark before close.

## Release boundary

Business runtime: `8a4e5216aa0ab56c6718af9011a47b4a06013b2b`.
Recorded workbench UI: `4692b4268bc46fc82513eb6c9e343a1ead1364dd`.
Later video/evidence-only changes are separate from that business release.
The existing runtime release results and CI remain linked from README. No new
compilation or full test suite was run for the presentation update.
