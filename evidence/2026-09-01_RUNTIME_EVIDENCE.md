# Runtime evidence — 2026-09-01

## Result

The authorized Python checks passed, the two-process A/B demonstration observed a
different runtime instance reading the same persisted Sibyl memory, and an isolated
runtime without the official Sibyl SDK failed closed. The matching machine-readable
record is [`2026-09-01_RUNTIME_EVIDENCE.json`](2026-09-01_RUNTIME_EVIDENCE.json).

This is useful local runtime evidence, but it is deliberately **not** labelled as a
completed contest gate. The A/B run used `deterministic_test_planner`, no continuous
video was recorded, and the isolated probe removed the SDK rather than deleting an
existing Sibyl database.

## Python environment and tests

- Python: `3.11.15`
- official distribution: `sibyl-memory-client==0.7.0`
- command: `.venv/bin/python -m pytest`
- result: `20 passed in 0.08s`
- runtime dependency fix: `eth-hash[pycryptodome]` was added so Keccak hashing has
  an installed backend

The Solidity contract was not compiled or tested. No wallet or chain operation was
performed.

## Two-process A/B observation

Both API processes used the same persistent Sibyl database, tenant ID, fixed
synthetic subject, port, and full build commit
`0a3b5595618566d97f973a6fec713ec72089edf5`.

| Check | Session A | Session B |
|---|---|---|
| runtime instance | `runtime_cb7f21148d894806a90b` | `runtime_549da928634d444c9aa0` |
| action fingerprint | `2f5af982…803cf1c7` | `2f5af982…803cf1c7` |
| verdict | `READY` | `DENY` |
| Agent state | `await_finalize` | `block_and_escalate` |
| model | `deterministic_test_planner` | `deterministic_test_planner` |

Session A accepted a typed open dispute while hashing and quarantining the attached
instruction-like text. Session B recalled the exact causal observation
`obs_969afec3064f40828288`, returned `cross_session: true`, suppressed the review
tool, created a non-executable escalation case, and passed every comparison preflight
check. The strengthened comparison gate also required the suppressed review trace,
successful escalation trace, and non-executable decision/artifact. The Session A
manifest digest was
`13da856b3f373050df59a4c69684eef262be1456ff3a64e7e5b946ae2d6e4335`.

The runtime also reported SDK version `0.7.0`, schema version `4`, compatible schema,
and matching installed-distribution `RECORD` hashes for the required runtime files.
Its `production_eligible=true` field refers only to the memory Adapter's SDK identity
and schema checks; the deterministic development process is not production mode.

### What this does and does not prove

It proves the observed API behavior and the internal evidence bindings. The JSON
alone cannot prove that the operator really stopped the whole process or that the
reported `BUILD_COMMIT` was the exact checked-out source. The final contest capture
must show Session A, full process shutdown, process restart, and Session B in one
unedited recording.

It also does not prove remote-model behavior. Production still requires a real HTTPS
model endpoint, model name, and API key; those were unavailable for this run.

## Isolated missing-Sibyl probe

A separate Python 3.11 virtual environment installed the app without its
`sibyl-memory-client` dependency. Before launch,
`importlib.util.find_spec("sibyl_memory_client")` returned `None`.

The isolated API produced:

- `GET /health/ready` → `503`, `memory.backend=sibyl_unavailable`,
  `production_eligible=false`;
- `POST /api/decisions` → `503 MEMORY_BACKEND_UNAVAILABLE`,
  `executable=false`;
- `POST /api/agent/runs` → `503 MEMORY_BACKEND_UNAVAILABLE`;
- `executable=false`;
- no fixture, JSON, alternate database, browser storage, or in-process fallback.

This proves fail-closed behavior when the official SDK/Adapter is unavailable. It is
not described as a completed deletion test because an existing Sibyl database was
not deleted and the environment setup was not continuously recorded.
