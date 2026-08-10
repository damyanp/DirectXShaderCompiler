# Batch 015 — orchestrator notes

Read this before doing anything else. Collation is a fresh session by design and never sees the
orchestrator's conversation, so anything not written here is unavailable to you.

## Batch contents

Ten issues: **4307, 4341, 4350, 4351, 4384, 4415, 4486, 4492, 4497, 4501**.

## Ground truth

`main-debug` = clean Debug build of `main` at `13730886e`, reporting `1.9.0.5433`. Verified at
batch-014 dispatch: the registered exe matches the registry row, `13730886e` is an ancestor of
`HEAD`, and `git diff 13730886e..HEAD` touches **0 files outside `.github/skills/`**, so the
build is still ground truth for `main`.

The version string embeds `ab5400907`, a **fork-local** SHA. The public citation is
`13730886e`. Verbatim captured output containing `ab540090` is evidence and must not be
rewritten; a *citation* of `ab540090` in prose is a defect.

## Pipelining — read this before touching the database

Batches overlap. **Batch 014's collation was running when this batch was dispatched**, and batch
016's workers may be running by the time you read this.

- **Do not run `reindex`.** It opens `DELETE FROM issues; DELETE FROM runs;` and `runs` has no
  UNIQUE constraint, so a badly-timed rebuild deletes in-flight rows or duplicates probes. The
  orchestrator owns `reindex` and runs it as single writer when no workers are live. The last
  authoritative run covered **76 issues / 1357 runs**.
- **Scope completeness checking to your own ten** with `triage.py audit --issue <n>`. A bare
  `audit` also runs `audit_overview()` across every issue on disk and will report another
  batch's in-flight work as gaps. Those are not gaps.
- **Tooling changes must be additive and backward-compatible** while another batch is in flight.
  Do not change the meaning of an existing flag or predicate under a running worker. Run
  `test_predicates.py` after any change and say loudly in the report if scoring changed.

## Related-issue checks for this batch

Workers are never told what else is in the batch, so convergence is real evidence rather than
suggestion. This batch has neighbours **inside** it and neighbours in **batch 014**, which was
being collated in parallel — so check batch 014's finished artifacts too:

- **4351 (rewriter incorrectly removes types used in a member array) and 4273 (batch 014,
  rewriter cannot remove an unused `cbuffer`).** Batch 014 established that `dxc.exe` cannot
  reach the rewriter at all — `dxr.exe` is the instrument, `bisect` refuses a non-`dxc` harness,
  and v1.4.1907 is an invalid probe because its option table has no `RewriteOption`. All of that
  is measured and reusable. Note the two issues pull in **opposite** directions: 4273 wants the
  rewriter to remove more, 4351 says it already removes too much. If both are valid, that is a
  finding about the pass's reachability analysis, not two unrelated bugs.
- **4415 (validator should prevent an invalid handle in `AnnotateHandle`) and 4256 (batch 014,
  validator should run `ComputeViewIdState`).** Both say the validator fails to check something a
  malicious or buggy producer could get wrong. 4256 established the validator never recomputes
  ViewID state and that PR #6859 compares two copies of the same producer-supplied metadata
  rather than recomputing. If 4415 has the same shape, the useful output is a single statement
  about what DXIL validation does and does not independently verify.
- **4350 and 4384** are both ICE-shaped (`const` object method call; integer vector as enum
  type). Probably distinct, but check whether they share a front-end path.

Reminder: a neighbour's **measurements** are inheritable; its **explanations** are hypotheses.

## Hazards this batch is likely to hit

Named as hazards, not predictions. The evidence decides.

- **4486 and 4501 are SPIR-V.** The bisection floor is higher than the usual v1.4.1907, which
  answers `SPIR-V CodeGen not available` — a real `invalid-probe`, already measured on #3768.
  History must be reported as "for as long as it is possible to check".
- **4350, 4384, 4492 are crash- or wrong-code-shaped.** Use `internal_failure`, never a message
  match: batch 014's #3954 found **one defect with four faces** and measured that an
  exit-status-only predicate reports it fixed four and a half years early. Its
  `manual-case-predicate-counterfactual.txt` is the reference.
- **4415 concerns the validator.** A DXIL validation failure exits E_FAIL (0x80004005) and is
  **not** an internal failure. Do not score it as a crash.
