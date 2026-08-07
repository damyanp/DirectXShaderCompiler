<!-- Orchestrator notes for batch 004. Written during the batch, not after.
     Collation should fold the relevant parts into reports/batch-004.md and
     decide what belongs in SKILL.md. -->

# Batch 004 — orchestrator notes

Batch 004 is the **first batch run under the per-issue parallel model**: five workers, one
issue each, no worker aware of the others' issues, with collation performed separately by an
agent briefed only by what is on disk.

## Setup

| | |
| --- | --- |
| Ground truth | `main-debug`, clean Debug build of `main` at `eff900d5` |
| Version string | `1.9.0.15422 (main, eff900d54)` — verified against the registered commit |
| Source unchanged | `git diff eff900d54..HEAD` touches **0** files outside the skill directory |
| Labels | re-fetched the day of the batch: 58 labels |
| Issues | #2188, #2191, #2202, #8527, #8737 |

## Why these five

Deliberately mixed, per SKILL.md's warning that an all-oldest batch is unrepresentative:

- **#2188, #2191, #2202** — the next un-triaged issues in oldest-first order (all 2019-05),
  which is the ordering the backlog pass follows.
- **#2188** carries `fxc-disagrees`, so it exercises the contrasting-compiler pane.
- **#2191** is crash-shaped, so it exercises `internal_failure` and bisection.
- **#2202** is a DXIL validation issue, which tests whether the `validation` label is applied
  with its narrow meaning.
- **#8527** was chosen to close a known gap: **`cmd.txt` has never been exercised with a
  multi-file repro or `-I`**, and `#pragma once` needs one by construction. It is also
  filesystem-sensitive, and the ground truth is Windows.
- **#8737** is days old and carries `needs-triage`, testing whether the workflow adds value
  where *history* is not the interesting output.

#2188 and #2191 are both 2019-05 issues about `static const` integers. **Whether they are
duplicates is a question for collation, not for either worker** — neither was told the other
exists, which is the point. If they independently converge on the same defect, that is a
stronger duplicate finding than one agent noticing two similar titles.

## Method finding: `reindex` is unsafe to run concurrently

Found during this batch, on the first parallel run, before any worker had finished.

`cmd_reindex`'s `--reset` argument is declared `action="store_true", default=True`, so the
**default** path executes:

```sql
DELETE FROM issues; DELETE FROM runs;
```

and then rebuilds both tables from whatever is on disk at that instant. Single-threaded that is
exactly right, and it is what makes re-scoring possible. Run concurrently it is destructive:

- A worker finishing at T deletes rows that other workers are still writing. Rows are restored
  only for evidence already flushed to disk, so a worker that has captured output but not yet
  written `verdict.json` loses its issue row.
- `runs` has no UNIQUE constraint. If a reindex lands between another worker's file write and
  its own `INSERT INTO runs`, that probe is inserted twice.
- The completeness audit reports gaps for *every* issue, so a worker running it mid-batch sees
  other workers' work-in-progress reported as missing evidence — noise that invites a worker to
  "fix" something that is not broken.

**The original per-issue brief told every worker to run `reindex` as a final check.** That
instruction was withdrawn mid-flight and the workers were asked to self-check by hand instead,
and to record the hazard in their own `method-notes.md`.

Nothing was lost: the database is derived, the evidence on disk is the source of truth, and a
single authoritative `reindex` after all workers finish restores a correct index. But it is a
real defect in the tool under the parallel model, and it argues for one of:

- making `reindex` refuse to run while another triage process holds a lock; or
- defaulting `--reset` to false and giving the destructive rebuild its own explicit flag; or
- reserving `reindex` to the collation phase, and documenting that per-issue workers must
  never call it.

Collation should decide which, and the fix belongs to collation rather than to this note —
`triage.py` is shared state, and changing predicate or tooling behaviour mid-batch would
invalidate verdicts already written by workers that had finished.

**A single `reindex` must be run during collation, before anything is written**, both to
restore a correct index and to re-score every probe in the batch.

### Confirmed: the database *was* churned

Workers self-reported running bare `reindex` before the withdrawal reached them:

| worker | times | when |
| --- | --- | --- |
| #2188 | 4 | during triage |
| #2202 | 4 | ~01:10–01:14 UTC |
| #8527 | 3 | ~01:18–01:21 UTC |

So the index is not trustworthy until collation rebuilds it. No evidence was lost — every one
of them confirmed `git status` clean outside their own directory — but at least one worker had
in-flight DB state destroyed by another's reindex and had to repair it by re-running `fetch`,
`godbolt` and `verdict`.

## Found from outside the workers

Three things the orchestrator observed that no single worker could see. Collation should verify
each independently rather than take this note on trust.

### 1. #2191's primary probes were overwritten (real, and it happened here)

`triage.py:776` builds the output filename from compiler and `--label` only — **the predicate is
not part of it**:

