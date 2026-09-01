# OpenRouter and temporary HTTPS evidence — 2026-09-01

## Result

A production-configured MemoryGuard process made two successful structured calls to
an OpenRouter free model across a full API restart. Session A returned `READY` and
prepared only non-executable review artifacts. Session B recalled the exact persisted
Sibyl dispute, returned `DENY`, suppressed the review tool, and created a
non-executable escalation artifact. In this captured build, the generation metadata
was read immediately after each run from runtime model health; it was not yet stored
inside the corresponding Sibyl Agent run.

The same process was exposed through a Cloudflare Quick Tunnel and checked through
its public HTTPS URL. This is useful public demonstration evidence, but it is not a
durable hosted deployment: the random URL can expire, the Mac must remain online,
and Cloudflare does not provide an uptime guarantee for Quick Tunnels. The matching
machine-readable record is
[`2026-09-01_OPENROUTER_HTTPS_EVIDENCE.json`](2026-09-01_OPENROUTER_HTTPS_EVIDENCE.json).

## Real remote-model A/B

- configured model: `dots-studio/dots-3-note-preview:free`
- resolved model: `dots-studio/dots-3-note-preview-20260813:free`
- provider reported by OpenRouter: `AtlasCloud`
- price reported for both successful generations: `$0`
- structured-output gate: strict JSON Schema plus
  `provider.require_parameters=true`
- build commit: `21f3d4b27bb59bf39337843ea4e7233e2bf98c38`
- evidence mode: synthetic `demo_fixture`

| Check | Session A | Session B |
|---|---|---|
| runtime instance | `runtime_720cbf614ffe40e2a3fa` | `runtime_f4eea05aaacd4ab4b8b8` |
| generation ID | `gen-1788248292-zx1ojYtjh2QwEZinvUYa` | `gen-1788248378-ceGyZOdVcYLRzC136IFe` |
| completion SHA-256 | `b1742c08…6eb6d53` | `2f6b8c21…b52333b9f` |
| action fingerprint | `dd23f9ac…a2db5a2` | `dd23f9ac…a2db5a2` |
| verdict | `READY` | `DENY` |
| Agent state | `await_finalize` | `block_and_escalate` |

Session A persisted dispute observation `obs_5ebe6dcbc07640c89a08` while
quarantining its instruction-like `raw_text`. Session B used a different runtime
instance, recalled that exact observation with `cross_session: true`, and passed the
comparison and then-current runtime-health remote-model gates. The Session A
manifest digest was
`b05fc34dbbfd04167d026bd80bb03e5039535f3dbe40c9aee22dbc79b1adad4b`.

OpenRouter's authenticated generation metadata independently returned both
generation IDs, the resolved model, provider, stop finish reason, token counts, and
zero cost. Their timestamps align with the stored Agent runs, but the old Agent run
schema cannot cryptographically bind the generation IDs to those runs. The prompt
and completion bodies are deliberately not copied into this repository; only hashes
and non-secret provenance are retained.

## Post-capture receipt hardening

Commit `ea561f8256319da168a5a33d6e3e529b128f04e7` adds `AgentRun` schema `1.1`.
Every successful remote plan now stores a non-secret receipt—configured and resolved
model, generation ID, completion SHA-256, structured-output checks, and completion
time—in the same Sibyl Agent run. A `model.receipt` tool event binds the receipt to
the run trace hash, and a tampered generation ID fails integrity validation. Session
A/B evidence scripts now accept remote proof only from this stored receipt, not from
global model health. The authorized suite passed `24 tests` after this change.

A receipt-bound live A/B rerun was attempted, but the free providers returned an
intermittent empty response and HTTP `429 Too Many Requests`. No receipt-bound live
success is claimed yet. The next successful run after the free quota/provider
recovers should replace the legacy runtime-health evidence above.

## Public HTTPS observation

The temporary URL observed during this run was:

```text
https://themselves-snapshot-equilibrium-cabin.trycloudflare.com
```

The following were observed through that public URL:

- `GET /health/ready` returned `200` with `memory.backend=sibyl_memory`;
- the model backend reported `remote_structured_model`, live call and structured
  output checks were true after each successful Agent run;
- `/` and `/proof` returned `200`;
- the API process was fully stopped and restarted while the tunnel stayed active;
- Session B read the same persistent local Sibyl database after the restart.

Both successful CLI sessions used the Quick Tunnel URL as their explicit
`--base-url`. The non-secret request trail is:

- Session A Agent run: `run_0055c8c6e76905999f9a`;
- Session B Agent run: `run_fcf432000f9a954f0136`;
- Session A command shape:
  `session_a.py --base-url https://themselves-snapshot-equilibrium-cabin.trycloudflare.com --require-remote-model`;
- Session B command shape:
  `session_b.py --base-url https://themselves-snapshot-equilibrium-cabin.trycloudflare.com --require-remote-model`.

The synthetic subject and manifest digest in the machine-readable file bind these
runs to the same A/B story. No API key or raw prompt is present in the commands.

This proves that the exact build was publicly reachable over HTTPS during the
observation and that its local persistent database survived the API restart. It does
not prove cloud-host durability, uptime, redeploy persistence, or that the temporary
URL will still work for judges.

## Reliability and privacy boundary

The free model is labelled `free_experimental`; MemoryGuard does not claim production
reliability for it. A later repeat attempt encountered a sanitized
`RemoteModelResponseError`. The deterministic MemoryGuard decision still denied the
high-risk intent, suppressed review, created the escalation artifact, and remained
non-executable, but the strict remote-model evidence gate correctly failed that
repeat. This is the expected fail-closed behavior and also evidence that the free
route is too intermittent for a final judge demo without a fallback rehearsal.

The OpenRouter free endpoint was not compatible with the tested `data_collection=deny`
policy. Therefore only synthetic `demo_fixture` facts were sent. Do not send private
support tickets, customer disputes, wallet data, secrets, or identity data through
this free route. No API key is stored in the repository, evidence files, or logs.

## Remaining contest evidence

- complete one receipt-bound successful A/B run, then record it continuously in one
  unedited 2–5 minute video;
- move the demo to a stable HTTPS hostname with durable storage, or keep the Mac
  online and use a named Cloudflare Tunnel backed by an owner-controlled domain;
- publish two build-in-public posts;
- do not claim Base, PMF, or production reliability without their separate evidence.
