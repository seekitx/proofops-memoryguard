# New VPS public evidence boundaries

- Target: `https://memoryguard.eyesonchain.xyz/`
- Build: `a4b216e73f2eed86ef2e07e2fdece4b48728190c`
- Synthetic scope: tenant/workspace `memoryguard-vps-20260906`, subject `vps-judge-20260906`.
- The A→B proof restarted only the MemoryGuard service. The build stayed the same, the runtime changed, and health returned to ready.
- Session A is **live-state recovery after the first local recorder timed out after its mutation sequence**. It is not a clean continuous recording. No mutation was replayed; the live overview and replay endpoints were read to reconstruct redacted A evidence.
- Session A recorded `READY`, `executable=false`; after the service restart, Session B evaluated the same action fingerprint as `DENY`, with two open risk blockers. Related work stopped and unrelated work stayed `READY`; observed decisions remained non-executable.
- The single remote investigation returned HTTP 200 but `planner_status=DEGRADED`, with `model_receipt=null` and no generation ID. The remote receipt gate is **NOT PASSED** and the request was not retried.
- Temporary access was removed. Both temporary credentials returned `401 INVALID_CREDENTIAL` after cleanup. The synthetic workspace and its evidence were retained.

This public evidence does not claim a successful remote generation receipt, clean continuous video, customer/private casework validation, wallet or chain action, Render shutdown, full test/build run, or any infrastructure remediation.