- **4351 concerns the rewriter**, which `dxc.exe` cannot reach; see the pairing above.
- **4497 ("struct value on \"stack\"") has a vague title.** Where a repro is prose-only, an
  `agent-constructed` repro that is clearly labelled beats "no repro provided" — but it must be
  labelled.

## Carried forward — the live method lessons

These came out of batch 014 with citations. Verify rather than assume.

1. **Headline claims must live in the `runs` table, or nothing re-verifies them.** #5293's
   regression boundary lives in a bespoke `manual-case-*.txt` and escapes `reindex`/`audit`
   entirely. If an issue's central claim comes from a hand-run measurement, either get it into
   `runs` or say plainly in the report that it is not covered by the automatic re-check.
2. **A clean result from an unproven query is worth nothing.** Three batch-014 workers produced
   false-negative self-checks by reimplementing a rule that already had a canonical
   implementation. Control your verification tooling the way you control a predicate, and prefer
   calling the canonical checker over rewriting its logic.
3. **An inherited flag can fake a floor *and* be inert.** #4036 carried `-HV 2021` from its
   title; the flag demoted four releases to `invalid-probe`, manufacturing a false SM 6.6 floor.
   Proving the flag inert recovered v1.6.2104 — six months *before* the report. Classifying a
   probe as invalid stops it lying to you but still costs you the datapoint; removing a
   non-load-bearing flag is strictly better.
4. **A predicate reads the instrument as well as the behaviour, and instruments change across
   releases.** Batch 013 produced two apparent regressions that were both artefacts of output
   format changes.
5. **`--expect` conflates a control with a hypothesis probe.** A documented refutation is
   currently indistinguishable from a rotted control and is re-reported on every reindex forever.
   Batch 014 recommended a distinct declaration; check whether collation 014 implemented one
   before designing another.

## Your job

`reindex` is not yours. Otherwise the usual: the cross-issue pairings above, the step-10
independent draft review on a **different model** from the workers' `claude-opus-5`,
`reviewed_by` on all ten, and `reports/batch-015.md` with drafts spliced in via
`python scripts/render_comments.py 015`.

Flag prominently any issue whose text no longer matches its behaviour — those are the
highest-value findings. And report what the batch taught us about the method.

## Observations during batch 015 (orchestrator, in flight)

### Workers end their turn before reporting — 3 of 10
4351, 4486 and 4497 each ended a turn mid-sentence ("Now recording the verdict.",
"Now `method-notes.md`, then the checks.", "Now `notes.md`:") with no findings
delivered. The work was largely done; only the report was missing. A single
follow-up asking them to finish and to confirm four explicit completion checks
recovered a full result each time — 4486's follow-up answer was among the
strongest in the batch.

Consequence for the method: **an idle worker is not a finished worker.** The
orchestrator must confirm a substantive report actually arrived and re-prompt
otherwise. Treating an empty turn as "done" would have silently dropped three of
ten issues, with no error raised anywhere.

### A worker wrote outside its boundary
An untracked `repro.hlsl` appeared at the repository root — 4351's repro, written
to the wrong directory, differing from its in-directory copy only in line endings.
Two other workers noticed it and correctly refused to touch it, which is the
boundary rule working as intended, but nobody owned removing it.

The skill requires that triage artifacts never pollute the DXC tree; the boundary
brief says where a worker *may* write, but not that it must write *nowhere else*.
Worth tightening, and worth an orchestrator check for untracked files outside the
skill directory before every commit.

### The pipelining hazard materialised, in the benign direction
Tooling was modified while batch 015's workers were live: `check_paths.py` gained
`--issue`/`--path` scoping plus UTF-16 and NUL-bearing-text handling, `triage.py`
gained `quote_from` and `--hypothesis`, and `test_predicates.py` gained coverage
for both. These close the two defects batch 014 recorded — the latent binary-scan
hole, and the `--expect` conflation of a control with a hypothesis probe.

Both changes are **opt-in and backward-compatible**: absent `quote_from` and absent
`--hypothesis` reproduce the previous behaviour exactly, and the path gate became
strictly stricter rather than looser. That is why no in-flight worker was
invalidated. The rule to carry forward is therefore not "never change tooling
during pipelining" but "changes made under live workers must be additive and
monotonic in strictness". A looser or re-scoring change would have altered verdicts
underneath ten running agents with nothing to signal it.

