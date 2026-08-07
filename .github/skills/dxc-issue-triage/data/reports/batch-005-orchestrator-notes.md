<!-- Orchestrator notes for batch 005. Written during the batch, not after.
     Collation should fold the relevant parts into reports/batch-005.md and
     decide what belongs in SKILL.md. -->

# Batch 005 — orchestrator notes

Batch 005 is the **second batch under the per-issue parallel model**. Batch 004 ended with an
explicit prediction, and this batch is the test of it:

> Three of the four defects batch 004 exposed were *caused* by parallelism rather than revealed
> by it. The next parallel batch should be much cheaper. If it is not, that is the signal to
> revisit.

Collation should answer that question directly, with evidence, and should not be gentle about
it. "Cheaper" means: fewer shared-state incidents, less redundant method reporting, and a
lighter collation session — not merely "no disasters".

## Setup

| | |
| --- | --- |
| Ground truth | `main-debug`, Debug build of `triage` at `ab5400907` (merge of `upstream/main` `13730886e`) |
| Source unchanged | verified: `git diff upstream/main..HEAD` touches 0 files outside `.github/skills/` |
| Labels | re-fetched the day of the batch: 58 labels |
| Issues | #2530, #3055, #3259, #8725, #8732 |

### The ground truth was rebuilt for this batch, deliberately

Batches 001–004 all used `eff900d5`. That build was 5 commits stale by the time batch 005
started, and one of those commits — `ec2ba18da`, "Update SPIRV-Tools to 1c336172" — touches
`external/SPIRV-Tools` and `tools/clang/test/CodeGenSPIRV/resource-heap-ext-texture.hlsl`.
**#8732 is a `SPV_EXT_descriptor_heap` issue**, so it sits directly in that commit's blast
radius, and #8740 ("DXC SPIR-V test fail with the latest spir-v tools") confirms the area is
actively churning right now.

Triaging a days-old SPIR-V miscompile against a build that predates the relevant SPIRV-Tools
bump risks exactly the class of wrong verdict this workflow exists to prevent. So
`upstream/main` was merged into `triage` (clean, verified with `git merge-tree` first), the
`external/SPIRV-Tools` submodule was updated to `1c336172`, and `dxc` was rebuilt in Debug.

**The cached version headers were deleted before rebuilding.** `SKILL.md`'s setup section warns
that DXC does not regenerate `version.inc` / `dxcversion.inc` when the branch changes, so a
freshly built binary can report a stale commit. After a merge this is not hypothetical — it is
the expected failure. Removing them is what makes the version string trustworthy.

**Consequence for cross-batch comparison:** batch 005's verdicts are measured against a
different compiler than batches 001–004. That is recorded per-issue in `triaged_with_commit`
and surfaced in `overview.md`, so nothing is ambiguous, but collation should not silently
compare a batch-005 result against a batch-004 result as though they shared a ground truth.

## Why these five

Batch 004's report closed with two explicit recommendations. Both are honoured:

- **#3055** — `tech-debt`, `diagnostic`. *This is the batch's designed test.* Batch 004's
  "Suggested next step" called out that **no batch has yet triaged an issue whose reported
  symptom is a diagnostic**, and that this is where the `invalid-probe` classifier is least
  trustworthy. The failure mode is structural: `invalid-probe` exists to detect "this release
  rejected the input without reaching the code under test", but when the *expected* outcome is
  itself a rejection, the classifier's signal and the symptom are the same observation. If this
  batch produces one wrong verdict, the prior says it is here.
- **A second parallel batch**, to test the cost prediction above.

The rest of the mix follows `SKILL.md`'s warning that an all-oldest batch is unrepresentative:

- **#2530** (2019-10, `bug`, `fxc-disagrees`) — "Array bound with static const variable".
  Exercises the contrasting-FXC pane. **Also a deliberate duplicate probe:** batch 004 found
  #2188 to be about `static const` *vectors*, not scalars, and #2530 is `static const` in a
  different position again. Whether these are the same defect is a question for collation, not
  for any worker. The `duplicate-of` suggested action still has **zero rows** across 20 issues,
  so it has never been exercised end-to-end.
- **#3259** (2020-11, `bug`, `dxil`, `crash`) — crash-shaped, so it exercises
  `internal_failure` and bisection over a long history.
- **#8725** (2026-07, `bug`, `needs-triage`) — an assert in SER `HitObject::Invoke`. SER is a
  recent feature, so most releases cannot compile the repro at all: this is a **forward**
  feature-absence test, the trap batch 004 recorded as item 5.
- **#8732** (2026-08, `bug`, `spirv`, `needs-triage`) — a *silent miscompile*, which is the
  hardest symptom shape to write a predicate for, since there is no exit code to key on.

Symptom shapes across the batch: diagnostic quality, wrong-code vs FXC, crash, assert, silent
miscompile. Ages: two 2019–2020, one 2020, two 2026.

## Worker boundaries

Batch 004's incident — a broadcast reaching four idle agents from earlier batches and
triggering an unrequested re-triage of #3768 — produced two rules, both applied here:

1. **Address workers by explicit agent id, never by `scope=children`.**
2. **State each worker's boundary as an absolute path**, not as "your issue". The phrase
   resolves differently in a context the orchestrator did not write.

## Tooling fixed since batch 004

Workers are briefed that these are already fixed, so that a rediscovery is a *new* finding
rather than an echo:

- `reindex` is collation's command. Workers run `audit`, which reads and writes nothing.
- `reindex` no longer discards database-only columns.
- Probes are filed per-predicate (`out-<compiler>--<predicate>.txt`), and `execute()` refuses to
  overwrite a capture recorded under a different predicate.
- `--reset` is no longer a flag that could not be turned off by its own name.
- `main()` propagates command exit codes, so `audit` can actually gate.

If a worker reports one of these as broken, that is a regression and collation should treat it
as such.

## In-flight observations

Recorded as they happened, so that the "was it cheaper?" question is answered from contemporaneous
evidence rather than from recollection after the fact.

### Shared state held, checked independently rather than taken on trust

Both #2530 and #3259 self-reported running `audit` and never `reindex`. Self-reports are not
evidence, so the orchestrator checked directly while the other three workers were still running:

| Check | Result |
| --- | --- |
| `git status` on `SKILL.md`, `README.md`, `scripts/` | clean |
| `git status` on DXC source (everything outside `.github/skills/`) | clean |
| issue directories touched | exactly `2530`, `3055`, `3259`, `8725`, `8732` — no strays |
| `issues` row count | 25 = 20 prior + 5 new; **every prior batch still has exactly 5** |
| `runs` row count | 358, growing monotonically |

**This is the batch-004 prediction being tested, and so far it holds.** At the equivalent point in
batch 004 the database had already been churned by workers running `reindex`, #2191 had lost its
title and `batch` column, and three workers had hit the predicate/filename collision. None of that
has recurred. The three defects were caused by parallelism, and fixing them appears to have
removed the cost rather than merely relocating it.

Collation should re-verify these numbers rather than quote this table — a claim that shared state
was never violated is exactly the sort of claim that should not rest on the word of the process
that would have violated it.

### The worker brief absorbed batch 004's incident