```python
out_path = os.path.join(
    d, f"variant-{label}-{compiler}.txt" if label else f"out-{compiler}.txt")
```

So a second `bisect --match <other>.json` silently overwrites the first predicate's per-release
probes. Measured across the batch by reading the `# match:` header of every `out-*.txt`:

| issue | out-* files | produced by |
| --- | --- | --- |
| #2188 | 21 | `match.json` × 21 |
| #2191 | 21 | **`match-rejected.json` × 20**, `match.json` × 1 |
| #2202 | 21 | `match.json` × 21 |
| #8527 | 3 | `match.json` × 3 |
| #8737 | 21 | `match.json` × 21 |

#2191 is the live casualty. It was **not** asked to re-run 20 probes, because the archived files
still carry the full raw output and the `# exit:` header, so the underlying measurement survives
and `reindex` re-scores from the `# match:` header rather than assuming `match.json`. What was
lost is only the *recorded scoring* under the primary predicate. #2202 and #8737 avoided the
collision by capturing their second predicate under `--label`, which is the workaround; #2202,
#2188 and #8527 all reported the same defect independently.

The tool gives no warning, and an overwritten probe looks exactly as authoritative as the one
that replaced it. Candidate fixes, for collation to choose between: put the predicate stem in
the filename; refuse to overwrite a probe whose header names a different predicate; or make
`--label` mandatory for any non-default `--match`.

### 2. `reindex` rebuilds `issues` from `verdict.json` alone

Reported by #8527 and confirmed: `title`, `url`, `created_at` and `labels` written by `fetch`
are **dropped** by a reindex unless they also live in `verdict.json`. `render_comments.py` takes
issue titles from the database, so a batch report generated after a reindex can silently lose
them.

Checked across all 20 issue directories: **19 of 20 `verdict.json` carry a title; #2191 does
not.** Collation should confirm this after its reindex and repair with `verdict --title` rather
than hand-editing, or the batch-004 report will render #2191 without a title.

### 3. `write_agent scope=children` is not scoped to the current batch

The withdrawal broadcast reached **9** agents, not the 5 workers — it also woke four idle
draft-reviewer agents left over from batches 002 and 003.

**This caused a real incident.** One woken reviewer, whose stale context was batch 002, read
"add it to your `data\issues\<your-issue>\method-notes.md`" as applying to **#3768** and
performed an unrequested re-triage of it between 17:58 and 18:03: it rewrote `verdict.json`,
`comment.md`, `notes.md`, `cmd.txt`, `match.json` and `godbolt-note.txt`, and added three new
files including a 436 KB captured `--repeat` measurement set.

#3768 is **batch 002** — already reviewed, signed off, committed and reported to the
maintainer. Modifying it silently is exactly what the review gate exists to prevent.

Handled as follows, and **nothing was discarded**:

- the tracked diff was saved as a patch and the three new untracked files copied to a
  quarantine directory outside the repo;
- `git checkout` restored the six tracked files; the three untracked files were removed;
- `#3768` is now byte-identical to its committed state, and the decision on whether to adopt
  any of the changes is the maintainer's, not collation's.

For the record, the changes were **not junk**, which is what makes the incident instructive:
the rewritten summary replaced the unbacked hit-rate "68–82% of runs" with counted, captured
figures (33/40 at v1.6.2104, 28/40 at v1.6.2106, 30/30 clean at v1.5.2010 and v1.6.2112, 55/55
clean on current builds) and named PR #4280 as the SPIRV-Tools fix. That directly closes the
durability gap #2191 identified — that `--repeat` aggregates live only in the database and are
destroyed by a reindex. One change was a regression: `match.json`'s note lost the "E_FAIL alone
is NOT internal" caveat.

**Collation must not act on this.** It is recorded here so that a reader who notices #3768's
history is not left guessing. If collation finds #3768 dirty in `git status`, something has
gone wrong and it should stop and say so.

Two lessons for `SKILL.md`: address workers by explicit agent id rather than by scope, and
**a worker's boundary must be stated as an absolute path, not as "your issue"** — a phrase that
resolves differently in a context the orchestrator did not write.

## All five workers ran `reindex` before the withdrawal reached them

| worker | times |
| --- | --- |
| #2188 | 4 |
| #2191 | 2 |
| #2202 | 4 |
| #8527 | 3 |
| #8737 | 2 |

Two of them independently reported having their *own* in-flight row destroyed by another
worker's reindex — #8737 lost `title`, `url`, `created_at`, `labels` **and `godbolt_url`**, and
noticed only because `labels --issue 8737` printed `now: (none)`. Both repaired it by
re-supplying values from their own `issue.json`. A verified, published Compiler Explorer link
was one `audit_issue` run away from being reported as missing evidence.

`--repeat` aggregate rows are written as `(see single runs)` with **no backing file**, so they
are the one thing a reindex genuinely cannot restore. Collation should treat any `--repeat`
hit-rate in the database as unreliable and take it from captured files instead.
