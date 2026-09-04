# Demo, video, and submission runbook

## One-sentence pitch

ProofOps MemoryGuard is a persistent decision firewall that remembers the exact risk
fact an Agent must not forget, even when a hostile instruction and a fresh session
try to erase it.

## 2–5 minute unedited video

### Render recording preflight

Before recording, open these three tabs and keep them visible:

- <https://proofops-memoryguard.onrender.com>
- <https://proofops-memoryguard.onrender.com/evidence>
- the Render service dashboard, so the restart action and recovery are visible.

Use one new subject for the whole take. On this Mac, the project virtual environment
must supply the HTTPS certificate bundle; do not disable certificate verification.

```bash
DEMO_SUBJECT="judge-$(uuidgen)"
SSL_CERT_FILE=/Users/hun/项目/proofops-memoryguard/.venv/lib/python3.11/site-packages/certifi/cacert.pem \
  .venv/bin/python scripts/session_a.py \
  --base-url https://proofops-memoryguard.onrender.com \
  --subject "$DEMO_SUBJECT" \
  --evidence-out /tmp/memoryguard-recording-a.json \
  --require-remote-model
```

Keep the printed `session_a_evidence_sha256`. In the same continuous recording,
choose **Manual Deploy → Restart service** in Render and wait until
`/health/ready` returns. Then run:

```bash
SSL_CERT_FILE=/Users/hun/项目/proofops-memoryguard/.venv/lib/python3.11/site-packages/certifi/cacert.pem \
  .venv/bin/python scripts/session_b.py \
  --base-url https://proofops-memoryguard.onrender.com \
  --subject "$DEMO_SUBJECT" \
  --session-a-evidence /tmp/memoryguard-recording-a.json \
  --session-a-sha256 PASTE_SESSION_A_SHA256 \
  --require-remote-model
```

Do a private rehearsal first because the OpenRouter model is a free experimental
service. If it fails, MemoryGuard remains safe but the strict video comparison will
correctly fail instead of hiding the degraded model call.

### 0:00–0:25 — problem and boundary

- Show the public repository and hosted page.
- Say: “A risk control that resets every chat is not a control.”
- Point out `DEMO_FIXTURE`, `no payment sent`, and `Base not claimed yet/verified`
  according to the live deployment state.

### 0:25–1:20 — Session A

- Display the generated subject and Session A ID.
- Establish the trusted baseline.
- Run the Agent on the `$4,200` intent and show `READY`, `AWAIT_FINALIZE`,
  mandatory `human_review.prepare`, the model-selected optional causal brief,
  `executable: false`, and its causal baseline ID.
- Submit the open dispute with the malicious note.
- Show `partially_accepted`, accepted structured fields, quarantined `raw_text`, and
  injection reason codes.

### 1:20–2:10 — fresh Agent/API process and Session B

- Stop the Agent/API process after Session A, then restart it on the same persistent
  Sibyl database. Do not reuse a Python object or in-process cache.
- Pass Session A's evidence manifest to `session_b.py`; the script must fail unless
  the runtime IDs differ and action fingerprints match. The manifest is comparison
  evidence only and is never an Agent memory input.
- Open Session B and show the new process/session IDs, server UTC time, exact public
  in-window commit, and unchanged action fingerprint.
- Run the same Agent goal again and pause on `DENY`, `BLOCK_AND_ESCALATE`, the
  suppressed review tool, the called escalation tool, `cross_session: true`, and the
  exact causal dispute observation ID.

### 2:10–2:45 — deletion test and source

- Show `MemoryGuard.decide` calling `load_subject` and the production Adapter guard.
- Show the separately captured, real deletion-test behavior—only after it has been
  run—not a typed slide. Development may show 503; production may fail startup.
- Open the README's exact source pointers.

### 2:45–3:30 — proof and truth boundary

- If a real Base integration has been exercised, request the fixed wallet plan,
  confirm it in the wallet, then show the backend-verified receipt and explorer.
- If it has not, show local finalization and clearly say Base is prepared but not
  claimed. Never use old BSC transactions as a substitute.
- End with public proof endpoint, prior-work disclosure, and the concrete PMF artifact
  if one exists.

## Submission copy draft

### Title

ProofOps MemoryGuard — Persistent Risk Memory for Autonomous Agents

### Short description

MemoryGuard uses load-bearing Sibyl Memory to preserve trusted disputes,
revocations, and action limits across sessions. It quarantines prompt-injection text,
changes the same non-executable payment intent from a READY review to causal DENY in
a fresh session, and can anchor only the redacted decision proof root after user
wallet confirmation.

### What is innovative

Most Agent memory demos optimize convenience. MemoryGuard treats forgetting as an
authorization vulnerability. The model may select an optional safe evidence
artifact, but exact typed memory and deterministic policy own authority. Raw model
prose is not persisted as operator guidance. Every behavioral change names the
memory that caused it, and removing Sibyl removes the behavior.

### Technical highlights

- official Sibyl WARM entities, COLD events, and REFERENCE policy document;
- no production memory fallback;
- source-labeled observation quarantine and instruction hashing;
- domain-separated observation, intent, memory, policy, and decision roots;
- deep `MemoryGuardAgent.run / inspect / resume` Interface over the
  `observe / decide / finalize` safety kernel;
- real-model production Adapter, closed safe-tool executor, and Sibyl Agent run ledger;
- manually approved Base wallet plan and backend sender/attester/receipt verification;
- explicit synthetic-data, prior-work, and partner-claim boundaries.

## Public posts

Prepare two distinct public posts using the exact current accounts/tags from the
official rules at submission time:

1. **Build post:** short Session A/B clip, repository link, and the exact statement
   that Sibyl is load-bearing.
2. **Problem/learning post:** explain why forgotten revocations are security bugs,
   what the injection attempt did, and what remains unproven.

Do not call a draft, screenshot, test fixture, configured contract, or pending
transaction a live integration.

## Final evidence bundle

- public repository and visible contest-period commits;
- hosted HTTPS demo with persistent Sibyl storage;
- raw unedited 2–5 minute video URL;
- README exact write/read/deletion pointers;
- Base explorer URL and backend verification output, if claimed;
- public PMF artifact, if the bonus is claimed;
- two post URLs;
- private build-page submission confirmation screenshot;
- registration/team confirmation screenshot.

The authoritative remaining-state list is
[`07_MANUAL_COMPLETION_GATES.md`](07_MANUAL_COMPLETION_GATES.md), not optimistic
marketing copy.
