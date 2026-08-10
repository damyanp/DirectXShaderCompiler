# Batch 012 — orchestrator notes for the collation session

You are collating batch 012. You did not see the dispatch conversation; this file is the only
channel from the orchestrator to you. Everything else you need must come from
`data/issues/<nnnn>/`.

## The batch

| Issue | Opened | Labels at dispatch | Title |
| --- | --- | --- | --- |
| 3044 | 2020-07 | enhancement | Feature request: option to preprocess without removing comments |
| 3066 | 2020-08 | enhancement, dxil | Suggestion: Improved human-readable values in disassembly |
| 3276 | 2020-11 | linux | Install target installs lots of unnecessary LLVM outputs |
| 3414 | 2021-02 | bug | DXIL Modifying recursive payload does not work |
| 3439 | 2021-02 | enhancement, tech-debt | Better demangling for improved error messages |

## Sampling bias — state this in the report

Batches 011 onward are drawn **exclusively from the oldest 100 open issues**, at the user's
explicit request for exhaustive coverage. SKILL.md's guidance to mix ages is therefore
**deliberately suspended** for age.

This batch is **enhancement-heavy** (three `enhancement`, one build-system, one `bug`) and
contains **no `crash` and no `spirv` issue**. Consequences you must state:

- The `internal_failure` predicate and the crash path are **not exercised at all** here. Batch
  011 exercised them thoroughly (see `batch-011.md`); do not re-derive conclusions about them
  from this batch's evidence, and do not report them as "confirmed again".
- Four of five issues are "the compiler does not expose X" requests. That is a real property of
  the 2020–2021 backlog, not a sampling artifact, but it means the batch's headline finding is
  about **option/# surface-area gaps**, and generalises to recent issues even less than usual.

## Ground truth and how to cite it

- Registered compiler `main-debug` self-reports `1.9.0.5433 (triage, ab5400907)`.
- **`ab5400907` is fork-local and resolves nowhere public. It must never appear as a citation.**
- The correct public citation is **`13730886e`**. See `data/reports/provenance-correction.md`.
- Verbatim `--version` or `!llvm.ident` output quoted inside a draft may still show
  `ab5400907` — that is captured evidence, not a citation. #3066 already checked this and
  confirmed its prose cites `13730886e`; verify the same for the other four.

## Your job

1. **`reindex` FIRST, before anything else.** It re-derives every verdict by running today's
   predicate code over archived output, so it retroactively applies this batch's lessons to
   earlier issues. Check all four reports: changed verdicts, stale captures, evidence gaps,
   control-assertion failures. Any output at all is a finding, not noise.

   **This batch you must expect `reindex` to move something**, because finding 1 below changes
   how a whole class of probe is scored. If it reports no change, that is itself a claim
   requiring proof — establish *why* (as batch 011 did, by showing the affected captures
   already matched through another clause) rather than accepting silence.
2. **Cross-issue patterns.** 3044 (`-C`/`-CC` not plumbed to the driver), 3066 (disassembler
   prints raw values), and 3439 (mangled names in diagnostics) are all **"the information
   exists inside the compiler but never reaches the user"**. Check their verdicts and proposed
   actions are mutually consistent, and whether any is a duplicate of an already-triaged issue
   — consult `data/reports/overview.md` for the 55 already done. If they really are one theme,
   say so once in the report rather than three times.
3. **Run the step-10 independent draft review** on a *different* model (previous batches used
   `gpt-5.6-sol`). Apply with judgement, not wholesale. Record the decisions.
4. **Blind re-derivation is MANDATORY for any issue recommended for closure** (`close-fixed`).
5. **Promote method lessons** from each `method-notes.md` into SKILL.md. Workers were forbidden
   from touching shared state, so every tooling fix they found is **unapplied and waiting for
   you**. Applying one mid-batch would invalidate already-finished workers, which is why it
   was deferred.
