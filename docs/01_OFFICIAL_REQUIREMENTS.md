# Official requirements and acceptance map

## Outcome

The project is eligible only if Sibyl Memory is on the critical path. Base and
Virtuals can increase the score, but neither can rescue a project that fails the
memory deletion test.

| Official requirement | MemoryGuard implementation | Final evidence still needed |
|---|---|---|
| Persist meaningful context | `SibylMemoryAdapter` writes trusted observations into WARM entities and COLD journal | Runtime capture of Session A write |
| Recall in a fresh session | `MemoryGuard.decide` performs exact Sibyl lookup; browser Session B has a new session ID and no reused page state | Unedited restart/fresh-session video |
| Recall changes behavior | Same intent changes from READY draft to DENY after trusted dispute/revocation | Decision diff in video and public proof |
| Deletion test | Missing/invalid Sibyl Adapter returns `MEMORY_UNAVAILABLE`; no production fallback | Run deletion scenario when testing is authorized |
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