### The 4036 lesson is a question, not a rule
Batch 014 found an inherited `-HV 2021` was faking a shader-model floor and was
inert, so removing it recovered releases. 4341 measured the same flag and it came
out the **other** way: load-bearing, because v1.6.2112 through v1.7.2212.1 answer
`'operator' is a reserved keyword in HLSL` without it. Dropping it there would have
destroyed four valid probes rather than recovering any.

The transferable instruction is "measure whether the inherited flag is
load-bearing", not "remove inherited flags". 4341 settled it with a per-release
feature-presence control that fails on exactly the four demoted releases and is
clean on the other sixteen.

### Score predicates against the controls, not just the probe
4350's counterfactual over five candidate predicates found one that gets the
release history **exactly right and is still wrong**: a bare "nonzero exit"
predicate matches the reported symptom on all 20 releases, but it also fires on the
syntax-error control, because an ordinary diagnosed error exits with the same
status. Only the control separates a predicate that measures the defect from one
that is accidentally right.

This extends 3954's counterfactual, which compared candidate predicates on the
probe alone.

### Blind re-derivation validated both batch-014 `close-fixed` attributions
Two independent agents, briefed with the release boundary and the repro but
explicitly denied the workers' notes, verdicts and drafts, re-derived both fix
commits from git history alone:

- 3954 → `0372fb792` (PR 6930), reached via `LookupVectorMemberExprForHLSL` and a
  `.r.xx` versus `.r.x` control that matches the changed duplicate-element
  condition. 133-commit window, 16 alternatives screened.
- 4168 → `bf015d2e1` (PR 5197), reached via the annotation-copy hunks and the
  commit's own `lib_6_x` → `vs_6_5` reflection regression test. 257-commit window.

Both matched the original attribution. The 4168 re-derivation also independently
counted **seven commits touching the production files, i.e. six alternatives**,
which corroborates the draft review's factual correction and retires the original
draft's claim that it was "the only commit in the window that touches this path".

Blind re-derivation is cheap — both ran in well under the cost of one issue — and
it is the only check performed so far that tests an attribution rather than
re-reading it. Worth making standard for every `close-fixed` verdict.


### `triaged_by` is self-reported, inconsistent, and sometimes wrong

Tallying `triaged_by` across every recorded verdict gives **22 distinct spellings**
for what is really a handful of models — `claude-opus-5 (Copilot CLI)` (19),
`claude-opus-4.6 (GitHub Copilot CLI)` (10), `GitHub Copilot CLI (claude-opus-4.6)`
(10), `claude-opus-4.6` (9), and a long tail including `claude-sonnet-4-6`,
`GPT-5 (Copilot CLI)` and two variants of "model not self-identifiable".

Some of that spread is real: earlier batches genuinely ran on different models. But
the formatting is pure noise — the same model appears under four different
spellings — and, more seriously, **the values are not reliable**. Batch 015's
workers were all dispatched on `claude-opus-5`; 4341 recorded itself as
`claude-opus-4.5` and 4350 as `GitHub Copilot CLI (Claude Sonnet 4.6)`. Models are
poor witnesses to their own identity, and this field asks each worker to be exactly
that.

This matters because provenance is what a reader uses to calibrate the evidence, and
because the drafts carry an AI-assistance disclosure that implicitly rests on it.

Fix: **the orchestrator knows which model it dispatched — that is the ground truth,
and self-report is not.** `triaged_by` should be set by the orchestrator from the
dispatch record, or stamped automatically by `triage.py`, rather than asked of the
worker. Normalising the existing values is a separate, low-risk cleanup, but it must
not flatten genuine model differences between batches into a single label.

### A worker can finish the investigation and still not record the verdict
4497 produced 55 artifacts — `expected.md` written pre-run, controls, a 21-build
comparative matrix, a corroborated source diagnosis — and then never ran `verdict`,
so `verdict.json` did not exist. Two follow-up prompts returned empty responses.

The recovery was to read its own `notes.md`, which stated every field explicitly
(status, quality, history, confidence, action, labels), and record the verdict from
it. That is safe **only** because the notes are unambiguous and evidence-backed; it
would not be safe to infer a verdict the worker never reached.

Worth an explicit orchestrator check: a worker's directory containing captures but
no `verdict.json` is a specific, detectable failure state, and `audit` already
surfaces it. Run it per issue before declaring a batch complete rather than trusting
the worker's own report — which in this case never arrived at all.

