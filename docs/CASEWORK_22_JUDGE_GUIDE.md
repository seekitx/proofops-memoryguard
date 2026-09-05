# Casework 2.2 — reviewer guide

**The product:** a persistent safety workflow that remembers why work stopped, gathers attributable evidence, and requires independent reconsideration before work resumes.

## One concrete story

A primary task and a dependent task are initially ready for human review. A scoped incident blocks both, but leaves an unrelated task unaffected. An investigator collects an allowlisted issue snapshot and, when configured, a matching Base transaction receipt. The exact source bundle is persisted with the investigation report. A designated reviewer accepts the handoff and resolves each case separately. After all blockers are cleared, explicit reconsideration restores work in dependency order.

No output is an executable payment capability. No model can sign, pay, or clear a risk case.

## Why persistent memory changes the work

- New processes recover open risks, graph dependencies, report versions and accepted handoffs.
- Source requests are recorded before network access; an interrupted read remains visible rather than being silently repeated.
- A still-current source snapshot can be reused. Once it expires or a forced refresh fails, an old report cannot authorize resolution.
- Historical source bundles remain attached to their original reports rather than being replaced by today's state.
- Resolution evidence is linked into subsequent task proof bases.
- Missing Sibyl stops the core workflow. There is no production alternate business store.

## Source pointers

| Question | Code |
|---|---|
| Where is business memory read/written? | `src/proofops_casework/store.py` |
| Where do relevant facts affect permission? | `core.py::policy_result`, `decision_validity`, `task_basis` |
| Where does a risk affect dependent tasks? | `core.py::affected_tasks`, `service.py::_invalidate` |
| Where are sources acquired and reused? | `source_service.py::collect`, `source_state.py::current_receipts` |
| Where is evidence required for resolution? | `source_service.py::resolution`, `service.py::resolve` |
| What does the model receive? | `service.py::investigate`, `receipts.py::bound_receipt` |
| How does a provider review bind to this case? | `partner_review.py`, `connectors/virtuals_cli.py` |
| What can an external MCP agent do? | `mcp_readonly.py`: seven GET-only tools |

## Evidence boundaries

This version ships implementation and verification scripts. A test file, adapter or example address is not an executed integration.

- The source-read benchmark deliberately uses synthetic HTTP responses. Its default memory backend is the official Sibyl SDK; these are separate claims.
- An ACP history observation binds a real protocol response to a request but is not an independent onchain audit or an awarded multiplier.
- An issue being closed, a transaction succeeding, or a provider returning a review is not enough to resolve a case without the authorized workflow.
- Hash consistency is not independently authenticated authorship, truth, or proof of customers.
- A single person operating multiple role credentials does not demonstrate independent humans or PMF.

## Demo acceptance

Show one continuous cold-start memory segment with a timestamp/build SHA; retain the real process interruption. Show scoped blocking and unaffected work, source reuse, invalidation after expiry/change, partial resolution still blocked, and a new decision after explicit reconsideration. Demonstrate partner actions only after actual execution. Public evidence exports must match the final code version and remain honest about simulations.