6. `python scripts/render_comments.py batch-012`, then `python scripts/render_overview.py`.
   **`overview.md` is a standing deliverable and must be regenerated after every batch.**
   The batch label in the DB has been inconsistent historically (`002` vs `batch-002`) — query
   the DB for the exact string before running `render_comments.py`.
7. Write `reports/batch-012.md`.

## Gates before you hand back

- `git status` shows nothing changed outside `.github/skills/dxc-issue-triage/`.
- `python scripts/test_predicates.py` passes.
- `python scripts/triage.py audit` passes.
- `python scripts/check_paths.py` passes. This gate is **new as of batch 011** and replaces the
  hand-run scan; it knows about the 16 deliberate, allowlisted hits. It has been validated in
  both directions (an injected leak in literal and JSON-escaped form fails it).
- No staged binaries. `git add -An` **quotes** the paths it prints, so a regex anchored with
  `$` on the extension silently never matches — this exact mistake gave a false negative once.
- Every issue has a non-empty `reviewed_by` in `verdict.json`, and none self-reviewed.
- No `ab5400907` in any *citation* position.

## Corrections and findings the orchestrator owes you

### 1. The spelling re-probe can silently DESTROY the repro. Fix it before anything else.

This is the most serious defect found in the tooling so far, because it **corrupts ground truth
while reporting success**. It was introduced by batch 011's own fix, so it has been live for
exactly one batch.

`run()`'s spelling re-probe (`triage.py` ~line 1195) retries an `Unknown argument` rejection
with `-`/`_`/`/` variants. On a release where the option has **`Separate` grammar**, the retry
turns a safe command into a destructive one. Measured by the #3044 worker across 21 builds, and
**independently re-derived by the orchestrator from first principles** — the two runs
disagreed, and resolving the disagreement is what pinned the real mechanism:

```
# v1.6.2112, P : Separate (changed by 8bf2b087c / PR 4624, 2022-08-31)
$ dxc -P in.hlsl -Fi out.i     -> dxc failed : Unknown argument: '-Fi'   exit=1   [triggers retry]
$ dxc -P in.hlsl /Fi out.i     -> (no output)                            exit=0   *** in.hlsl OVERWRITTEN ***
                                  in.hlsl now reads: #line 1 "out.i"
```

`-P <file>` consumes the next token as the **output** file, `/Fi` is silently ignored, and
`out.i` becomes the **input**. So the retry writes preprocessed text over the repro.

**The worker reported this as "destructive on 6 releases". That framing is under-specified and
you must not repeat it.** The release count is an artifact of that issue's run order. The
actual precondition is:

> the rejected flag's **value token names a file that already exists**.

With `out.i` absent the same command exits 1 with `The system cannot find the file specified`
and harms nothing; with `out.i` present it clobbers at exit 0. Since all probes for an issue
share one directory, the *first* release that successfully writes `preprocessed.i` arms the
trap for **every subsequent older release** — and every probe after that measures the clobbered
file. Silent, exit 0, and it looks like clean evidence.

What the fix must do (design it yourself, but it must satisfy all of these):

- **Never let a re-probe write to a file that is an input of any command in `cmd.txt`.** That
  is the invariant that actually matters; a fix that only special-cases `-P` will miss the next
  option with `Separate` grammar.
- **Hash the repro inputs before and after every probe** and hard-error on change. Cheap,
  general, and it catches the whole class rather than this instance. A run that modifies its
  own evidence must never be scored.
- Consider running each probe in a scratch copy of the issue directory. #3044's worker had to
  do this by hand (`manual-case-release-history.py`) precisely because the shared directory is
  unsafe; that workaround belongs in the tool.
- Add a regression test to `test_predicates.py` covering both directions: value token present
  (must refuse/clobber-detect) and absent (must behave as before).

`data/issues/3044/cmd.txt` carries a `DO NOT RUN bisect` banner and its release history came
from `manual-case-release-history.txt`. **Once you have fixed the tool, that banner and the
manual harness are a liability** — they will rot. Either re-run 3044 through the fixed tool and
delete the workaround, or leave both and say explicitly in the report why the manual result is
still the citable one.

