# Batch 014 — orchestrator notes

Read this before doing anything else. Collation is a fresh session by design and never sees
the orchestrator's conversation, so anything not written here is unavailable to you.

## Batch contents

Ten issues: **3902, 3906, 3943, 3954, 4036, 4096, 4168, 4206, 4256, 4273**.

This is the first batch of **ten** rather than five. The change is deliberate and is explained
under "Pipelining" below; it is not a mistake and does not need correcting.

## Ground truth

`main-debug` = clean Debug build of `main` at `13730886e`. Verified at dispatch time:

- the registered exe exists and reports `1.9.0.5433`, matching the registry row;
- `13730886e` is an ancestor of `HEAD`;
- `git diff 13730886e..HEAD` touches **0 files outside `.github/skills/`**, so the build is
  still ground truth for `main`.

The version string embeds `ab5400907`, which is a **fork-local** SHA. The public citation is
`13730886e`. Verbatim captured output containing `ab540090` is evidence and must not be
rewritten; a *citation* of `ab540090` in prose is a defect. Both are correct in different
places — do not "fix" the captured output.

## Pipelining — the one procedural change, and it affects you

Batches now overlap. By the time you read this, **batch 015's workers may already be running**
against the same working directory. Two consequences, both binding:

1. **Do not run `reindex`.** It opens `DELETE FROM issues; DELETE FROM runs;`, which would
   delete rows batch 015's workers are mid-write, and `runs` has no UNIQUE constraint so a
   badly-timed rebuild duplicates probes. The orchestrator now owns `reindex` and runs it as
   the single writer when no workers are live. An authoritative reindex was run immediately
   before this batch was dispatched: **66 issues / 1163 runs, every probe re-scoring as
   captured, none stale, no issue missing required evidence.** That is your clean baseline.
2. **Scope your completeness checking to this batch.** Use `triage.py audit --issue <n>` for
   each of the ten. Do *not* run a bare `triage.py audit`, because with no `--issue` it also
   runs `audit_overview()` across every issue on disk and will report batch 015's in-flight
   issues as gaps. Those are not gaps; they are work in progress.

If you make a change to `triage.py` that alters scoring, say so explicitly in the report. The
next orchestrator-run reindex re-scores every historical probe under your new code, so a real
scoring change will surface there — but only if someone is expecting it.

## Related-issue checks for this batch

Workers are never told what else is in the batch, so convergence is real evidence rather than
suggestion. Two pairings are worth checking at collation, where cross-issue judgement belongs:

- **3943 and the already-triaged 8527.** 3943 is "`#pragma once` cannot support path aliases";
  8527, triaged in batch 004, is "`#pragma once` is case sensitive". Both are about how
  `#pragma once` establishes file *identity*. They may be the same defect wearing two hats, or
  genuinely separate (one about normalisation, one about case-folding). 8527's artifacts are on
  disk under `data/issues/8527/`. Decide deliberately; do not assume either way.
- **4168 and 4206.** Both are reflection issues. 4168 is cbuffer variables missing from a
  *linked* shader; 4206 is a wrong `D3D_SVF_USED` flag in `$Globals`. Probably distinct, but
  they may share a root cause in how reflection is regenerated.

## Hazards this batch is likely to hit

Named as hazards, not predictions. The evidence decides.

- **3906 is reported as an infinite loop.** A hang and an assert are the same defect wearing
  two faces; `#3873` needed `any_of[timeout, internal_failure]` because a bare `timeout`
  predicate scores the Debug ground truth as clean and reports an open bug as fixed. Whether
  that applies here is for the worker to establish.
- **4036 uses `ResourceDescriptorHeap`,** which is SM6.6. Releases predating it will reject the
  input without reaching the code under test. That is the `invalid-probe` trap; the classifier
  should catch it, but confirm it did rather than trusting the range.
- **4168 and 4206 are about reflection data,** which `dxc.exe` does not expose the way a host
  program using `ID3D12ShaderReflection` does. Whether these are verifiable from the CLI at all
  is an open question. `not-compiler-verifiable` is a legitimate outcome and is much better
  than a forced verdict; so is `inconclusive`.
- **4273 concerns the rewriter (`-rewrite`),** a mode this workflow has never exercised. Expect
  the command shape to differ from a normal compile.
