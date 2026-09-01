# Contest-period build plan

## Why this document exists

The current MemoryGuard foundation was created before the official build window
opened. It is a useful prototype, but it cannot honestly be presented as the final
contest build. The window is now open; all Agent/runtime changes below must land as
substantive, auditable in-window commits.

## P0 — turn the memory service into a real Agent

Add a `MemoryGuardAgent` Module with two narrow Seams:

- `ModelPort`: produces an explanation/plan from redacted decision context, but has
  no authority to change a verdict;
- `ActionPort`: receives only a finalized, capability-bound action. `DENY`,
  `NEEDS_HUMAN`, model failure, memory failure, stale policy, and stale memory never
  call it.

The Agent flow must be visible in the demo:

1. Agent receives the same payment goal in Session A and B.
2. Agent calls MemoryGuard as a tool.
3. Session A proposes “await human finalization”; Session B chooses “block and
   escalate” because Sibyl recalled the dispute.
4. The event stream shows which tool was considered/called or suppressed.
5. A model can explain but cannot grant permission or rewrite causal memory.

Acceptance: removing Sibyl prevents the Agent from choosing the claimed guarded
action. A deterministic service with “Agent” in its name is not enough.

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

1. Owner reviews and records the pre-build boundary without falsifying dates.
2. After the window opens, implement the Agent loop, event stream, and process-level
   evidence in several logical commits.
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
