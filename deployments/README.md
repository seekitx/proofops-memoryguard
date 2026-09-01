# Base deployment evidence

No MemoryProofAnchor deployment is claimed yet.

When the user explicitly authorizes a Base deployment, `contracts/deploy.cjs` writes
the resulting network record here. A deployment record is not partner credit by
itself. The final demo must also exercise the contract through the user's wallet and
the backend must independently verify the receipt and emitted proof root.
