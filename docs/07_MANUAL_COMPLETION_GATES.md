# Manual completion gates


> Latest update, 2026-09-06: the initial degraded model attempt below is historical. A separate current-VPS request using `openai/gpt-4.1-mini` now passed with a real generation receipt on build `a4b216e`. See [public receipt](../output/final-release-20260906/new-vps/remote-model-receipt-public.json). Virtuals Job #76728 passed its deadline without funding or delivery; no completion is claimed. Current-VPS continuous video and public submission remain open.

## Conclusion

The repository is a contest-oriented implementation, not yet a complete submission.
The authorized Python checks, local two-process A/B exercise, historical Render
OpenRouter structured-model calls, and isolated missing-Sibyl fail-closed probe
are complete. The current VPS HTTPS endpoint has passed read-only readiness,
runtime, and public-release checks on the final candidate SHA. A synthetic current
VPS Casework A/B also passed across a real `memoryguard` container restart, with
the same action fingerprint, `READY` → `DENY`, related-work suspension,
unrelated-work continuation, and `executable=false` throughout. This does not
prove migrated private-data persistence. The initial remote investigation degraded. A separate request after the model switch returned a validated live receipt; both attempts are preserved.
Continuous recording, publication choices, the owner's account, and wallet
approval also remain open; the former Render restart evidence remains historical.
They cannot be honestly completed by source code or local JSON alone.

At the official-source research snapshot on 2026-08-31, registration closed at
23:59 UTC, the build window was September 1–10 UTC, judging September 11–12, and
winners September 13–15. Recheck the live site before relying on these dates.

## Gates in priority order

| Gate | Current state | Acceptance evidence | Reject if |
|---|---|---|---|
| Registration/team | **Registered; private build page opened read-only** | Keep the private build-page link/account confirmation privately | Public page alone or lost build-page access |
| Contest-period implementation | **Window open; in progress** | Substantive Agent/runtime work in reviewable in-window commits | Pre-build files committed later and relabeled |
| Real Agent behavior | **Current VPS synthetic A/B passed; current remote receipt passed** | The public VPS evidence files record a real `memoryguard` restart, same action fingerprint, `READY` → `DENY`, related work stopped, unrelated work continued, and all results `executable=false`; a separate remote investigation returned `REMOTE` with a validated generation receipt | Historical Render output or an HTTP 200 degraded response is presented as a successful current remote-model call |
| Prior Work boundary | Awaiting owner review | Pre-build snapshot and in-window delta are both explicit | Filesystem/Git dates imply a false build story |
| Local dependency install | **Passed on Python 3.11.15** | Official `sibyl-memory-client==0.7.0` and project dev dependencies installed in `.venv` | README exists but runtime was never started |
| Python tests | **32 passed on 2026-09-05** | `.venv/bin/python -m pytest` completed after the public Render evidence, judge benchmark, readiness degradation, and rate-limit tests were added | Presence of tests is called “passing” |
| Public judge benchmark | **12/12 local checks passed on clean commit** | Committed JSON/Markdown linked from `/evidence`, with `git_dirty_at_capture=false` | Self-generated checks are called independent evaluation or PMF |
| Contract compile/test | Passed in candidate unified release gate | Clean Hardhat compile/test output | Source alone is called deployed/verified |
| Real fresh-session Sibyl run | **Current VPS synthetic restart A/B passed; current-VPS continuous capture remains open** | Current VPS evidence has separate runtime IDs, the same action hash, exact causal `DENY`, related-task stop/unrelated-task continuation, and no executable result; the separate receipt-bound remote run passed; an unedited fresh-session video segment is still required | Historical Render JSON or the degraded remote attempt is said to prove a current successful remote-model run |
| Missing-Sibyl fail-closed probe | **Passed in isolated environment** | `find_spec` is absent; readiness and Agent run return 503; `executable=false` | The normal environment is mutated or a fallback succeeds |
| Contest deletion capture | **Not complete** | Continuous recording of the isolated setup/removal and fail-closed result accepted by the live rubric | Missing-SDK probe is relabelled as deletion of an existing database |
| Public HTTPS deployment | **Current VPS HTTPS/readiness/runtime/public-release and synthetic restart A/B passed** | <https://memoryguard.eyesonchain.xyz/>, `/health/ready`, `/api/runtime`, `/api/v2/public-release`, `/casework/evidence`, and the new-VPS restart evidence on SHA `a4b216e73f2eed86ef2e07e2fdece4b48728190c`; scope is synthetic only and does not prove private-data migration persistence | Historical Render A/B or a random Quick Tunnel URL is called current VPS private-data persistence proof |
| Base deployment | Base Sepolia deployment recorded; multiplier unclaimed | Owner-approved deploy tx and contract address | Old BSC address or config placeholder |
| Base exercised action | Base Sepolia audit anchor recorded; demo inclusion pending | Wallet-confirmed anchor tx plus verified receipt/event/root | Deploy tx only, pending tx, or screenshot |
| Base multiplier wording | Blocked on evidence/rule confirmation | Partner rule confirmed plus exercised integration | “Prepared” or testnet ambiguity treated as credit |
| Virtuals multiplier | Deferred/not claimed | Real native integration and transaction | Logo/import-only integration |
| PMF bonus | Missing/not claimed | Public waitlist, pilot, user interviews, or usage artifact | Old SafeHire users/evidence relabeled |
| Demo video | Missing | Public 2–5 minute video with a continuous unedited fresh-session recall segment | Edited fresh-session recall segment or fake deletion result |
| Two public posts | Missing | Two public URLs with currently required tags | Draft text only |
| Private build-page fields | **Repo + Memory fields saved on 2026-09-05; video + two posts missing** | Add published video/posts, recheck wording, then save again | Draft text or private-link possession alone |
| Private build-page submission | Not marked ready | Dashboard confirmation | Public repo alone |
| Final repo push/history | **Reviewable code/evidence commits pushed; current status must be rechecked after every sync** | Public contest-period commits and local/remote HEAD equality immediately before final submission | One opaque dump or unpushed changes |

## Owner decisions before any irreversible action

- separately authorize contract compilation if it is still wanted;
- choose Base Sepolia or mainnet after partner eligibility is confirmed;
- approve contract deployment and every wallet prompt;
- approve public video/posts and any customer/PMF claim;
- review the public commit history and Prior Work wording before final submission;
- submit through the contest account.

No private key, wallet seed, service token, or customer dispute text should be put in
the repository, video, logs, or support messages.
