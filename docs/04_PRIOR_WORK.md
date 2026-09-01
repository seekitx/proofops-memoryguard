# Prior Work declaration

## Pre-existing project

Before this Sibyl Hackathon, the builder had a separate SafeHire / ProofOps project:

- Repository: <https://github.com/seekitx/safehire-proofops-bnb>
- Local source used for this migration: `/Users/hun/项目/coin/safehire-proofops-bnb`
- Snapshot date: 2026-08-31
- Snapshot commit: `bf1e1b575cc361d6c8d0949c066cb213b8d38413`

The full copied snapshot is retained locally at
`.prior-work/safehire-2026-08-31/`. That directory is intentionally excluded from
Git and Docker so judges see only the MemoryGuard contest product. The original
repository remains the auditable public history.

## Concepts reused and rewritten

- deterministic fail-closed policy before execution;
- canonical JSON and SHA-256 evidence identifiers;
- secret redaction and explicit evidence labels;
- human wallet confirmation rather than model-held signing authority;
- proof receipts and independent verification as product behavior.

These ideas are reimplemented inside `src/proofops_memoryguard/` for the new
MemoryGuard domain. The old BNB marketplace, Agent categories, ERC-8183 job flow,
and sponsor-specific plugins are not part of the contest runtime.

## MemoryGuard pre-build prototype

The MemoryGuard files below were created locally on 2026-08-31 before the official
2026-09-01 00:00 UTC build window. They are therefore declared pre-build Prior Work,
not contest-period implementation. Their filesystem timestamps or a later Git commit
must never be used to imply otherwise.

- Sibyl Memory Adapter and load-bearing fresh-session recall;
- typed observation quarantine and prompt-injection containment;
- the `observe / decide / finalize` deep Module Interface;
- causal READY → DENY decision diff;
- MemoryProofAnchor design for Base;
- MemoryGuard-specific API, judge page, proof page, tests, and submission documents.

## Required contest-period delta

During the official window, the public history must show substantial new work on top
of this prototype: a real Agent loop whose action changes because of Sibyl recall,
reproducible restart-based fresh-session and deletion evidence, security hardening,
and any exercised Base integration. Merely committing or restyling this pre-build
snapshot after midnight is not an acceptable eligibility story.

## Claims not carried forward

The following SafeHire artifacts do not prove MemoryGuard adoption, PMF, Sibyl use,
or Base integration:

- BSC Testnet Job #808;
- ERC-8004 / ERC-8183 registrations or transactions;
- PancakeSwap, Venus, Lista, or TermiX reports;
- SafeHire Render availability;
- SafeHire's internal adversarial scorecards;
- old screenshots, deployment JSON, or wallet-related runtime files.

They may be cited only as prior engineering context, with their original network,
date, and evidence limits intact.
