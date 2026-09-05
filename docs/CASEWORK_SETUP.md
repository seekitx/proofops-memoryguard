# Casework v2 setup and validation

## 1. Start from the current source, not the old v2 installer

Casework v2 was integrated in commit `3ff9863dcab45ef4040506bab91492d5ee74575f`.
Do not reapply the old d82e729 overlay to a checkout that already contains it.
The 2.1 incremental bundle targets exactly 3ff9863 and must be previewed before apply.
See [2.1 hardening](CASEWORK_21_HARDENING.md) and
[capture/release steps](CASEWORK_21_CAPTURE.md). Do not discard local changes or
force a patch onto a different HEAD. The remaining setup steps below configure
the same existing application; pushing source alone does not enable v2.

## 2. Dependencies

Reuse the original project's Python3.11+ virtualenv and dependency declarations:

```bash
python -m pip install -e '.[dev]'
python -c 'from sibyl_memory_client import MemoryClient; print("official Sibyl import OK")'
```

No bundled substitute SDK is provided. A missing Sibyl dependency is a failure, not permission to use TestStore in runtime. The new sibling `proofops_casework` package is picked up by the existing src package discovery.

## 3. Private local operator registry

From the repository root:

```bash
python scripts/casework_create_credentials.py --tenant tenant_demo --subject subject_demo
```

It creates `.casework-private/registry.json` (hashes + principals) and `.casework-private/operator-tokens.json` (raw local demo tokens), both0600. It prints file paths only. Do not commit/upload either; the installer ignores this directory. Copy a role token into the workbench password field without screen-recording it. Default four roles are demo identities, not four real users.

## 4. Enable

```bash
export CASEWORK_ENABLED=1
export CASEWORK_AUTH_FILE="$PWD/.casework-private/registry.json"
export BUILD_COMMIT="$(git rev-parse HEAD)"
uvicorn apps.api.main:app --env-file .env --host 127.0.0.1 --port 8000
```

Use the original `.env` for Sibyl path and existing remote-model configuration. For final evidence, commit reviewed changes first, ensure clean source, and keep BUILD_COMMIT fixed across restart. A local uncommitted experiment is not release evidence merely because an old SHA is exported.

Open `/casework`. Owner first selects `bootstrap` with expected_revision0. Establish baseline, register tasks and risks. Investigate/handoff as investigator, accept/resolve/reconsider as reviewer. Refresh state to get current revision before a new command. A failed request retains its idempotency key; don't blindly generate a new key when the first request may have committed.

The static `/casework` page can load while v2 is disabled; its API will report not enabled. When enabled, old v1 mutation endpoints return410. Old evidence GET endpoints remain historical. Disabling CASEWORK_ENABLED returns the original demo behavior; it does not migrate v2 decisions into v1.

## 5. Run the real gates

From repository root with official dependencies:

```bash
python -m pytest
python scripts/casework_benchmark.py --backend sibyl --out /tmp/casework-sdk-benchmark.json
python scripts/casework_process_probe.py --commit "$(git rev-parse HEAD)" --out /tmp/casework-restart.json
```

The process probe uses ONLY its own newly created temporary database. It spawns separate workers, closes them, deletes that temporary database and tests a fresh read. It never accepts your production DB path. Review successful output and backend labels before calling the gate passed.

For isolated new-core unit experiments only:

```bash
python -m pytest tests/casework
python scripts/casework_benchmark.py --backend test --out /tmp/casework-test-benchmark.json
```

The test backend is clearly labelled TEST_DOUBLE_NOT_SIBYL. It is never configurable as the running API store.

## 6. Remote investigation

Configure the original `AGENT_MODEL_MODE=remote`, HTTPS endpoint, model and secret key. v2 reuses the original HttpModelAdapter implementation. Run a new case investigation and inspect planner_status/model_receipt/report_root. Model failure safely degrades optional planning; no success claim may be based on the old v1 receipt.

## 7. Base optional audit

First compile/test using existing contract tooling:

```bash
cd contracts
npm install  # use npm ci when a reviewed package-lock exists
npm test
```

Review and commit the generated lockfile; the base repository did not provide one. Package resolution success is not guaranteed by this bundle. No contract build was executed in the bundle-generation environment.

Review signer/network and gas budget before any deployment. The included new deployment script is Base Sepolia-only, independent of the existing v1 contract. With an operator-configured Hardhat signer:

```bash
CASEWORK_DEPLOY_APPROVAL=base-sepolia-audit-only \
  npx hardhat run deploy-casework.cjs --network baseSepolia
```

This command **does broadcast a deployment** when authorized and configured; it is not a dry-run. It was not run while producing this bundle. Keep signing secrets outside application/CI; never send keys in chat.

Configure runtime `CASEWORK_BASE_ANCHOR_ADDRESS` to the actual new contract and `CASEWORK_ANCHOR_ATTESTER` to the explicit demo wallet. Existing BASE_CHAIN_ID/BASE_RPC_URL settings must match Base Sepolia. Restart. Reviewer prepares an audit plan; browser wallet explicitly approves the zero-value contract call; submit resulting txhash to verify. Gas is still charged. No private key enters API.

Two confirmations are required by the adapter. PENDING is not VERIFIED. A verified application receipt is not the organizer's multiplier decision.

When enabled, `/` redirects to `/casework`, so the obsolete v1 form does not invite calls to disabled writes. Existing `/evidence` is historical v1 and receives an explicit evidence-scope header; use `/casework/evidence` for an explicitly exported 2.1 capture; until a valid capture is configured it reports NOT_RECORDED. For judging, provide a least-privilege viewer credential through an approved private channel or publish a separately reviewed redacted evidence artifact. Never expose owner/reviewer credentials as a public demo shortcut.
