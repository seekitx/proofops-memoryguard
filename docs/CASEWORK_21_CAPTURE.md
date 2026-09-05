# Casework 2.1 — capture and publish without mixing evidence versions

## 0. Enable the module explicitly

A pushed commit is not an enabled deployment. The existing `casework.env.example`
defaults to `CASEWORK_ENABLED=0`. Create the operator registry on the target host
using `scripts/casework_create_credentials.py` only if it does not already exist;
keep it on private persistent storage. Then set `CASEWORK_ENABLED=1` and the absolute
`CASEWORK_AUTH_FILE` path through the existing deployment configuration. Do not
publish owner/reviewer credentials or insert them into public evidence.

After the operator's restart, `/api/runtime` must identify `casework-v2.1` and the
actual deployment SHA. A static `/casework` page loading is not sufficient proof
that the API was enabled. V2 storage readiness and owner bootstrap are separate.

## 1. Authorized verification in the complete checkout

These commands are provided for execution in the user's environment. They were not
run as part of this source-only review. Keep secrets and output artifacts outside Git.

```bash
python -m pip install -e '.[dev]'
python -m pytest --junitxml=/tmp/memoryguard-tests.xml
python scripts/casework_benchmark.py --backend sibyl --out /tmp/casework-benchmark.json
python scripts/casework_champion_probe.py --out /tmp/casework-capture.json
```

The new capture defaults to the real official SDK, never the in-memory test store.
It requires a clean Git checkout unless explicitly requested as an ineligible rehearsal.
If the SDK is missing it exits with UNRUN; this is not a passing deletion test.

Three workers use one newly allocated temporary Sibyl database:

- A: baselines, parent/child/unrelated tasks, actual review artifact, quarantined note,
  two remembered risks.
- B: same parent action denied, descendant denied, old review rejected, real persisted
  escalation artifact, one risk resolved while the other still blocks, then both
  resolved but explicit reconsideration still required.
- C: independent reviewer principal re-evaluates the parent before its child,
  producing fresh READY proofs and another non-executable review artifact.
- After all workers exit: only the allocated temporary DB is deleted; another worker
  observes missing workspace and stops. No real deployment or user DB is touched.

The script outputs a strict public summary, not the worker's private payloads. It proves
only the synthetic SDK/service path it actually exercises. It is NOT authenticated
HTTP E2E, a hosted service restart, distinct human reviewers, PMF or continuous video.

## 2. Optional real model path

After configuring existing `AGENT_MODEL_*` secrets privately:

```bash
python scripts/casework_champion_probe.py --live-model --out /tmp/casework-live-capture.json
```

`--live-model` explicitly permits external model calls and possible cost. Two reports
must bind valid receipts or the command does not pass. Provider degradation remains
visible; no deterministic planner is relabelled as remote AI. A context-bound receipt
is still not a cryptographic statement signed by the model provider.

## 3. Evidence publication

Configure an owner-reviewed file on persistent storage, for example:

```text
CASEWORK_PUBLIC_EVIDENCE_FILE=/data/public-evidence/casework-capture.json
```

Copy the **public summary** produced by the capture into that file using the
operator's deployment process. Do not copy the credential registry, private tokens,
raw case material, an entire workspace export or an arbitrary previous assistant log.
The schema rejects extra fields, rather than redacting unknown fields by guesswork.

Visit `/casework/evidence`. Status meanings:

| Status | Meaning |
|---|---|
| NOT_RECORDED | No file configured/available; nothing is claimed |
| INVALID_ARTIFACT | Malformed, oversized or unexpected fields; no content is echoed |
| TEST_ONLY | Explicit test-double record, never official SDK evidence |
| HISTORICAL_OR_UNCOMMITTED | Commit/source/cleanliness does not match the active build |
| CHECKS_INCOMPLETE | Artifact exists but its required checks did not all pass |
| CURRENT_SELF_RECORDED | Same commit + same runtime-source fingerprint, official SDK, clean build and recorded checks; still not independent/judge verification |

The fingerprint covers shipped Python/web/config code plus pyproject, not media,
credentials, test outputs or the container's entire dependency environment.

Do not solve the commit self-reference problem by lying about BUILD_COMMIT. Commit
code, capture from that clean SHA, and publish the data out-of-band on persistent
storage. Committing the capture changes HEAD; that older capture must then stay
historical unless a new valid run is made. A source match alone is not an exact SHA match.

## 4. Browser read probe (limited scope)

```bash
python -m pip install playwright
python -m playwright install chromium
python scripts/casework_browser_read_probe.py \
  --base-url https://YOUR_HOST \
  --out-dir /tmp/casework-browser-check
```

The output directory must not already exist. This checks public pages at desktop and
mobile sizes, including script errors and horizontal overflow. It uses no credentials
and performs no business writes. Authenticated role-switch, stale-response and full
business E2E acceptance remain separate manual/browser tests.

## 5. Required real deployment checks

Keep the same SHA on both sides of an actual API/service stop/start. Reopen the
operator workbench, prove that cases/reports/tasks survived, and show changed behavior
plus actual artifacts. Record the cold-start segment continuously. Never erase the
production DB to demonstrate deletion; use the isolated probe.

Base remains NOT CLAIMED until contract tests, actual network operation and receipt
verification are real. Virtuals remains NOT CLAIMED; this increment adds no ACP job.
A public feedback issue or self-run synthetic scenario is not automatically PMF.
