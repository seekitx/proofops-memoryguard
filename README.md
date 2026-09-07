# ProofOps MemoryGuard

**Team:** ProofOps Labs

**Builder:** [@reslibadsi28525](https://x.com/reslibadsi28525) (public entrant identity)

**Stacks:** Sibyl Memory; Base Sepolia audit anchoring; Virtuals / Otto completed external-news purchase.

## Judge entry — September 7 final presentation

MemoryGuard remembers risk across processes, stops only dependent work, and
requires valid resolutions plus explicit human reconsideration before a new READY
proof. READY is never a payment or execution capability.

- [Project introduction](https://memoryguard.eyesonchain.xyz/) · [English demo, 3:10](https://memoryguard.eyesonchain.xyz/assets/memoryguard-demo.mp4)
- [Current recording evidence](submission/evidence/heritage-4692b42.json) · [video timing and fingerprints](submission/evidence/video-manifest.json)
- [Runtime release result](submission/evidence/local-release-8a4e521.json) · [runtime CI](https://github.com/seekitx/proofops-memoryguard/actions/runs/34093259925)
- [Hosted workbench](https://memoryguard.eyesonchain.xyz/casework) · [public evidence](https://memoryguard.eyesonchain.xyz/casework/evidence)

The business runtime remains `8a4e5216aa0ab56c6718af9011a47b4a06013b2b`.
The recorded interface is `4692b4268bc46fc82513eb6c9e343a1ead1364dd`, served
separately by the web proxy. Later media and evidence commits do not alter the
recorded workbench or business runtime. No new build or full test suite was run
for this presentation update.

The September 7 film contains an uncut, normal-speed 65-second sequence from a
120-second retained raw recording: READY, actual VPS Docker restart, same-action
DENY, scoped stop, investigation, and explicit reviewer reconsideration.
UTC timestamps and both commit identifiers remain visible. Three validated
remote-model receipts accompany the synthetic casework. English
narration uses word timestamps for captions. The voice was previously
owner-approved; the newly assembled film still needs the owner's final listen.

Base is a historical verified Sepolia audit anchor. Virtuals now has a real
completed native ACP job: **77243**, purchased by the original MemoryGuard wallet
from **Otto AI - Market Alpha Agent** for **0.01 USDC**. The provider accepted,
delivered a news report, and the buyer explicitly accepted delivery. An independent
Base mainnet RPC check confirms the creation, funding, submission and completion
transactions succeeded. [Full receipt](submission/evidence/virtuals-otto-77243.json)
· [Completion transaction](https://basescan.org/tx/0x2d888017553a27a515df29b8a0d5a0779ba78a20278c7be11afcbf5b3d076737).
The film shows dated receipt cards, not a live replay of these transactions.
News claims remain unverified; buyer acceptance is not independent security review
and cannot resolve MemoryGuard risks or override DENY. The model has no wallet authority.
The earlier [Gloria job](submission/evidence/gloria-status-20260907.json) remains
separate historical delivery evidence with pending settlement. PMF and awarded
partner multipliers are not claimed. Research and internal docs stay local.
Storage maintenance preserved all tables and row identifiers; only unused pages
were reclaimed. No SDK quota was changed. All three temporary recording roles
were revoked and returned HTTP 401 after cleanup.

Current load-bearing memory calls are
[`SibylWorkspaceStore.load/save`](src/proofops_casework/store.py).
[`CaseworkService`](src/proofops_casework/service.py) reloads that sole durable
workspace for risks, dependencies, resolutions and reconsideration.
See [the submission handoff](submission/FINAL_HANDOFF.md) for the judged path,
partner scope, deadline and remaining owner review.

## Current candidate

The hosted implementation reports `2.3.0-rc1` and API compatibility id
`casework-v2.2`. It supports scoped risk propagation, bounded investigation,
independent handoff, case-specific resolution, and explicit reconsideration.
Every result remains non-executable.

> **Forgetting is a security bug.** MemoryGuard gives high-risk AI Agents a
> persistent, inspectable reason to stop.

[![Sibyl Memory](https://img.shields.io/badge/Sibyl_Memory-load--bearing-c9ff4a?labelColor=171714)](https://github.com/Sibyl-Labs/Sibyl-Memory)
[![Base](https://img.shields.io/badge/Base-Sepolia_audit_anchor-0052ff)](https://base.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-f2efe6.svg)](LICENSE)

MemoryGuard remembers a trusted dispute or revocation across Agent sessions,
quarantines external instructions that try to rewrite that fact, and names the exact
memory that caused a decision to change. It is an entry for the 2026 Sibyl Labs
Hackathon.

**Build boundary:** the original Sibyl integration, decision kernel, web demo, Base
anchor contract, wallet transaction plan, and receipt verifier were committed as a
separately disclosed pre-build baseline. After the official 2026-09-01 00:00 UTC
window opened, this repository added a substantive `MemoryGuardAgent`: a real model
Seam, Sibyl-backed run ledger, verdict-gated tool executor, resumable runs, and
executor-generated inspectable traces. The deterministic Agent path, two-process
Sibyl recall, isolated missing-SDK fail-closed behavior, and a 12-check official-SDK
benchmark have now been exercised locally. The receipt-bound OpenRouter A/B on
the former Render HTTPS deployment passed across a real service restart; that run
is now historical evidence. The current VPS runtime is live at the current judge
URL below on candidate SHA `8a4e5216aa0ab56c6718af9011a47b4a06013b2b`, and its
read-only readiness, runtime, and public-release checks have passed. A current-VPS
synthetic Casework run also completed Session A `READY` → a real `memoryguard`
container restart → Session B `DENY`, with the same action fingerprint, different
runtime IDs, related work stopped, unrelated work continuing, and every result
`executable=false`. This evidence uses only a synthetic workspace
(`real_private_casework_touched=false`); it does not prove migrated private-data
persistence. An earlier VPS attempt degraded. The current recorded run returned three
validated GPT-4.1-mini receipts on the frozen runtime commit.
The recorded evidence distinguishes both attempts, the video, and Base evidence.
Two public post URLs have been saved to the submission portal; PMF remains unclaimed.

## Judge path — under two minutes

1. Open the [introduction and current film](https://memoryguard.eyesonchain.xyz/).
2. Watch 00:16.46–01:21.46: same action, actual restart, remembered risks and
   explicit reconsideration, without internal cuts or speed changes.
3. Inspect the [current recording record](submission/evidence/heritage-4692b42.json)
   and [release result](submission/evidence/local-release-8a4e521.json).
4. Find current memory reads/writes in
   [`SibylWorkspaceStore.load/save`](src/proofops_casework/store.py), called by
   [`CaseworkService`](src/proofops_casework/service.py).
5. Follow [the local Casework walkthrough](#run-the-current-casework-workbench-locally)
   to create your own scoped roles and reproduce risk/recovery behavior. Public
   workbench access requires credentials; the film and public evidence do not.

The following Interface discussion includes historical v1 foundations. The
current scoped v2 walkthrough and its evidence are the judging entry above.

## Where Sibyl is load-bearing

| Judge question | Exact source pointer |
|---|---|
| Where is memory written? | [`SibylMemoryAdapter.commit_observation`](src/proofops_memoryguard/adapters/sibyl.py) writes a WARM entity and COLD events. |
| Where is fresh-session memory read? | [`SibylMemoryAdapter.load_subject`](src/proofops_memoryguard/adapters/sibyl.py), called synchronously by [`MemoryGuard.decide`](src/proofops_memoryguard/module.py). |
| How does recall change behavior? | [`policy.decide`](src/proofops_memoryguard/policy.py) maps an exact open dispute or revocation to `DENY` and causal observation IDs. |
| What happens if Sibyl is removed? | [`UnavailableMemoryAdapter`](src/proofops_memoryguard/adapters/sibyl.py) raises; production wiring rejects every non-Sibyl Adapter. There is no JSON/database fallback. |
| How is memory pollution handled? | [`classify_observation`](src/proofops_memoryguard/policy.py) separates allowed typed facts from hashed, quarantined external text. |
| How is the proof bound? | [`proof.py`](src/proofops_memoryguard/proof.py) checks the observation hash chain, action fingerprint, decision root, policy root, and memory root. |
| Where does Agent behavior change? | [`MemoryGuardAgent.run`](src/proofops_memoryguard/agent.py) reduces the authoritative verdict to a closed tool set and generates the trace server-side. |
| Where are Agent runs persisted? | [`SibylAgentRunAdapter`](src/proofops_memoryguard/adapters/agent_ledger.py) writes run state and executor trace through the official Sibyl SDK. |
| Can the model pay? | No. [`adapters/model.py`](src/proofops_memoryguard/adapters/model.py) only selects an optional safe artifact from a bounded plan; no payment/sign/broadcast tool or Adapter is registered. Raw model prose is hashed for the trace, not persisted or shown as operator guidance. |

The WARM subject entity is the load-bearing decision memory. COLD events preserve
audit chronology and the REFERENCE document preserves policy metadata, but this
version does not claim that COLD/REFERENCE retrieval changes the decision or that it
implements temporal/time-travel recall.

If the stored Sibyl data is deleted, the remembered facts and the corresponding
behavior change disappear. Separately, the tested missing-SDK/Adapter condition makes
development decisions return `503 MEMORY_BACKEND_UNAVAILABLE`; production wiring
refuses to start without the official Adapter. Neither condition falls back to a
fixture or alternate memory store.

## Deep Module Interface

```python
receipt = guard.observe(observation)        # validate, classify, hash, commit
draft = guard.decide(payment_intent)        # exact recall, policy, causal proof
final = guard.finalize(draft.decision_id)   # reload, lock proof, plan/verify anchor

run = agent.run(GuardedPaymentGoal(intent)) # recall, plan, gate tools, persist trace
same = agent.inspect(run.run_id)             # pure read from Sibyl Agent ledger
next = agent.resume(run.run_id, signal)      # cancel, prepare anchor, or verify wallet tx
```

HTTP and browser code cannot submit their own verdict or replacement proof root.
`READY` is always a draft. There is no payment execution Adapter in this entry, so
the product never claims that it moved money.

Development defaults to a clearly labelled deterministic planner so the repository
can be inspected without a secret. Contest production refuses to start unless
`AGENT_MODEL_MODE=remote` and a real HTTPS model endpoint, model name, and API key
are configured. A configured model provider is not decision authority: if it is
temporarily unavailable, the Agent records `planning_degraded=true` and still runs
the deterministic verdict plus mandatory review/escalation action. Sibyl Memory,
the Sibyl run ledger, and Sibyl safety-action storage remain hard dependencies.
The authorized contest run also exercised strict structured output
through an OpenRouter free model across a full API restart; its generation IDs,
completion hashes, and legacy runtime-health binding limitation are recorded in
[`evidence/2026-09-01_OPENROUTER_HTTPS_EVIDENCE.md`](evidence/2026-09-01_OPENROUTER_HTTPS_EVIDENCE.md).
The historical Render run stored and trace-bound the receipt inside each schema
`1.1` Agent run; both sides passed after that service restart. See
[`evidence/2026-09-05_RENDER_OPENROUTER_AB.md`](evidence/2026-09-05_RENDER_OPENROUTER_AB.md).
The current VPS deployment has completed the synthetic restart/A/B. Its first
investigation degraded; the separately linked subsequent investigation has a
successful receipt. Neither is claimed as a remote-model A/B pair. A deterministic-planner screenshot is not claimed as real-AI
proof.

## Run the current Casework workbench locally

This walkthrough uses the current scoped Casework interface shown in the film.
It runs against the official Sibyl store, with a free deterministic investigator
for local development. It does not make remote-model calls, purchase a Virtuals
job or send a Base transaction. The hosted film's three real model receipts are
separate evidence; a deterministic local report is not a remote receipt.

### 1. Install and create local roles

Requirements: Python 3.11+, Git, and the official `sibyl-memory-client` dependency
installed by this project. Start from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/casework_create_credentials.py --directory .casework-private
```

The credential helper creates private files with restricted permissions:
- `.casework-private/registry.json`: hashed credentials and allowed roles/scopes.
- `.casework-private/operator-tokens.json`: local tokens for `owner`,
  `investigator`, `reviewer` and read-only `viewer`.

These roles share `tenant_demo` and `subject_demo`. Open the token file locally
and copy only the role you need into the workbench. Never paste tokens into a
public issue, recording or submission. The directory is ignored by Git. The
helper refuses to overwrite existing credentials; reuse the existing files
when restarting. These local tokens cannot access the hosted service.

### 2. Start the actual v2 API

Run these exports in the same terminal as the server. A separate local database
keeps this exercise apart from earlier `.data` workspaces.

```bash
unset CASEWORK_CONNECTORS_FILE CASEWORK_BASE_ANCHOR_ADDRESS CASEWORK_ANCHOR_ATTESTER
export APP_ENV=development
export CASEWORK_ENABLED=1
export CASEWORK_AUTH_FILE="$PWD/.casework-private/registry.json"
export SIBYL_MEMORY_PATH="$PWD/.casework-private/sibyl-memory.db"
export AGENT_MODEL_MODE=deterministic
export BUILD_COMMIT="$(git rev-parse HEAD)"
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/casework>. The local API root redirects here; the
hosted introduction page is served separately by Nginx. No frontend compilation
is required. Use `/api/runtime` to inspect the actual commit and runtime ID.
Keep the same checkout, exports, database and credential registry across restart.
Do not use `--reload` for restart evidence.

If reusing a terminal previously configured for live integrations, unset
`CASEWORK_CONNECTORS_FILE`, `CASEWORK_BASE_ANCHOR_ADDRESS` and
`CASEWORK_ANCHOR_ATTESTER` before this isolated exercise. Otherwise extra source
or anchor obligations may correctly prevent completion.

### 3. Initialize and make the first READY draft

Connect with the `owner` token. On an empty database, the first connection can
report an uninitialized workspace; this is expected. In **Command center** choose
**Initialize empty workspace**, then **Load example** and **Submit command**.
The browser supplies revision 0 and the confirmation value for initialization.

For every subsequent command: select the operation, click **Load example**, open
**Advanced payload** if necessary, enter any returned resource ID in the separate
resource field, then submit. **Last response** contains IDs and result fields.
The page supplies revision, session and duplicate-request protection automatically.
The normal task list and **Replay** show stored decisions.

1. Choose **Set / tighten baseline (owner)** and submit the example. It uses
   `subject_demo`, Base Sepolia chain ID `84532`, target
   `0x0000000000000000000000000000000000000001`, method `transfer`, and a future
   expiry. This is an explicitly synthetic, owner-attested baseline.
2. Choose **Register task (owner / investigator)** and submit the example.
   Save the returned `task.task_id` as the root task ID. The example request is
   USD 4,200 within a USD 5,000 limit. Expect `decision.verdict=READY` and
   `executable=false`.
3. To show dependent work, register another task with the same example scope
   and `depends_on: ["<root task ID>"]`. Keep all other example fields.
4. To show unrelated work, create a second baseline with only the target changed
   to `0x0000000000000000000000000000000000000002`, then register a task with
   that matching scope and `depends_on: []`. The subject remains `subject_demo`.

### 4. Persist two risks, restart, and recall

1. As owner, **Quarantine an external note** with the example malicious text.
   Expect `QUARANTINED`, `authority=false` and `model_received_raw_text=false`.
2. **Open risk case** for the root task's scope, first with `kind: "dispute"`,
   then again with `kind: "revocation"`. Save both returned `case.case_id` values.
   The example digest strings represent synthetic evidence, not verified facts.
3. Stop Uvicorn with Ctrl+C. Restart it with the **same command in the same
   terminal**, without deleting the database or recreating credentials. Open a
   fresh workbench tab and reconnect as owner.
4. **Evaluate task** with the original root task ID and `{}` as the payload.
   Expect DENY with the two causal cases. **Replay** should show an unchanged
   action fingerprint and commit, but a changed runtime ID. Dependent work is
   suspended; the unrelated target's task stays READY under its own baseline.

A new tab alone is not proof of a process restart. A list of saved decisions alone
is not an unedited video. For judge evidence, record the entire transition without
cuts and show timestamps or the commit, as in the published film.

### 5. Investigate, independently review, and reconsider

Switch roles using **Connect / switch role**, with the corresponding local token.
The reviewer must be distinct from both the case opener and investigator.

1. As **investigator**, choose **Investigate case**, supply the dispute case ID
   and submit `{}`. Save the returned `report.report_id`. The local default is
   visibly `DETERMINISTIC`; it is useful for this workflow without model charges.
2. Choose **Hand off report**, use the same case ID and set the example
   `report_id` to the actual returned ID, with `reviewer_id: "actor_reviewer"`.
   Save the returned `handoff.handoff_id`.
3. As **reviewer**, **Accept handoff** using that handoff ID and `{}`.
   Then **Resolve ONE case** using the dispute case ID and a payload containing
   the actual `handoff_id`, `resolution: "remediation_verified"`, and the example
   synthetic `evidence_digest`. The root task remains DENY while revocation is open.
4. Investigate the remaining revocation **after** the first resolution, then
   create a new handoff, accept it as reviewer, and resolve it. Context changes
   can invalidate an older report; never reuse a stale report/handoff to bypass
   that check.
5. Both risks are now resolved, but the task still needs human reconsideration.
   As reviewer, **Reconsider task** with the root task ID and `{}`. Expect a new
   READY decision and proof root, with `executable=false`. Earlier decisions stay
   immutable. No money moves during any of these steps.

### Troubleshooting and verification boundaries

- `401`: wrong/local-versus-hosted token, missing token, or revoked credential.
- `403`: wrong role or scope; use the correct role rather than widening permissions.
- Uninitialized workspace: owner bootstrap first; reconnect after successful setup.
- `REVISION_CONFLICT`: reload memory and inspect the latest state before resubmitting.
- Stale report/handoff: investigate current evidence and obtain a new handoff.
- Source coverage or stale-source errors: configured sources add real obligations;
  this minimal local walkthrough assumes no connector configuration.
- Missing Sibyl or quota errors must stop the workflow. Do not substitute fixtures
  or another memory store. Preserve records and inspect capacity before retrying.

The current instructions were checked against source and UI command definitions;
this README update did not rerun the scenario or test suite. Published runtime
verification is linked above. The old `session_a.py`, `session_b.py` and
`judge_benchmark.py` examples exercise historical v1 behavior and do not replace
this scoped Casework walkthrough or the current film.

## Base proof anchor

[`MemoryProofAnchor.sol`](contracts/src/MemoryProofAnchor.sol) stores only:

- a 32-byte decision proof root;
- the wallet attester;
- the Sibyl memory version;
- the anchor timestamp.

It never receives raw memory, the vendor note, a customer identifier, or a signing
key. Deployment commands exist in [`contracts/package.json`](contracts/package.json),
but no address or multiplier is claimed until an owner-authorized deployment and an
independently verified action receipt exist.

## Security boundaries

- External free text is never authoritative and is not persisted; only its
  domain-separated hash is kept.
- Anonymous `caller_supplied` facts cannot create trusted authority.
- `demo_fixture` is deliberately accepted for the public judging story and must not
  be confused with real identity verification.
- Missing/corrupt memory, stale drafts, wrong chain, wrong contract, reverted
  transaction, and wrong event/root all fail closed.
- A browser wallet request is manually approved. The backend verifies that the
  receipt sender matches the event attester, but does not claim that wallet is an
  authenticated customer identity. The Agent never handles a private key.

## Python test evidence

The repository includes focused tests for:

- fresh Module/Session A → B causal recall;
- identical action fingerprint across sessions;
- prompt-injection quarantine and non-persistence;
- unverified-source rejection and Sibyl deletion behavior;
- non-executable drafts and fixed Base wallet plans;
- empty/duplicate onchain proof roots;
- fresh Agent instances changing real tool paths from review to escalation;
- adversarial model requests for an unregistered payment tool being suppressed;
- Agent request idempotency and production Adapter rejection.

On 2026-09-05, the latest authorized Python run completed with `32 passed` using
`.venv/bin/python -m pytest`. This includes the 12-check benchmark behavior,
production readiness under an optional model outage, and the public write-rate
guard. The remote-model evidence path persists a
non-secret model receipt in the same Sibyl Agent run and binds it to the tool trace;
tampering with the generation ID fails the run integrity check. The historical
public Render A/B completed successfully with a pinned OpenRouter free model and a
real service restart. The generic free router had previously produced invalid JSON
and
HTTP failures; those runs stayed fail-closed, and no production-reliability claim is
made for the free model. The first run exposed
a missing Keccak backend; the
runtime dependency now explicitly includes `eth-hash[pycryptodome]`, and the clean
rerun passed. The Solidity contract was **not** compiled or tested, so no contract
runtime claim is made.

The same authorized run also completed a local two-process A/B exercise and an
isolated missing-Sibyl probe. Session B had a different runtime ID, kept the same
action fingerprint, recalled the exact dispute, and changed the deterministic Agent
path from `READY/await_finalize` to `DENY/block_and_escalate`. The isolated API had
no importable `sibyl_memory_client`; readiness, direct decision, and Agent run all
returned 503, while the decision and Agent responses also reported
`executable=false`. Exact values and limitations are recorded in
[`evidence/2026-09-01_RUNTIME_EVIDENCE.md`](evidence/2026-09-01_RUNTIME_EVIDENCE.md).
That earlier file is not remote-model evidence. A later production-configured run
successfully used an OpenRouter free model in both sessions through a temporary
Cloudflare HTTPS tunnel. It remains historical evidence only. The former stable
Render deployment and receipt-bound restart run are recorded in
[`evidence/2026-09-05_RENDER_OPENROUTER_AB.md`](evidence/2026-09-05_RENDER_OPENROUTER_AB.md).
The current VPS `/health/ready`, `/api/runtime`, and `/api/v2/public-release`
checks establish availability and build identity; the new synthetic A/B evidence
also establishes the real container restart and the `READY` → `DENY` safety change.
It does not prove migrated private-data persistence or a successful remote-model
receipt, and it does not replace the required unedited video. See also
[`evidence/2026-09-01_OPENROUTER_HTTPS_EVIDENCE.md`](evidence/2026-09-01_OPENROUTER_HTTPS_EVIDENCE.md).

The current evidence/dashboard hardening commit was revalidated on 2026-09-05 with
another full local API stop/start, the same persistent Sibyl database, the same
action fingerprint, exact causal dispute recall, `READY → DENY`, changed safety-tool
path, and a fresh isolated missing-SDK probe. This deterministic local result and its
limits are recorded in
[`evidence/2026-09-05_RUNTIME_REVALIDATION.md`](evidence/2026-09-05_RUNTIME_REVALIDATION.md).

## Prior Work

The original MemoryGuard foundation was created before the official build window
and is declared pre-build Prior Work in the public commit history. The Agent Module
and tool-audit increment was implemented after the window opened. The project also
reuses lessons—not contest evidence—from
[SafeHire / ProofOps BNB](https://github.com/seekitx/safehire-proofops-bnb), whose
latest copied local snapshot was commit
`bf1e1b575cc361d6c8d0949c066cb213b8d38413` on 2026-08-31.

Old BSC transactions, SafeHire jobs, reports, screenshots, users, or deployment
status do not prove Sibyl usage, Base integration, MemoryGuard PMF, or current
contest eligibility. Claim status is tracked in
[`submission/status.json`](submission/status.json).

## License

[MIT](LICENSE)
