# Manual completion gates

## Conclusion

The repository is a contest-oriented implementation, not yet a complete submission.
The authorized Python checks, local two-process A/B exercise, and isolated
missing-Sibyl fail-closed probe are complete. The remaining items require a remote
model credential, continuous recording, hosting/publication choices, the owner's
account, or wallet approval. They cannot be honestly completed by source code or
local JSON alone.

At the official-source research snapshot on 2026-08-31, registration closed at
23:59 UTC, the build window was September 1–10 UTC, judging September 11–12, and
winners September 13–15. Recheck the live site before relying on these dates.

## Gates in priority order

| Gate | Current state | Acceptance evidence | Reject if |
|---|---|---|---|
| Registration/team | **Registered; private build page opened read-only** | Keep the private build-page link/account confirmation privately | Public page alone or lost build-page access |
| Contest-period implementation | **Window open; in progress** | Substantive Agent/runtime work in reviewable in-window commits | Pre-build files committed later and relabeled |
| Real Agent behavior | **Deterministic Agent path exercised; remote model pending** | Real remote model + Agent invokes decision/safety tools; fresh-process recall changes its chosen action | Deterministic dev planner is called remote-model proof |
| Prior Work boundary | Awaiting owner review | Pre-build snapshot and in-window delta are both explicit | Filesystem/Git dates imply a false build story |
| Local dependency install | **Passed on Python 3.11.15** | Official `sibyl-memory-client==0.7.0` and project dev dependencies installed in `.venv` | README exists but runtime was never started |
| Python tests | **20 passed on 2026-09-01** | `.venv/bin/python -m pytest` completed in 0.08 s after the Keccak dependency fix | Presence of tests is called “passing” |
| Contract compile/test | Supplied, not run | Clean Hardhat compile/test output | Source alone is called deployed/verified |
| Real fresh-session Sibyl run | **Local two-process behavior observed; continuous video missing** | One unedited capture of separate A/B processes, same action hash, exact causal DENY, and visible commit | JSON alone is said to prove the restart/checkout |
| Missing-Sibyl fail-closed probe | **Passed in isolated environment** | `find_spec` is absent; readiness and Agent run return 503; `executable=false` | The normal environment is mutated or a fallback succeeds |
| Contest deletion capture | **Not complete** | Continuous recording of the isolated setup/removal and fail-closed result accepted by the live rubric | Missing-SDK probe is relabelled as deletion of an existing database |
| Public HTTPS deployment | Missing | Public URL, persistent disk, redeploy persistence | Ephemeral filesystem loses memory |
| Base deployment | Missing | Owner-approved deploy tx and contract address | Old BSC address or config placeholder |
| Base exercised action | Missing | Wallet-confirmed anchor tx plus verified receipt/event/root | Deploy tx only, pending tx, or screenshot |
| Base multiplier wording | Blocked on evidence/rule confirmation | Partner rule confirmed plus exercised integration | “Prepared” or testnet ambiguity treated as credit |
| Virtuals multiplier | Deferred/not claimed | Real native integration and transaction | Logo/import-only integration |
| PMF bonus | Missing/not claimed | Public waitlist, pilot, user interviews, or usage artifact | Old SafeHire users/evidence relabeled |
| Demo video | Missing | Public unedited 2–5 minute URL | Edited montage or fake deletion result |
| Two public posts | Missing | Two public URLs with currently required tags | Draft text only |
| Private build-page fields | **All fields currently empty; draft prepared locally** | Saved repo, video, two posts, deletion impact, walkthrough, and honest primitives | Draft text or private-link possession alone |
| Private build-page submission | Not marked ready | Dashboard confirmation | Public repo alone |
| Final repo push/history | Public contest-period runtime build pushed through `5442f65`; evidence documentation is the current change | Reviewable contest-period commits on public repo | One opaque dump or unpushed changes |

## Owner decisions before any irreversible action

- separately authorize contract compilation if it is still wanted;
- choose and authorize the hosting provider if cost or account access is involved;
- choose Base Sepolia or mainnet after partner eligibility is confirmed;
- approve contract deployment and every wallet prompt;
- approve public video/posts and any customer/PMF claim;
- review the public commit history and Prior Work wording before final submission;
- submit through the contest account.

No private key, wallet seed, service token, or customer dispute text should be put in
the repository, video, logs, or support messages.