### 2. The `/` spelling variant is UNFALSIFIABLE on Windows — the acceptance test is broken

Deeper than finding 1, and it survives any fix aimed only at destructiveness. The retry accepts
a candidate unless the candidate *names itself* in an `Unknown argument` diagnostic:

```python
candidate_rejected = unknown_argument_token(candidate_text)
if candidate_rejected and candidate_rejected.lower() == candidate.lower():
    continue          # rejected -- try the next spelling
accepted = (...)      # otherwise: believed to work
```

But SKILL.md already documents that **unrecognised `/`-style flags are silently ignored** —
`/ZZZNONSENSE` exits 0. A `/` candidate therefore *never* produces the diagnostic and is
*always* accepted, whether or not it did anything. The retry converts "flag rejected" into
"flag silently ignored" and scores the probe as valid.

This is the **dangerous direction of error**: it does not miss a bug, it *invents* a working
feature, promoting an `invalid-probe` into a scored probe that measured nothing.

#3044 proved the point with the right instrument — **byte identity, not exit status**: `/C`,
`/CC`, `/ZZZNONSENSE`, and *no flag at all* produce preprocessed output with the **same
SHA-256** on every build. Exit 0 proved nothing; identical bytes proved the flags were inert.

The acceptance test must require **positive evidence that the option was honoured** — a
behavioural difference against the same command without it — not merely the absence of a
complaint. Where no such difference is available, the honest outcome is to keep the
`invalid-probe`, not to accept the spelling. Promote the byte-identity technique into SKILL.md
next to the existing `/ZZZNONSENSE` warning, which currently tells the reader the trap exists
but not how to escape it.

**Two workers hit this same defect from opposite directions, independently.** #3439 found that
on v1.4.1907 the failure was *silent*, so the text-keyed check misread the outcome and **hid a
real reproduction** — its history was 19/20 releases until it stopped trusting the error text,
and 20/20 afterwards. So the text-keyed acceptance test fails in **both** directions:

| direction | mechanism | consequence |
| --- | --- | --- |
| #3044 | no diagnostic because the flag was silently *ignored* | candidate accepted; **invents** a working feature |
| #3439 | no diagnostic because the failure was *silent* | probe misscored; **hides** a real repro |

Convergent evidence from two issues that never shared a process is the strongest signal this
pass has produced about any single piece of tooling. The fix is the same for both, and #3439
states it well: **key on anchor presence/absence in the output you expect, not on error text.**

### 3. `VALUE_FLAGS` is missing `-fi` (orchestrator-verified)

`triage.py:774`. The set lists `-fo`, `-fh`, `-fc`, `-fe`, `-fd`, `-fre`, `-frs`, `-fsh` but
**not `-fi`**, so `-Fi preprocessed.i` leaves `preprocessed.i` looking like a *positional
input*. Consequences: `ce_args` emits a dangling `-Fi`, and `--shader` retargeting rewrites the
wrong token. Add it, and while you are there audit the set against `HLSLOptions.td` rather than
adding one entry and moving on — this is the second value-flag omission to surface.

### 4. Compiler Explorer appends `-Zi -Qembed_debug` to EVERY DXC pane

From #3066, proved via `!dx.source.args`, and `-Qstrip_debug` does **not** counter it. The
worker caught this *after* generating a first link that would have over-stated the issue as
partly fixed — it showed named handles and `; line:N col:M` that a local run does not produce.

This generalises the banner trap already in SKILL.md. That rule currently says CE *embeds the
source*, so a banner naming a token it claims is absent manufactures a hit. The stronger and
more general rule is:

> **CE does not run the command you gave it.** It appends debug flags unconditionally. Any
> claim about the *absence* of debug-derived output — names, line numbers, source text — is
> therefore unsafe to make from a CE pane, and a CE pane can show a capability the shipping
> compiler does not have by default.

Fold this into the existing CE-limits table (which lists Release-only, oldest-is-1.6.2112, and
single-file) as a fourth row. It is the same class of limit and belongs beside them.

