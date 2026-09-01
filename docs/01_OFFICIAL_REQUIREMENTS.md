# Official requirements and acceptance map

## Outcome

The project is eligible only if Sibyl Memory is on the critical path. Base and
Virtuals can increase the score, but neither can rescue a project that fails the
memory deletion test.

| Official requirement | MemoryGuard implementation | Final evidence still needed |
|---|---|---|
| Persist meaningful context | `SibylMemoryAdapter` writes trusted observations into WARM entities and COLD journal; local Session A write observed | Unedited Session A capture and public proof |
| Recall in a fresh session | `MemoryGuard.decide` performs exact Sibyl lookup; local A/B run observed distinct runtime IDs and exact recall | Unedited restart/fresh-session video |
| Recall changes behavior | Local deterministic Agent path changed the same intent from READY draft to causal DENY | Decision diff with a real remote model in video and public proof |
| Deletion/fail-closed test | Missing SDK/Adapter directly returned `503 MEMORY_BACKEND_UNAVAILABLE` for decision and Agent run; no fallback | Continuously record isolated removal/setup; do not relabel it as deletion of an existing database |
| Public repo and real history | Public repository exists; implementation is split into reviewable commits | Commit and push after owner review |
| README code pointers | README names exact write/read/finalize files | Re-check links after final file layout |
| 2–5 minute demo | Single Session A → Session B story is scripted | Record and publish |
| Prior Work | `docs/04_PRIOR_WORK.md` separates SafeHire from contest work | Keep dates and commit hashes current |
| PMF bonus | No bonus claimed without public evidence | Interview/pilot/waitlist artifact |
| Base multiplier | Memory proof anchor contract and wallet-confirmed plan | Deploy, execute, and independently verify receipt |
| Virtuals multiplier | Deferred | Real ACP/registration/transaction only |

## Rejection conditions

- Sibyl is imported but not read on the decision path.
- A fixture, JSON file, browser state, or alternate database silently replaces Sibyl.
- Session B is only a visual reset while the decision comes from in-process state.
- Free-form external text directly alters authority.
- A DENY decision can still generate an execution capability.
- Base is claimed from BSC evidence, a deployment without an exercised action, or an
  unverified transaction hash.
- Prior SafeHire evidence is presented as MemoryGuard usage or PMF.
- The repository, demo, README, two posts, or private build-page submission is missing.

Official sources are recorded in
`docs/research/SIBYL_HACKATHON_OFFICIAL_RESEARCH_2026-09-01.md`.
