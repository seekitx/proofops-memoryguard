# MemoryGuard runtime revalidation

Captured against commit `7f002fb56c7ce21187047f3e7b00255ef36327ce` on
2026-09-04 16:52 UTC (2026-09-05 Beijing time).

## Observed process-restart comparison

- Session A API runtime: `runtime_9ca7e40cad2a4e94a1dd`
- Session B API runtime: `runtime_77b6c333af844871b79d`
- Same commit and official `sibyl-memory-client 0.7.0`, schema 4
- Same action fingerprint in both runs
- Session A: `READY / await_finalize`
- Session B: `DENY / block_and_escalate`
- Exact dispute observation recalled across sessions
- Review tool suppressed; non-executable escalation created
- Session A manifest digest and stored-run comparison passed

## Observed isolated missing-SDK behavior

The official Sibyl SDK was not importable in a separate virtual environment.
Readiness, direct decision, and Agent run returned `503`; both action responses
reported `executable=false` and no alternate memory backend was used.

## Evidence boundary

This is local engineering evidence. JSON cannot independently prove that the operator
really stopped and restarted the process; the contest video must show that sequence
continuously. The isolated environment proves missing-SDK fail-closed behavior, not
deletion of an existing database. The planner was deterministic, so this file is not
receipt-bound remote-model evidence, stable HTTPS hosting, Base/Virtuals, or PMF.