- **4096 is labelled `hlsl-next`** and may be a language-design question rather than a defect.
  Where a thread has already diagnosed the behaviour, the useful question is often what
  happened to the *resolution*, not whether it still reproduces.

## Carried forward from batch 013 — one real gap

**Headline claims must live in the `runs` table, or they are not re-verified.** #5293's
regression boundary (clean through v1.7.2212.1, crashes from v1.7.2308) is the single most
important claim that batch produced, and it lives in `manual-case-release-matrix.txt`, produced
by a bespoke script. `reindex` and `audit` therefore never re-check it. It is correct today and
nothing mechanical would tell us if it stopped being correct.

If any issue in this batch produces its headline claim from a hand-run or bespoke measurement,
either get it into the `runs` table or state plainly in the report that it is not covered by
the automatic re-check. Promoting this to `SKILL.md` is a reasonable collation action.

## Also carried forward

- **A neighbouring issue's *measurements* are inheritable; its *explanations* are hypotheses.**
  #3863 falsified #3044's source-derived claim that `-H` cannot run alongside `-P`, by measuring
  it. A note in another issue's `notes.md` is a lead, not a finding.
- **A predicate reads the instrument as well as the behaviour, and instruments change across
  releases.** Batch 013 produced two apparent regressions that were both artefacts: reflection
  metadata relocating into `STAT`, and the disassembler printing `NONE` in 2019 where trunk
  prints `SHDINGRATE`. Both were caught only by a per-release self-test clause.
- **Unresolved from batch 013,** recorded so it is not silently dropped: the
  `outparam-analysis` control in #5293's matrix exits 0 from v1.6.2112 onward, which reads
  ambiguously against the `1380cf88e` boundary. The release-crash transition is the crisp
  evidence and the verdict rests on that, not on the control.

## The path gate is not wired into the per-issue check — fix this

Found mid-batch, and it is the most actionable tooling finding of batch 014.

`check_paths.py` failed across **three** worker directories simultaneously (3943, 4036, 4168),
with a drive letter plus local checkout directory leaking mostly through `manual-case-*.txt`
files that workers generate from bespoke scripts. None of the three workers noticed unprompted,
because **`triage.py audit --issue <n>` does not run the path gate**. The gate is batch-global
and manual, so it is only ever run by whoever remembers, at the end — which is exactly when a
leak is most expensive to fix, and after the point where a worker still owns its directory.

Two changes worth making, both squarely in collation's remit:

1. **Fold the path check into `audit --issue <n>`, scoped to that issue's directory.** Every
   worker already runs `audit` before reporting back, so the leak would be caught by the person
   who created it, while they still own the file. A batch-global gate cannot be fixed safely
   during a parallel phase — nine other workers own the other directories — which is why this
   had to be handled centrally this time.
2. **Record the re-run ordering trap.** #3943's gate run was clean; the worker then added a
   method note *about* another directory's leak, quoted the offending prefix verbatim, and
   manufactured a fresh hit in its own prose. It never re-ran the gate after that edit and
   reported the tree as clean-except-others. The lesson is not "be careful" — it is
   **run the gate after your last edit, not before it**, and describe a path by shape rather
   than reproducing the pattern you are trying to detect. That worker has written this up
   first-hand in `data/issues/3943/method-notes.md`; promote it to `SKILL.md`.

Note the shape of this defect, because it generalises: a check that lives outside the loop
people actually run is a check that reports failures too late to be actionable by the only
person who can safely fix them.

## Converging finding: the control discipline applies to *verification tooling*, not just predicates

Three workers independently produced a **false-negative self-check** while answering the very
narrow question "are any of these gate failures mine?". They caught their own errors, which is
why this is a method finding rather than a defect list:

- one used `Select-String -SimpleMatch` with an alternation pattern, which **disables regex**
  and matches the `|` literally, so the query could never have reported a hit. It printed
  nothing, which is indistinguishable from a pass. The true answer happened to be zero, so
  nothing was missed — but the check was worthless and would have read as authoritative;
- one piped the batch-global gate's output into a file **inside its own issue directory** in
  order to grep it, thereby importing every other worker's leaked path into a clean directory,
  in exactly the escaped form the gate rejects. Spotted and deleted;
- one ran the gate, edited prose afterwards, and never re-ran it.

