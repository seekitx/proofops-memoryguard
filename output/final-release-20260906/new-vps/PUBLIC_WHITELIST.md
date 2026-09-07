# Public evidence whitelist

Only these files are safe for public release:

- `output/final-release-20260906/new-vps/public-safe-evidence.json`
  - SHA-256: `726468ad47fd76496c9f0fe6d41ada61806623fff616f87af8641e03d12b29ea`
- `output/final-release-20260906/new-vps/http-results.json`
  - SHA-256: `ece06818a185f98904fdf43cee4aa94c58da17bd1803ca0f30f8ec8d30bf2fb8`
- `output/final-release-20260906/new-vps/BOUNDARIES.md`
  - SHA-256: `e2030bb5a72c2f579a3d369598a3595a59a3bcdb19391c0fbbeb5708cd2cb459`

`new-vps-final-evidence.json` is the complete internal record. Keep it out of public uploads because it contains deployment-internal details.

The public record is `PASS_WITH_LIMITATIONS`: Session A is live-state recovery after recorder timeout, and the remote model receipt gate is not passed (`HTTP 200`, `DEGRADED`, no receipt or generation ID).

A later independent request after the model switch passed. The original A/B evidence remains unchanged.

- `output/final-release-20260906/new-vps/remote-model-receipt-public.json`
  - SHA-256: `709690b9c454cfc689fc01d8eb98308062dfa421d656691b40108ff3563fe7a8`