### 5. The `grep` tool silently finds NOTHING under `.github/` — orchestrator-discovered

ripgrep skips dot-directories by default, so every `grep` against
`.github/skills/dxc-issue-triage/**` returns "No matches found" **whether or not the pattern is
present**. The orchestrator hit this three times this batch: greps for
`argument_spelling_variants` and for `Unknown argument` in `triage.py` both reported no
matches while `Select-String` found them immediately.

This is a false negative that reads exactly like a true one, and it will have silently
corrupted searches in earlier batches. **Use `Select-String`** (or ripgrep `--hidden`) for
anything under the skill directory, and put this in SKILL.md — every future worker and
collation session runs inside this directory and is exposed to it.

### 6. Prerelease policy (standing, from the user)

> Releases marked `prerelease` are **ignored**, unless a bug is explicitly filed against one.

Already in SKILL.md (~line 1020) and correctly implemented: `bisectable=0` for prereleases is
right, boundaries are expressed in **stable** releases, and the carve-out requires a validated
`release-policy.json` opt-in naming the tag. "Was the current release when the issue was filed"
does **not** qualify. No prior history claim needed reopening. Nothing to do — listed so you do
not "fix" it in the wrong direction.

### 7. #3276 is the first build-system issue in the whole pass

No shader, nothing to compile: it is about what `install` copies. Expect and *accept*
`not-compiler-verifiable`; SKILL.md explicitly calls that a legitimate outcome. Watch for two
failure modes in that worker's output and correct them if present:

- **An invented predicate.** A hollow one that scores something irrelevant is worse than
  declaring none. `unscored` exists for this.
- **A configuration claim not marked as such.** The issue is labelled `linux`; triage runs on
  Windows. Any statement about install behaviour must name the platform it was measured on, and
  if it was not measured, say so rather than reasoning from `CMakeLists.txt` alone.

Its `method-notes.md` is the first evidence about non-compiler issues in this backlog, so
promote its lessons into SKILL.md even if the verdict itself is thin — the *next* build-system
issue is the one that benefits.

### 8. Verify worker claims against artifacts, not prose

Standing instruction, and it paid off twice this batch. Worker summaries have been imprecise
while the on-disk `match.json` / `manual-case-*.txt` were correct:

- #3044's clobbering framing was wrong in the way described in finding 1 — the artifact was
  right, the summary's generalisation was not.
- #3883 (batch 011) summarised an E_FAIL as a crash, which looked self-contradictory until the
  capture showed E_FAIL **plus** a leaked `llvm::cast<>()` marker.

When a worker's number and its artifact disagree, **the artifact wins and the disagreement is
itself a finding** worth a line in the report.

### 9. #3066 shows how to handle a multi-ask issue

It is five separate requests, and a blanket verdict would have been wrong in both directions:
ask **E (resource bindings)** was **already satisfied when the issue was filed**, while asks B
and D are unmet with an open `TODO` still in today's source. The worker answered each ask
separately and found a genuine *regression* on the way (v1.4.1907 printed resource-derived
names with no debug flag; v1.5.2010+ requires `-Zi -Qembed_debug`), reached only by refusing to
trust a `no-repro` bisect result inside an `all_of` predicate.

Two things to carry into SKILL.md: **decompose multi-ask issues before choosing a verdict**,
and **investigate every `no-repro` inside an `all_of` bisect** — the conjunction hides which
clause flipped. The worker's `manual-case-clause-matrix.txt` (all clauses × all captures) is a
good general device; describe it.

Also note its anti-vacuity construction: the predicate's self-test clauses stay matched while
the symptom clauses flip, so a no-match proves *names appeared* rather than *output vanished*.
That is the presence/absence discipline SKILL.md asks for, done well — cite it as the worked
example.

### 10. Commit hygiene and history rewriting — verify, do not re-add

Both landed in SKILL.md from batch 011 (`SKILL.md:17–25`, and the rewrite prohibition). Do
**not** duplicate them. Confirm they are still present and correct, and that batch 012's own
commit message uses **bare numbers only**. Validate the check regex in both directions:
positives (`fixes #3377`, `GH-3429`) must match, negatives (`triage: batch 012 (3044, 3066)`,
a bare SHA) must not.

