# MemoryGuard judge evidence index

Runtime: `a4b216e73f2eed86ef2e07e2fdece4b48728190c`. Documentation commits do
not change that runtime. All business scenarios are synthetic; no PMF claimed.

| What to inspect | Evidence | Boundary |
|---|---|---|
| English demo, 4m25s | [Public release](https://github.com/seekitx/proofops-memoryguard/releases/tag/demo-a4b216e-20260907) | Core continuous Render take; supplements labeled separately |
| What risk changes | [Outcome table](JUDGE_OUTCOMES.md) | Existing observations, not a new benchmark |
| Official SDK gate | [Release result](../submission/evidence/local-release-a4b216e.json) | Local run; not current hosting health |
| Exact runtime CI | [GitHub Actions](https://github.com/seekitx/proofops-memoryguard/actions/runs/33982006493) | a4b216e |
| VPS restart | [Public-safe A/B](../output/final-release-20260906/new-vps/public-safe-evidence.json) | Session A recovered, not a continuous VPS video |
| Real remote model | [Receipt](../output/final-release-20260906/new-vps/remote-model-receipt-public.json) | Separate later successful request, no authority |
| Storage preservation | [Maintenance](../submission/evidence/capacity-maintenance.json) | All rows retained; backups private |
| Write and restart replay | [Repeat proof](../submission/evidence/capacity-repeat.json) | One diagnostic note; no risk changes or new model calls |
| Gloria | [Integration boundary](GLORIA_NEWS_HANDOFF.md) | News received, seven fingerprints; final platform completion unverified |
| Video identity | [Manifest](../submission/evidence/video-manifest.json) | File hash and source commit |
| Submission | [Status](../submission/status.json) | Private portal URL and secrets are never published |

The free cap still applies until legitimate account entitlement is wired. File
compaction reclaims already unused pages; it does not erase records or grant an
entitlement. Sustained capacity and a full repeat of every product scenario are
not established by the single diagnostic-write probe.
