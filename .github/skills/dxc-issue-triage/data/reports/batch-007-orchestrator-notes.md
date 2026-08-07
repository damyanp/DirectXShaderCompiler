# Batch 007 — orchestrator notes

Written before dispatch. Collation must read this.

| | |
| --- | --- |
| Issues | #2673, #2918, #3005, #3189, #3305 |
| Ground truth | `main-debug`, `ab5400907`, Debug build |
| Version string | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| Model | one isolated session per issue, dispatched in parallel; collation is a separate session |

## Ground-truth check

`git fetch upstream main` reports **0 commits ahead**, so the rebuild the user asked for
before every batch would be a no-op. Recorded rather than skipped silently:

- `ab5400907` is an ancestor of `HEAD` (`8b61ec72e`);
- `git diff ab5400907..HEAD` touches **nothing outside `.github/skills/`**, so the binary
  still measures `main` faithfully;
- `dxc --version` re-read and matches, with no `-dirty`.

Label taxonomy re-fetched: 58 labels.

## The review gate is still suspended

Batches 006–010 run continuously at the user's explicit request, with the per-batch email as
the checkpoint instead. SKILL.md's hard rule ("batch and checkpoint … verdict quality degrades
silently") is knowingly overridden. Nothing in `audit`, `test_predicates.py` or the step-10
review checks whether a verdict is **true** — they check that evidence exists and is
self-consistent. Batch 006's collation introduced two markdown defects into SKILL.md and one
falsification-adjacent quote into a draft; both were caught only by an independent human-side
re-check, not by a gate.

## Sampling has shifted, and it changes what this batch can conclude

Batches 001–005 drew from a pool dominated by `bug` and `crash`. The oldest-untriaged pool is
now visibly **enhancement-flavoured** — of the 17 oldest untriaged issues, 6 carry
`enhancement` and several more are feature requests in all but label. Two consequences:

1. A rising `enhancement-not-bug` rate in later batches is partly an artefact of the pool, not
   a discovery about DXC. The overview must not be read as "the backlog is turning into
   feature requests".
2. Bisection gets less informative: a feature that was never implemented reproduces on every
   release by construction, so `always-repro'd` carries little signal here.

## Why these five

Chosen oldest-first but mixed deliberately, and weighted towards **subsystems no previous
batch has exercised** — five batches of shader-compile issues have stopped finding new tooling
gaps, and the two most valuable findings in batch 006 both came from unusual issue *shapes*
rather than unusual bugs.

- **#2673** (2020-01, unlabelled, 0 comments) — `-D` defines duplicated in debug-info metadata.
  Countable symptom (a list element appearing twice), so the predicate can be exact rather than
  heuristic. Carries a stated **configuration dependence**: the reporter says it appears when
  dxc is driven from the command line but *not* through the test infrastructure, which skips
  work in `dxc.cpp`. Our harness uses the command line — the reproducing path — but that must
  be stated, not assumed.

- **#2918** (2020-05, unlabelled) — PIX numbering pass, `/Od`, subroutines. **The repro is not
  available**: it points at an internal PIX bug number and says to ask two named engineers.
  Deliberately included as a test of honest outcomes — `needs-repro-from-reporter` and
  `not-compiler-verifiable` are legitimate results, and an agent-constructed public repro is
  the only acceptable substitute. Also the first issue in the effort to touch the **PIX passes**,
  which are not reachable through a plain `dxc file.hlsl` invocation.

- **#3005** (2020-06, `bug`, `debug info`) — separate `-Fd` PDB files may have an invalid MSF
  header. Chosen **because #2331 just found that no predicate kind can inspect an output file**;
  the evidence there had to be measured by hand and lives in prose, invisible to `audit`. If a
  second, independent issue hits the same wall in consecutive batches, the gap is systemic and
  worth designing for rather than working around twice. Also one of the few candidates with
  genuine "may have been fixed" potential — it was filed against 1.5.0.2616 and the PDB writer
  has changed since.

- **#3189** (2020-10, `spirv`) — descriptor bindings assigned before dead-code elimination, so
  an unused cbuffer still consumes a binding number. Keeps SPIR-V represented; the symptom is a
  specific decoration value in the disassembly, so the predicate can be positive and exact.

- **#3305** (2020-12, `bug`) — empty payload struct accepted on the SPIR-V path and rejected on
  the DXIL path. A **disagreement between DXC's own two backends** is a shape no batch has
  covered; every previous cross-compiler comparison has been against FXC or Clang. Tiny repro,
  4 comments.

## Briefing discipline carried over from batch 005

A brief may name a hazard but **must not predict the verdict**. Two batch-005 briefs predicted
"history is likely unmeasurable"; one was wrong, and the worker had to contradict its brief to
get the right answer. Each worker below is told what is unusual about its issue and which traps
apply, and nothing about how it is expected to come out.

## Carried into this batch from 006

- The `invalid-probe` classifier now **warns** when an absence-only predicate matches a failed
  compile, rather than demoting it. #3005 and #3305 may both produce absence-shaped predicates;
  if the warning fires, that is the intended behaviour and the fix is to anchor the predicate.
- PowerShell silently eats `$` and backticks from double-quoted prose. Any worker writing a
  summary containing `$Globals`, `$Global`, or a backtick must single-quote it.
