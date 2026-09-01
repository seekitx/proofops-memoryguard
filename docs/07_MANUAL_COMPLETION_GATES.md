# Manual completion gates

## Conclusion

The repository is a contest-oriented implementation, not yet a complete submission.
The remaining items require the owner's account, wallet, public publishing choice,
or permission to run builds/tests. They cannot be honestly completed by source code
alone.

At the official-source research snapshot on 2026-08-31, registration closed at
23:59 UTC, the build window was September 1–10 UTC, judging September 11–12, and
winners September 13–15. Recheck the live site before relying on these dates.

## Gates in priority order

| Gate | Current state | Acceptance evidence | Reject if |
|---|---|---|---|
| Registration/team | **Registered; private build page opened read-only** | Keep the private build-page link/account confirmation privately | Public page alone or lost build-page access |
| Contest-period implementation | **Window open; in progress** | Substantive Agent/runtime work in reviewable in-window commits | Pre-build files committed later and relabeled |
| Real Agent behavior | **Source implemented; runtime unverified** | Real remote model + Agent invokes decision/safety tools; fresh-process recall changes its chosen action | Deterministic dev planner, memory service, or chat shell only |
| Prior Work boundary | Awaiting owner review | Pre-build snapshot and in-window delta are both explicit | Filesystem/Git dates imply a false build story |
| Local dependency install | Not run | Exact official SDK installs from clean environment | README exists but runtime was never started |
| Python tests | Supplied, not run | Focused suites pass with captured output | Presence of tests is called “passing” |
| Contract compile/test | Supplied, not run | Clean Hardhat compile/test output | Source alone is called deployed/verified |
| Real fresh-session Sibyl run | Not run | Separate A/B processes; same action hash; causal DENY | Browser visual reset only |
| Deletion test | Not run | Removing Sibyl yields fail-closed 503 and no fallback | Static expected-output box only |
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
| Final repo push/history | Public contest-period commits pushed through `6662336` before the current evidence-hardening change | Reviewable contest-period commits on public repo | One opaque dump or unpushed changes |

## Owner decisions before any irreversible action

- authorize dependency installation and test/compile execution;
- choose and authorize the hosting provider if cost or account access is involved;
- choose Base Sepolia or mainnet after partner eligibility is confirmed;
- approve contract deployment and every wallet prompt;
- approve public video/posts and any customer/PMF claim;
- review the public commit history and Prior Work wording before final submission;
- submit through the contest account.

No private key, wallet seed, service token, or customer dispute text should be put in
the repository, video, logs, or support messages.
