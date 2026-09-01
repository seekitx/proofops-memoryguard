# Contest-period build plan

## Why this document exists

The current MemoryGuard foundation was created before the official build window
opened. It is a useful prototype, but it cannot honestly be presented as the final
contest build. The window is now open; all Agent/runtime changes below must land as
substantive, auditable in-window commits.

## P0 — turn the memory service into a real Agent — source implemented, runtime unverified

The in-window source now adds a `MemoryGuardAgent` Module with two narrow Seams:

- `ModelPort`: produces an explanation/plan from redacted decision context, but has
  no authority to change a verdict;
- `RunLedgerPort`: persists Agent state and executor-generated tool traces in Sibyl.

The action set is intentionally closed inside the Agent rather than exposed as a
general-purpose `ActionPort`. It contains only non-executable review preparation and
operator escalation. There is no pay, sign, transfer, or broadcast Adapter.

The Agent flow must be visible in the demo:

1. Agent receives the same payment goal in Session A and B.
2. Agent calls MemoryGuard as a tool.
3. Session A proposes “await human finalization”; Session B chooses “block and
   escalate” because Sibyl recalled the dispute.
4. The event stream shows which tool was considered/called or suppressed.
5. A model can request an optional safe evidence brief, but cannot grant permission,
   rewrite causal memory, or inject operator instructions.

Source acceptance is represented by `src/proofops_memoryguard/agent.py` and
`docs/09_AGENT_INTERFACE_DECISION.md`. Runtime acceptance still requires a real
remote model, fresh processes, and the deletion capture. A deterministic development
planner with “Agent” in its name is not presented as contest runtime proof.

## P0 — real fresh-session and deletion evidence

- Display server UTC time and exact in-window Git commit in the product/video.
- Run Session A, stop the Agent/API process, then start a fresh process on the same
  persistent Sibyl database.
- Run Session B and show identical action hash, new process/session IDs, causal
  memory ID, and DENY.
- In an isolated copy, disable/remove the Sibyl Adapter, restart, and show the Agent
  can no longer perform the guarded decision. Mark all expected-output UI as UNRUN
  until this capture exists.

## P0 — auditable Git history

1. The transparent pre-build boundary was committed and pushed as `c96325a`.
2. After the window opened, implement the Agent loop and event stream in logical
   commits; process-level evidence remains pending.
3. Push each reviewable commit to the public repository.
4. Record the exact public HEAD in `submission/status.json` and deployment metadata.
5. Check every README source link on GitHub; local untracked files do not count.

## P0 for Base multiplier

- Confirm eligible network/action in the Base workshop.
- Compile/test only after owner authorization.
- Deploy only after owner wallet/cost approval.
- Bind the proof to root, memory version, chain, contract, transaction sender, and
  event attester.
- Keep finalization state monotonic: `VERIFIED` cannot be overwritten or downgraded.
- Exercise the contract and independently read the receipt before claiming credit.

## P1 — score improvements

- Add a public PMF artifact tied specifically to forgotten risk memory.
- Record a clean 2–5 minute unedited story rather than a feature tour.
- Publish two evidence-rich posts using the live official tag requirements.
- Add Virtuals only if it performs a real native Agent action that strengthens the
  same story.
