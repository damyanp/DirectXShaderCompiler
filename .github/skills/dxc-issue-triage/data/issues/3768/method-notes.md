# Method notes

## Do not reindex from a parallel per-issue worker

I was initially instructed to run `python scripts\triage.py reindex` as the
final completeness check. That instruction was withdrawn mid-flight during the
first parallel batch after the orchestrator identified that `reindex` defaults
`--reset` to true and executes `DELETE FROM issues; DELETE FROM runs;` before
rebuilding from the evidence currently on disk.

That is unsafe while other workers are still writing: it can delete their
in-progress database rows and rebuild from an incomplete view of their files.
The database is derived data, so no evidence files are lost, but its intermediate
results can be misleading and create churn. Per-issue workers should check their
own evidence tree manually; the single-writer collation phase should run the
authoritative reindex after all workers finish.

I did not run `reindex` at any point in this worker. I manually checked this
issue for `expected.md`, repro and command files, per-compiler output, repeated
measurement captures, `notes.md`, `comment.md`, `match.json`, and the Compiler
Explorer record.
