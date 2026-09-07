# Gloria: external news, not independent security review

Gloria job `1003558157` delivered ten AI AGENTS news items to MemoryGuard Research
Buyer for 0.01 USDC. At the latest read the protocol state remains `EVALUATION`;
delivery is observed, final completion is not. News claims are not verified facts.

`scripts/gloria_news_handoff.py` reads only an existing purchased job from the
official authenticated API. It checks job, buyer, provider, offering, requested
category and bounded news structure. It never creates or pays for jobs, fetches
article links, changes risk state or grants authority. Credentials stay outside
the repository in a private regular file. Each run requires a new output directory.

Read and prepare:

```sh
python3 scripts/gloria_news_handoff.py --job-id 1003558157 \
  --acp-credentials "$HOME/.config/memoryguard/acp-research-buyer.json" \
  --out /private/new-gloria-observation
```

To import, add `--import-notes --memoryguard-token /private/operator-token`
and `--scope /private/existing-scope.json`. The token must be a 0600 regular file;
the scope must exactly match an existing task visible to that operator. The URL
is fixed to the current public MemoryGuard host. Import uses the existing
`/api/v2/notes` interface and preserves its scope and revision checks.

Each article becomes an explicitly untrusted note. Sibyl retains the existing
quarantine event/content fingerprint, not the raw article or a trusted fact.
Raw delivery is retained separately in the operator's output directory for manual
inspection. This is an external-news quarantine handoff, not a new evidence-desk
connector, automated risk detector or completed ACP independent review.

The script records each successful note response before proceeding. Network
failures stop without automatic retries; inspect partial output before resuming.
Deterministic job/article idempotency keys prevent a silent duplicate import.

Current validation: real Gloria read/prepare succeeded for ten items. Python
syntax was inspected; no build or test suite was run. Production import partially succeeded: seven quarantine records persisted at
revisions 74–80. Three articles remain unimported because the official Sibyl client
rejected further writes at the 5 MB free-tier cap without an activated account.
SSH access was rechecked successfully. The store currently does not pass account
credentials into MemoryClient.local; activation alone will not wire entitlement.
The temporary operator was removed and the original registry restored.
The existing frozen production runtime was not changed. Do not claim all ten
imports, unchanged task-state verification, or completed ACP settlement.
The budget-conscious contest cut uses the existing seven records; importing the
remaining three is not required for that recorded demonstration. No new purchase
is authorized by this plan. Further production writes remain blocked, and online
interactive readiness must not be claimed. If additional capacity is required,
obtain legitimate entitlement and securely wire credentials; do not delete memory
or bypass quota checks.

## September 7 maintenance and evidence refresh

The capacity failure above is historical: preserving all records and compacting
unused SQLite pages reduced the file from 5,173,248 to 3,608,576 bytes. A subsequent
authenticated diagnostic note write succeeded. Its identical request replayed
without another revision, including after a service restart; tasks and cases were
unchanged by that diagnostic. This does not retrospectively assert a before/after
comparison for the original Gloria import. Seven Gloria receipts were recovered
and are included in [the repeat proof](../submission/evidence/capacity-repeat.json).
No further news was purchased or imported. Platform completion remains unverified.
The contest portal advertises Pro access at no cost through the event; no paid
upgrade is needed to activate that offered entitlement.