### 11. #3414 is the batch's only `close-fixed` — orchestrator has already verified it

Because `close-fixed` is the verdict most likely to be acted on unexamined, the orchestrator
independently checked its decisive claims rather than accepting the summary. **All confirmed:**

- **The operand flip, read straight from the archived captures** (not re-run, not paraphrased):
  v1.6.2104 and v1.8.2502 emit `... %struct.Payload* %payload)` — the *same* value as the entry
  parameter `%struct.Payload* noalias %payload`, so the `inout` copy is elided. v1.8.2505 and
  v1.9.2607 emit `... %struct.Payload* nonnull %2`, a distinct temporary with its own GEP.
- **The fix attribution.** `053e7ac65` is real: *"Refactor udt intrinsic arg copy to before
  SROA, flatten RayDesc (#7440)"*, **2025-05-16**, and it adds the cited
  `ScalarReplHLSL/traceray_scalarrepl.ll` (182 lines). That date falls between v1.8.2502
  (2025-02) and v1.8.2505 (2025-05), consistent with the measured boundary.

So measurement, source attribution, test, and date all agree independently. The worker's own
hedge — a 162-commit window means **strong but not certain** attribution — is correct and must
survive into the published draft; do not let the review round it up to certainty.

The worker already ran a blind re-derivation (`gpt-5.6-sol`, withholding `notes.md` and
`comment.md`), which matched status, both transitions, repro quality and action, and caught two
real defects. That is the right construction, but it is **self-administered**. Item 4 still
stands: either run your own, or state explicitly in the report why the worker's is sufficient.
Do not silently skip it.

Note also its honest handling of the standing 2023-07-14 maintainer comment: marked
`text_stale` *factually*, because that comment predates the fix and was accurate when written.
That is the right tone for a stale-text finding on someone else's issue — no implied criticism.

### 12. Endpoint short-circuiting hid a real bug for the SECOND time — strengthen the rule

SKILL.md currently advises `--linear` when the issue history "mentions a fix, a revert, or a
re-opening", and separately advertises that `bisect` checks both endpoints first and
short-circuits when they agree. #3414 shows those two statements combine into a trap.

Its true history is **clean → regressed in v1.6.2104 → fixed in v1.8.2505 → clean**. Both
endpoints (v1.4.1907 and v1.9.2607) are clean, so the short-circuit concludes
`never-repro'd-in-releases` and the entire mid-history window is invisible. Nothing in the
issue text mentions a fix or a revert, so the existing trigger for `--linear` would not have
fired either.

This is the **second independent instance** — #3768 was clean → broken in v1.6.2104/v1.6.2106 →
clean. Two occurrences make it a recurring failure mode, not an anomaly. Restate the rule in
SKILL.md in its stronger form:

> **Both endpoints agreeing is not evidence that the symptom never occurred — it is the
> signature of a possible mid-history window.** For an issue that was filed against a specific
> release, the endpoints are the *least* informative probes available: the reporter's release
> sits in the middle. Treat a `never-repro'd-in-releases` short-circuit on an issue whose
> report date falls inside the release range as a prompt to re-run with `--linear`, not as a
> result.

Consider making `bisect` itself emit that warning when it short-circuits and the issue's
`createdAt` lies within the probed range — the tool knows both facts and the human does not.

### 13. Remaining method findings from #3439 and #3414 to promote

- **IR text is no more portable than message text.** v1.4.1907 emits *named* SSA values, so a
  predicate anchored on `%\d+` false-negatives on the oldest release. SKILL.md warns that
  *diagnostic* text varies across builds; extend that warning to disassembly.
- **No release ships `dxl.exe`** (#3439). A repro needing the linker cannot be bisected from
  release binaries at all; that is a stated limit, not a gap to paper over. It also means a
  `--version` self-check belongs in any per-issue release matrix.
- **Release trees live in two roots** — the `.cache` download area and the repo's
  `build/tools/clang/test/dxc_releases` seed tree. Both #3044 and #3414 had to handle this by
  hand. If the catalog already reconciles them, say so; if not, that is a fix.
- **Per-release controls need a per-issue script**, because releases are not registered
  compilers and `run --shader` only retargets the registered ground truth. #3414's
  `measure-controls.py` and #3044's `manual-case-release-history.py` are two independent
  reinventions of the same missing feature — a strong sign it should exist in `triage.py`.
- **Split the predicate so a control scores the instrument, not the symptom** (#3439). Same
  idea as #3066's self-test clauses; state it once, generally.
- **A cross-compiler *silence* needs a control just as much as a cross-compiler error does**
  (#3439). Clang exits 0 with no diagnostic on that repro; the worker proved the silence was
  real with a second link showing Clang diagnostics do surface in the same pane. SKILL.md
  covers the error direction ("a Clang error is not evidence until you have a control") but
  not the silence direction. Add it — absence of output is the easier one to over-read.
- **Explore old releases before fixing the predicate** (#3414). Tuning a predicate against the
  ground-truth build alone bakes in that build's output shape, and the oldest releases are
  where it differs most.

### 14. #3276 answered finding 7 better than the orchestrator framed it

Finding 7 warned this worker off inventing a predicate and predicted `not-compiler-verifiable`.
It reached that verdict — but it did **not** stop at reading `CMakeLists.txt`, and the way it
got further is the reusable lesson:

> **`not-compiler-verifiable` does not mean "static analysis only". Find the other
> instrument.** CMake's *generated* `cmake_install.cmake` scripts are machine-readable output
> describing exactly what `install` will copy. A **configure-only A/B** — two trees, one
> variable changed, ~2 minutes, no build — converts code-reading into measurement.

That measurement earned its keep by finding something reading had missed, which the orchestrator
has verified in the source: `tools/clang/CMakeLists.txt` closes its
`if (NOT LLVM_INSTALL_TOOLCHAIN_ONLY)` guard and then **immediately re-installs
`include/clang-c` outside it**, so those headers ship even with the toolchain-only switch on.
That is why the A/B showed header trees going 4→1 rather than 4→0. `install-distribution` is
likewise confirmed present (`CMakeLists.txt:807–825`, `LLVM_DISTRIBUTION_COMPONENTS =
"dxc;dxcompiler;dxc-headers"`).

Handle three things carefully when you write this up:

- **The platform caveat must survive.** Everything was measured on Windows against a
  `linux`-labelled issue. The worker's justification for generalising — the install rules carry
  no `if(WIN32)`/`if(UNIX)` guard, so the *finding* transfers even though the exact file list
  does not — is sound, but it must be stated, not assumed.
- **The counts are lower bounds**, because both real install runs aborted on unbuilt artifacts
  and the enumeration came from the rules. Do not let the review turn a lower bound into a
  figure.
- **The `linux` label removal is the batch's most contestable proposal.** It rests on the bloat
  reproducing on Windows. It is defensible and clearly reasoned, but it is exactly the kind of
  removal SKILL.md says needs a reason from the issue itself — keep it flagged as a proposal
  with its evidence attached.

Its integrity device is worth promoting too: with `match.json` and `cmd.txt` deliberately
absent (permitted — `audit_issue`, `triage.py:2083`, does not require them), it carried
integrity in a `RULE-PARSE-SELFTEST` inside the harness, **which caught a real parser bug**. A
harness that parses its own instrument needs a self-test for the same reason a predicate does.

## Standing constraints

- **Read-only on GitHub.** No `gh issue edit|comment|close|reopen|label`, ever. Drafting is in
  scope; posting is not.
- **Never modify DXC source.** Only `.github/skills/dxc-issue-triage/` may change.
- **Do not push.** The orchestrator commits locally; the user has not authorised a push.
- **No history rewriting.** It orphans commits without retracting what they published.
- If you are genuinely stuck, say so and stop. Do not guess a verdict.