The common cause is not carelessness — it is that all three wrote a *second, ad-hoc
implementation* of a rule that already had a canonical implementation. The skill already
insists that a predicate is meaningless until it has been run against a known-good input; the
same is true of any query used to verify a claim. Two workers made this explicit and got it
right: one ran the gate's **own matcher** (`import check_paths; find_hits()`) scoped to its
subtree rather than hand-rolling the rule; the other control-tested its query against a fixture
containing all four spellings and required 4/4 matches **before** trusting a zero.

Worth promoting to `SKILL.md` roughly as: *a clean result from an unproven query is worth
nothing — control your verification tooling the way you control a predicate, and prefer calling
the canonical checker over reimplementing its rule.* The three first-hand write-ups are in
`data/issues/{3902,3943,4096}/method-notes.md`.

### The concrete fix workers keep asking for

Independently, several workers proposed the same thing: **give `check_paths.py` an `--issue` or
`--path` filter** so a worker can verify its own subtree during a parallel phase without either
reading peers' failures as its own or hand-rolling the rule. Combine that with folding the gate
into `audit --issue <n>` and the whole class of problem disappears. This is the single highest-
value tooling change available to this batch.

### A latent hole in the gate, verified as not-yet-live

One worker noticed that `check_paths.py` skips any file containing a NUL byte (`if b"\0" in
data: continue`), so a UTF-16 artifact would pass the gate **without ever being scanned** —
relevant because Windows PowerShell 5.1's `>` defaults to UTF-16LE, though the shell in use here
is PowerShell 7.4, whose `>` writes UTF-8.

The orchestrator checked whether this is theoretical or live, and the first check asked the
wrong question — it only tried UTF-16 decodes, which would never reveal an **ASCII** path inside
a binary. That matters because 45 `.pdb` files are committed and debug containers routinely
embed build paths as plain ASCII. Re-run against the **raw bytes** of every skipped file:

```
.bc     40 skipped,  0 contain a machine path
.cso    21 skipped,  0 contain a machine path
.dxbc   51 skipped,  0 contain a machine path
.dxil    1 skipped,  0 contain a machine path
.pdb    45 skipped,  0 contain a machine path
```

**158 skipped files, zero leaks.** So the hole is real but nothing has come through it. Worth
hardening the skip test into a genuine binary sniff; not worth treating as an incident. Recorded
mainly because the first-pass check was itself a false negative of exactly the kind described
above — the orchestrator is not exempt from that failure mode.

## `close-fixed` in this batch requires a blind re-derivation — and there are TWO

