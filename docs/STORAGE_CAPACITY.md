# Capacity maintenance and repeatability

On 2026-09-07 the database occupied 5,173,248 bytes with 383 free 4-KiB
pages (about 1.50 MiB unused). Entities used 380,928 bytes on disk with
353,983 payload bytes; search-shadow data used 2,031,616 bytes. Rewriting an
atomic workspace also updates full-text search indexes, so the file footprint
is larger than the news text. The official client checks estimated growth
before writing; a file slightly below the cap can still reject a write.

Maintenance stopped only MemoryGuard, retained private byte copies of the
database and any WAL/SHM files, then used standard SQLite VACUUM. Every table
and applicable row identifier matched before and after; quick_check returned
ok. No rows, audit events or quarantine records were deleted. No SDK quota,
tier or credentials were altered. The compacted file was 3,608,576 bytes.

One authenticated diagnostic note then moved revision 80 to 81; the identical
request returned the same revision without another write. Restarting the actual
service changed runtime ID; the same command again replayed revision 81. Tasks
and cases were unchanged by the diagnostic. The temporary actor was removed
and the exact original registry restored. The resulting database was 4,509,696
bytes, so this is a bounded recovery, not proof of indefinite free-tier capacity.

[Maintenance evidence](../submission/evidence/capacity-maintenance.json) and
[write/replay receipts](../submission/evidence/capacity-repeat.json).
Backups and account credentials remain private and outside Git.

## Sustainable contest path

The private build portal explicitly advertises free Pro access with the storage
cap lifted throughout the hackathon. Activate a legitimate plugin account and
wire its server-issued credentials into the runtime; never edit tier flags to
pretend to have entitlement. At this report's time activation/wiring is pending.
No paid subscription is required by the advertised event offer.

Do not rerun large paid model workflows just for demonstrations. Reuse existing
immutable evidence and idempotency keys for review. For maintenance, require a
backup, exclusive downtime, before/after logical equality and service recovery.
Do not automatically compact on every error or delete history to make checks pass.

SQLite reference: https://www.sqlite.org/lang_vacuum.html