Workers were addressed by explicit agent id, never `scope=children`, and each was given its
boundary as an absolute path (`...\data\issues\<nnnn>\`) rather than as "your issue". No
out-of-batch issue directory has been touched. Batch 004's #3768 incident has not recurred.

### The ground-truth rebuild was load-bearing, not precautionary

The rebuild was justified above on the grounds that #8732 sat in `ec2ba18da`'s blast radius.
That turned out to be an understatement, and it is worth recording that the justification was
*tested* rather than merely asserted.

#8732's worker found that **the reporter's own suggested workaround compiles on the v1.9.2607
release binary but fails on `main`**, because `ec2ba18da` (SPIRV-Tools → `1c336172`) newly
enforces a `UniformConstant` ArrayStride rule. On the old `eff900d5` ground truth that
divergence did not exist and would not have been observed. The worker also reports that today
*no* `-fspv-use-descriptor-heap` shader validates on `main` at all — which is issue #8740,
independently rediscovered from the compiler rather than from the backlog.

Had batch 005 run on the stale build, the finding would have been missed entirely and the
report would have been confidently wrong about the current state of the feature.

### Two workers converged on the `invalid-probe` classifier, independently

This is the convergence signal the parallel model is supposed to produce, and it appeared
without prompting:

- **#3055** was *dispatched* to probe the classifier, and found the hazard real in two
  directions, escaping only because dxc says `no matching **member** function for call to`
  where the marker is `no matching function for call to`.
- **#8732** was given no such brief, and hit the same classifier from a different angle: the
  marker `is not supported` collides with legitimate compiler output in its issue's area.

Neither worker could see the other. Collation should weight this accordingly: one observer
finding a defect twice is one datapoint, but two isolated observers reaching the same component
by different routes is a much stronger argument that the component — not the issue — is the
problem.

### A worker contradicted its own brief, correctly

#8725's brief stated, at length, that SER is recent and therefore "most or all shipping releases
will not be able to compile the repro at all", and that the honest finding was likely to be
"history is unmeasurable".

**That was wrong, and the worker proved it wrong rather than confirming it.** SM 6.9 shipped in
v1.8.2505, so 5 of the 20 bisectable releases can express `-T lib_6_9`, and all 5 reproduce. The
worker established this with a feature-presence control (`control-hello.hlsl`) that the other 15
releases also reject and that v1.8.2505+ accept — so the `invalid-probe` classification was
*proved* rather than assumed.

This is worth recording because it is the failure mode the per-issue brief is most likely to
cause. The brief is written by the orchestrator, who has not done the triage, and a worker that
treats it as authoritative will confirm whatever it says. Batch 004's report worried about
context leaking *between* workers; this is context leaking *downward*, and it is the more likely
direction because it is sanctioned.

**Suggested rule for `SKILL.md`, for collation to judge:** a brief may name a hazard to check,
but should not predict the verdict. "SER is recent, so establish which releases can express the
repro before interpreting a clean history" carries the warning without supplying the answer.
Two of the five briefs in this batch predicted `history is likely unmeasurable`; one of those
predictions was wrong.

## Final tally — the batch-004 cost prediction

Batch 004 predicted the next parallel batch would be "much cheaper", with three of its four
defects having been *caused* by parallelism rather than revealed by it. Measured:

| | batch 004 | batch 005 |
| --- | --- | --- |
| workers that ran destructive `reindex` | 5 of 5 | **0 of 5** |
| rows lost / issues arriving with NULL columns | #2191 (title, url, batch) | **none** |
| predicate/filename collisions | 3 of 5 workers; 20 captures lost | **none** |
| out-of-batch directories modified | 1 (#3768, an earlier signed-off batch) | **none** |
| shared-state writes (`SKILL.md`, `scripts/`, DXC source) | — | **none** |

The prediction held. Every defect batch 004 attributed to parallelism stayed fixed, and the
orchestration incident did not recur under explicit-agent-id addressing.

**Collation should verify this table independently** — it is the orchestrator grading its own
homework, and the numbers for batch 004 are quoted from that batch's report rather than
re-derived.

What batch 005 spent its budget on instead was *findings*: the `invalid-probe` × diagnostic
hazard (#3055, two directions, both reachable), the descriptor-heap issue being filed against an
unmerged PR (#8732), and a `text_stale`/`audit` expressiveness gap. Those are defects the method
revealed rather than caused, which is the distinction that matters.