**4168** (`does-not-repro`, attributed to `bf015d2e1` in v1.7.2308) and **3954**
(`does-not-repro`, attributed to `0372fb792` / #6930 in v1.8.2502) are the batch's only closable
results, and the skill requires a **blind re-derivation** before a `close-fixed` recommendation
stands. Both workers flagged this themselves, and both described their attribution as
**"strong, not bisected"** over a wide commit window — 257 and 133 commits respectively.

Do the re-derivation independently: do not read the worker's attribution first and then check
it, because confirming someone else's commit is a much easier task than finding it, and it will
feel like verification. Re-derive each transition from the artifacts, then compare.

Two specifics to check rather than assume:

- **4168** measured that **no release ships `dxl`/`dxa`** (0 of 21), so `dxl` ran as `dxc -link`
  and the reflection reader was pinned to the local build. Both deviations were justified with a
  live self-test and a per-release control. Verify those controls hold — a pinned reader is the
  "instrument changes across releases" hazard in another costume.
- **3954** is the stronger of the two on predicate design and is worth reading for that alone.
  It found **one defect with four faces** — `0xC0000005` with *empty* stderr, `0xE0000002`
  "LLVM Unreachable", `0x80AA001C` carrying the reporter's message, and an E_FAIL carrying
  `error: Unexpected matrix subscript use.` Both halves of `internal_failure` are load-bearing:
  E_FAIL is excluded from `INTERNAL_STATUS`, so nine releases match only via the
  `UNREACHABLE executed` marker. Its `manual-case-predicate-counterfactual.txt` **measures** what
  three naive predicates would have concluded, and exit-status-only reports the bug fixed four
  and a half years early. That file is the best argument for the `internal_failure` rule this
  project has produced and belongs in `SKILL.md` as a citation.

## An inherited flag can fake a floor *and* be inert — second instance, different flag

This connects to batch 013 and is worth a `SKILL.md` strengthening.

The skill already warns about inheriting a reporter's stale workaround, using #3768's
`-fcgl -Vd` as the case study: copying it into `cmd.txt` silently disabled legalization and
validation for the whole history search. Batch 013 then found a *second* mechanism — captures
failing with `Unknown HLSL version: 2021` were being scored `no-repro` when they had tested
nothing, and four of #5293's were restamped `invalid-probe`.

**4036 is the two mechanisms compounding, and shows the fix is not just better classification.**
Its repro carried `-HV 2021` from the issue title. That flag demoted four releases to
`invalid-probe`, which manufactured an apparent Shader Model 6.6 floor. The worker did not stop
at "the classifier caught it": it asked whether the flag was doing anything at all, and proved
with a 21-build × 3-case × 2-spelling matrix that it was **inert** — 51 runs identical, 12
differing, and the 12 were exactly the four releases that reject the flag. Dropping it recovered
v1.6.2104, moving the start of the history to **six months before the issue was filed**.

The generalisation to record: classifying a probe as invalid stops it from lying to you, but it
still costs you the datapoint. Where an inherited flag is not load-bearing, *removing* it is
strictly better than classifying around it — it widens the code under test and recovers releases
the classifier would have discarded. The test is cheap and mechanical: run the matrix with and
without, and show the results differ only on the builds that cannot parse the flag.

Two further specifics worth carrying:

- 4036's method notes report that `_predicate_quotes` does not cover a **second**
  `internal_failure` predicate — a tooling defect, deferred to you on purpose.
- 4036 left one absolute path verbatim as evidence: the Windows SDK install location of
  `cdb.exe` inside a captured command line. That is a standard product path, not a checkout or
  user-profile path, and the gate correctly does not reject it. Do not "fix" it.

## Do NOT blanket-`--accept` the two reindex disagreements — they are findings, not rot

The authoritative reindex (76 issues / 1357 runs) reports exactly two verdicts that today's
predicate code scores differently:

```
#3902 variant-od-main-debug.txt:                 control declared no-match but now scores repro
#4206 variant-valver14-main-debug-refl4206.txt:  control declared no-match but now scores repro
```

**Both are correct as they stand, and both should keep their current headers.** The orchestrator
checked each against its artifact and its write-up rather than trusting the summary line:

- **3902** ran `-Od` predicting the optimisation level was load-bearing. It is not — the variant
  still reproduces. The worker wrote up the falsified prediction explicitly: *"I expected the
  exotic `RAY_FLAG_*` template argument to be load-bearing. It is not."*
- **4206** ran `-validator-version 1.4` to test the simpler story that the symptom is "just the
  validator-version gate", declared `--expect no-match`, and **refuted it**. Its notes say the
  expectation was *"tested and refuted rather than quietly presenting a mechanism that had not
  been checked."*

Running `reindex --accept` would restamp both headers to agree with today's scoring, and in doing
so would **destroy the on-disk record that a hypothesis was tested and found false**. The prose
would survive; the artifact would not. That is the wrong direction — the refutation is the more
valuable half of each measurement.

### The underlying defect: `--expect` conflates two different things

This is the method finding, and it will get worse every batch until it is fixed:

- a **control** asserts something that must hold. A mismatch is a defect and should fail loudly;
- a **hypothesis probe** asks a question. A mismatch is a *result*, and often the best one.

`--expect` currently expresses both, so a documented refutation is indistinguishable from a
silently rotted control — and it will be re-reported on **every future reindex, forever**. Two
entries today; more each batch. The predictable end state is that people learn to skim past the
"verdicts that today's predicate code scores differently" section, which is precisely the check
that has caught real defects in earlier batches.

Recommended fix, for collation to weigh: give the runner a distinct declaration for a refuted
hypothesis (`--expect no-match --refuted`, or an `# outcome: refuted` header) so the disagreement
is recorded as a finding, is visible in the artifact, and stops counting as drift. Whatever the
spelling, the requirement is that **a refutation must remain legible on disk without being
reported as an error.**

## Your job

`reindex` is done and is not yours. Otherwise the usual: cross-issue patterns and the two
pairings above, the step-10 independent draft review on a **different model**, `reviewed_by` on
all ten, and `reports/batch-014.md` with the drafts spliced in via
`python scripts/render_comments.py 014`.

Report what the batch taught us about the method. That has been worth more than the verdicts in
every batch so far.
