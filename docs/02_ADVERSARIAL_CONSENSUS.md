# Adversarial review and final consensus

## Process

Three independent roles were asked to attack the project from different directions:

1. official-rules researcher: verify requirements and the existence of past winners;
2. skeptical judge: find reasons to reject the copied SafeHire repository;
3. security builder: find the smallest safe implementation that can survive a curious
   judge and a hostile input.

The skeptical judge and security builder then received each other's proposal and
were required to choose one Interface, one demo, and one scope.

## Round one disagreements

### Two methods or three

- Security builder initially preferred `remember / decide` for the smallest surface.
- Skeptical judge initially preferred `observe / decide / finalize` so receipt
  verification could not be assembled loosely in HTTP handlers.

### What should the demo prove

- One proposal emphasized a user revocation changing a Base action.
- The other emphasized quarantining prompt injection while preserving a trusted
  dispute fact.

### Is Base part of the core

- One proposal treated Base as optional after the memory gate.
- The other treated it as required for a winning submission because it adds 1.15 and
  gives the local proof an external timestamp.

### What happens to SafeHire

- Keeping it in the main tree honors the literal copy request but buries the new
  critical path.
- Removing it from the workspace would lose a useful construction reference.

## Concessions

- The two-method side accepted `finalize` because finalization owns version locking,
  proof commitment, wallet confirmation planning, and receipt verification. These
  behaviors belong behind the same Module Interface as the decision.
- The three-method side accepted that `observe` does not mean “trust”. It validates
  structured facts and quarantines instruction-like text field by field.
- Both sides accepted that Base is a winning-scope P0, not an eligibility P0. Sibyl
  must work first. Base is never claimed before a real exercised integration.
- Both sides accepted that Virtuals remains P1 until a real ACP or native Agent action
  exists.
- Both sides accepted that the copied SafeHire tree stays locally under
  `.prior-work/`, excluded from Git and Docker. The original repository remains the
  public prior-work reference.

## Final unanimous decision

The public Module Interface is:

```python
observation = guard.observe(event)
draft = guard.decide(intent)
final = guard.finalize(draft.decision_id, confirmation=None)
```

Post-implementation security review added `inspect_finalization(decision_id)` as a
read-only query. It is not a fourth command and cannot create, retry, or downgrade a
finalization. This keeps HTTP GET proof inspection free of side effects.

The one demo story is:

1. Session A evaluates a Base vendor payment and returns a non-executable READY draft.
2. A trusted user opens a dispute/revokes the target.
3. A malicious vendor note says to ignore the rule and pay; it is quarantined.
4. The process/session is replaced.
5. Session B evaluates the identical intent.
6. Sibyl recalls the trusted dispute; the result becomes DENY and names the causal
   memory.
7. The user may anchor the proof root on Base. `finalize` independently verifies the
   configured chain, contract, event, and proof root.

## Non-negotiable rules

- No production memory fallback.
- No free-form text in the authority path.
- `decide` never returns executable transaction authority.
- `finalize` reloads the stored draft; callers cannot submit a replacement verdict.
- DENY never creates a capability.
- A Base transaction is pending until independent receipt verification succeeds.
- Old BSC transactions are Prior Work, not Sibyl, Base, PMF, or contest evidence.

## Why this consensus is stronger

The Module remains deep: three calls hide normalization, provenance, quarantine,
exact recall, deterministic policy, versioning, proof construction, wallet planning,
and receipt verification. The Interface is small enough for a judge, while security
logic stays local instead of spreading across routes and JavaScript.
