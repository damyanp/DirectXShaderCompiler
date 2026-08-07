<!-- Orchestrator notes for batch 006. Written during the batch, not after.
     Collation should fold the relevant parts into reports/batch-006.md and
     decide what belongs in SKILL.md. -->

# Batch 006 — orchestrator notes

First batch of a **five-batch continuous run** (006–010) authorised by the maintainer. This
changes one thing that matters, and collation must not lose sight of it.

## The review gate is suspended, deliberately and with the risk named

`SKILL.md`'s hard rules say:

> **Batch and checkpoint.** Triage a handful of issues, then stop and let a human review
> before continuing. Verdict quality degrades silently; unattended full passes hide that.

The maintainer was asked directly about this before the run started, and chose to run all five
batches continuously, with an emailed summary after each acting as an asynchronous checkpoint
rather than a blocking one.

**That is a real reduction in safety and should be treated as one.** The rule exists because
verdict quality degrades *silently* — the failure mode is not a crash, it is a batch of
confident, plausible, wrong verdicts. Nothing in this run detects that automatically.

What compensates, partially:

- every batch is committed and pushed separately, so a bad batch can be reverted alone;
- collation is a fresh session each time, and cannot inherit an earlier batch's assumptions;
- the independent draft review (step 10) still runs per batch, on a different model;
- `audit` gates on evidence completeness and overview staleness.

What does *not* compensate: none of those check whether a verdict is **true**. Collation should
say plainly in the report if it sees quality slipping, and should not smooth it over.

## Setup

| | |
| --- | --- |
| Ground truth | `main-debug`, Debug build at `ab5400907` |
| Rebuild | **not needed** — `git fetch upstream main` showed 0 commits ahead of HEAD, so the batch-005 build is already current. Version string re-verified against HEAD rather than assumed |
| Labels | 58, re-fetched |
| Issues | #2128, #2331, #2528, #2792, #3251 |

The maintainer asked for a rebuild before every batch. Upstream had not moved, so a rebuild
would have produced an identical binary; the *check* was performed and the result recorded,
which is what the instruction is actually for.

## First action: #2202's stale headers, carried over from batch 005

Batch 005 found three `variant-*.txt` in #2202 (batch 004) whose `# verdict:` lines disagreed
with the current classifier, and left them uncorrected as out of scope. Corrected here with
`reindex --accept` as batch 005 recommended.

Exactly the three predicted files changed, and **only their headers** — verified by diff. Two
were re-scored `invalid-probe` because their output matches the HLSL-2021 feature-absence marker
`for non-scalar types use 'select'`, and one because the probe failed internally. No captured
output, command line or exit status was altered, and #2202's issue-level verdict is unaffected.

The new `# invalid-probe-reason:` line added in batch 005 is what makes this checkable at a
glance; before it, confirming these three would have meant re-deriving `classify()` by hand.

## Why these five

Oldest-first, which is the strategy the maintainer chose for the whole run, with a deliberate
mix so the batch is not uniform:

- **#2128** (2019-04, `dxil`, `revisit-sooner`) — the oldest untriaged open issue. **No code
  block and 4 comments**, so the repro is prose-only at best; a realistic test of the
  `agent-constructed` path and of `not-compiler-verifiable` as an honest outcome.
- **#2331** (2019-07, `bug`) — DXIL *signing* with switch/enum. Signing is a code path no batch
  has exercised.
- **#2528** (2019-10, `bug`, `fxc-disagrees`) — exercises the contrasting-FXC pane.
- **#2792** (2020-03, `bug`) — "**Need to report error when** ... offset bigger than root
  constant size". A **missing-diagnostic** issue, prose-only, no comments. This is the batch's
  designed test: batch 005 rewrote the `invalid-probe` classifier precisely because diagnostic
  symptoms collide with feature-absence markers, and this is the first issue triaged under the
  new code whose expected behaviour is *an error that does not currently appear*. Note the
  inversion — here the symptom is the **absence** of a diagnostic, where #3055's was its
  presence. If the fix generalised, it should hold; if it only patched #3055's shape, this is
  where that shows.
- **#3251** (2020-11, `bug`, `crash`) — recommended by batch 005's report. Same reporter as
  #3259 (batch 005), filed one day earlier; batch 005 established from source that it still
  traps on `main` but in `TranslateCBAddressUserLegacy` rather than `WrapInArrayTypes`.
  **The worker is not told this.** Whether the two are duplicates is collation's question, and
  batch 005's finding is on disk for collation to check the worker against.

## Standing worker rules (unchanged, and they held in batch 005)

- Addressed by explicit agent id, never `scope=children`.
- Boundary stated as an absolute path.
- Workers run `audit`, never `reindex`.
- No cross-issue claims in drafts; those go to `method-notes.md`.
