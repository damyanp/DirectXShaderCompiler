# DXC issue triage — batch 004

**Ground truth:** clean `main` **Debug** build, `dxc` 1.9.0.15422, commit `eff900d5`
(`dxcompiler.dll: 1.10(5422-eff900d5)(1.9.0.15422) - 1.9.0.15422 (main, eff900d54)`).
**History:** 20 official release binaries, v1.4.1907 → v1.9.2607.
**FXC comparisons:** real `fxc.exe` from Windows SDK 10.0.26100.
**Nothing was posted, edited, labelled or closed. No DXC source was modified.**

This is the **first batch run under the parallel per-issue session model**: five isolated
workers, one issue each, none aware of the others, plus this collation session briefed only by
what is on disk. The model itself is assessed in [§ What batch 004 taught us](#what-batch-004-taught-us-about-the-method).

## Headline

**All five issues still reproduce. None is closable.** That is the least interesting possible
verdict distribution, and it makes the batch's value entirely a matter of *what else* was
found — which is where it earns its keep.

**#2188 and #2191 are two different defects in the same function.** Filed a day apart in May
2019 by different reporters, they both pass a `static const` value to
`ValidateAttributeIntArg` (`SemaHLSL.cpp`). #2188 passes a *component of a const vector*,
which fails `isCXX11ConstantExpr` and is diagnosed; #2191 passes a *scalar*, which passes the
check and then leaves odr-use bookkeeping behind that trips an assert. Neither worker knew the
other issue existed. They are **not duplicates** and the drafts now say so in both directions —
but anyone fixing one should read the other.

**#2191's history line is a trap that reads as a fix.** All 20 releases compile the repro
cleanly with correct DXIL. That is not evidence of anything: the symptom is an `assert`, and
release binaries are built with `NDEBUG`. `never-repro'd-in-releases` and "fixed" are
indistinguishable in the data and opposite in meaning. `bisect` now warns when they coincide.

**#8737's title understates it and #8527's overstates its scope.** #8737's silent case emits a
DXIL atomic with `i32 undef` where the sample index belongs, and the resulting container
*passes validation* — the defect survives every downstream check DXC has. #8527's title says
"case sensitive"; the mechanism is that `#pragma once` is keyed on the **path as spelled**, so
`"./cs_pragma.hlsli"` vs `"././cs_pragma.hlsli"` fails identically with no case difference at
all.

## Summary

| # | Title | Repro | Status | History | Action | Link |
| --- | --- | --- | --- | --- | --- | --- |
| [#2188](https://github.com/microsoft/DirectXShaderCompiler/issues/2188) | `static const int` as compile-time constant | partial | **repros** | always (v1.4.1907+) | keep open | [nvqTPYffM](https://godbolt.org/z/nvqTPYffM) |
| [#2191](https://github.com/microsoft/DirectXShaderCompiler/issues/2191) | Assert on `static const uint` with `[numthreads]` | complete | **repros** (Debug only) | **never in releases — by construction, not fixed** | keep open | [dGK17oobT](https://godbolt.org/z/dGK17oobT) |
| [#2202](https://github.com/microsoft/DirectXShaderCompiler/issues/2202) | `DXIL intrinsic overload must be valid` | complete | **repros** | always; **v1.8.2403 crashes instead** | keep open | [v7WofnW4f](https://godbolt.org/z/v7WofnW4f) |
| [#8527](https://github.com/microsoft/DirectXShaderCompiler/issues/8527) | `#pragma once` is case sensitive | complete | **repros** | both endpoints (v1.4.1907, v1.9.2607) | keep open | n/a — [see below](#8527--not-about-case) |
| [#8737](https://github.com/microsoft/DirectXShaderCompiler/issues/8737) | Atomics on `RWTexture2DMS` — silent UB or ICE | complete | **repros** | always since v1.7.2207 (SM 6.7) | keep open | [ea91a6vnj](https://godbolt.org/z/ea91a6vnj) |

Confidence is `high` on all five. All five were reviewed by `gpt-5.6-sol`; all five drafts were
written by `claude-opus-5`.

## Per-issue findings

### #2188 — the title names the wrong construct

`static const` is not the problem. A `static const uint` used as an array bound or in
`[numthreads]` compiles fine. What fails is reading a **component of a `const` vector**
(`c2Thread.x`), which `isCXX11ConstantExpr` rejects. Four separately-compiled variants isolate
it, and the behaviour is codified in DXC's own test expectations
(`tools/clang/test/SemaHLSL/const-expr.hlsl`, which carries the comment *"here dxc is
different from fxc… It would be desirable to have this supported"*), so any fix has to update
those.

FXC compiles it and folds the constants. `clang-dxc` rejects it too, with a better message —
so this is a shared gap in the successor front end, not a DXC-only quirk.

Worth flagging for the report's own sake: the draft originally said the dropped `numthreads`
attribute produced "the third error". The capture has **four** error lines, because
`ValidateAttributeIntArg` fails once per component and the `numthreads` diagnostic appears
twice. The independent reviewer caught that; a domain reader would not have counted.

### #2191 — a clean release history that means nothing

The repro asserts on the Debug ground-truth build (`0xE0000001`,
`MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking"` at
`SemaDecl.cpp:11156`) and compiles cleanly on all 20 releases, emitting the *correct*
`!{i32 8, i32 8, i32 1}`. Release binaries compile asserts out. The bisection is silent by
construction.

The worker also found that the assert is not `[numthreads]`-specific — `[maxvertexcount]` on an
empty-bodied GS trips it identically, and 28 attributes route through the same function — and
that **an empty function body is load-bearing**.

**Collation corrected the mechanism.** The draft claimed the workaround was to *reference the
constant* in the body. Comparing against #2188's `variant-scalar-numthreads.hlsl` — a shader
with a body that never mentions the constant, which compiles clean — showed that any statement
suffices. A new control, `variant-body-no-const.hlsl`, was captured to measure this rather than
infer it:

```
$ dxc -T cs_6_0 -E main variant-body-no-const.hlsl   # buf[0] = 1; -- does not mention `eight`
exit=0  ->  no-repro
```

This is the single clearest thing the parallel model produced: **neither worker could have made
this correction, and the collation session could only make it because both sets of artifacts
were on disk.**

### #2202 — one release is worse than the bug

Reproduces from v1.4.1907 to v1.9.2607 — except v1.8.2403, which **access-violates**
(`0xC0000005`) instead of diagnosing, with `-Vd` too. Fixed in v1.8.2403.1 by the revert of
#6302/#6342.

Two independent traps in one issue:

- **Forwards in time.** The 2019 repro has no `-HV`. At today's default `-HV 2021` the front
  end rejects `bool3 ? a : b` (*"for non-scalar types use 'select'"*) before codegen, so the
  validator never runs and the bug looks fixed on `main`. Every previously-known instance of
  this trap ran *backwards* — old compiler, new feature. This is the mirror image, and none of
  the existing markers covered it.
- **A crash scored as a clean run.** The v1.8.2403 access violation matched no symptom
  predicate, so it scored `no-repro` — the one release strictly *worse* than the reported
  symptom, recorded as the absence of a problem.

The substantive finding is that the validator is right and codegen is not: `-Vd` compiles and
emits `call double @dx.op.dot3.f64`, but `Dot3` is declared over `"hf"` only, so `-Vd` produces
DXIL no runtime will accept. The literal-float ternary resolves to `double`, and `dot` is
declared over `numeric` — a type HLSL accepts and DXIL cannot express.

### #8527 — not about case

`#pragma once` is keyed on the path **as spelled**. `DxcArgsFileSystemImpl::TryFindOrOpen`
matches an already-loaded include by `wcscmp` on the spelled name, so a second spelling gets a
second slot in `m_includedFiles`; `GetFileInformationByHandle` then reports that slot's handle
as the file index with a zero volume serial, so `FileManager`'s `UniqueRealFiles[UniqueID]`
deduplication sees two distinct files. Case is just the spelling difference Windows users hit
first: `"./cs_pragma.hlsli"` included as `"././cs_pragma.hlsli"` fails identically.

**No Compiler Explorer link, and the reason is itself a method finding.** The obvious
single-file fold — a header including *itself* under a different spelling — appears to
reproduce. It does not: the worker built it, ran it, and then ran the *same construction with
a matching spelling*, which fails identically. The fold measures clang's rule that
`#pragma once` is ignored in the main file. A transformation adopted to fit a repro into CE
needs its own control, and this is the first time one has failed that check.

Only Windows was measured. The `#ifndef _WIN32` branch of the same class synthesises `st_ino`
from the same handle, so the defect looks platform-independent, and the draft says "looks" —
correctly.

### #8737 — the silent case is worse than the ICE

Two symptoms, both present since v1.7.2207 (the first release with SM 6.7):

- **ICE:** `InterlockedMax(tex.sample[s][uv], …)` fails with
  `llvm::cast<X>() argument of incompatible type!` — an *internal* failure that exits
  **E_FAIL (0x80004005)**, the same status as a syntax error. Also fires with `InterlockedAdd`
  and a constant sample index, and on `RWTexture2DMSArray`.
- **Silent:** the implicit-sample form compiles with **exit 0 and no diagnostic**, emitting
  `atomicBinOp` with `i32 undef` in the coordinate slot — byte-identical to the correct
  encoding for a non-multisampled `RWTexture2D`, because
  `TranslateAtomicBinaryOperation` has no multisample branch.

The reporter's own analysis was correct; what the triage added is that **nothing downstream
catches it**. `DxilValidation.cpp:2412` checks the overload type and that the handle is a UAV,
but not the resource *kind* — so `-Fo` produces a validated container. The defect passes every
automated check DXC has.

## Cross-issue analysis

### Duplicates and relationships

**#2188 ↔ #2191: related, not duplicates. Confident.**

The two were filed one day apart (2019-05-14 and 2019-05-15) in the same language territory,
and this was the batch's designed test of whether isolated workers converge or contradict.
The evidence:

| | #2188 | #2191 |
| --- | --- | --- |
| construct | `static const uint2 c2Thread`, then `c2Thread.x` | `static const uint eight` |
| `isCXX11ConstantExpr` | **fails** | succeeds |
| outcome | diagnosed error, `E_FAIL` | assert, `0xE0000001` |
| function | `ValidateAttributeIntArg` (`SemaHLSL.cpp:13889`) | `ValidateAttributeIntArg` (`SemaHLSL.cpp:13858`) |
| visible in releases | yes, all 20 | no — asserts compiled out |

They share an entry point and nothing else: one fails a check, the other passes it and trips
over the residue. **Fixing either will not fix the other.** Both drafts now carry a
cross-reference stating exactly this.

The workers did not contradict each other, but they *appeared* to. #2188 captured
`variant-scalar-numthreads.hlsl` — which is #2191's construct — and recorded it as compiling
clean, while #2191 recorded the same construct asserting. Both are correct: #2188's variant has
a non-empty body. #2191's own "the empty body is load-bearing" finding is exactly what
reconciles them, and neither worker could see that it did. **Two isolated sessions produced an
apparent contradiction that resolved into a sharper mechanism than either had alone.** That is
the strongest argument for the model in this report.

**No other pair is related.** #2202 (type promotion to `double`), #8527 (include file
identity) and #8737 (multisampled atomics) share no mechanism with each other or with the 2019
pair. No forcing was required.

### Bearing on batches 001–003

Checked all 15 previously-triaged issues. No duplicates. One genuine relationship:

**#8737 ↔ #3009 (batch 002) — same trap class, independently re-navigated.** #3009 is
"uninitialized local silently reaches arithmetic as `i32 undef`, exit 0, no diagnostic". Its
draft warns:

> `undef` alone is not a usable signal. Some DXIL ops carry structurally-undef operands in
> correct code — `loadInput`'s trailing `gsVertexAxis` and `bufferStore`'s unused coordinates
> both appear as `undef` in the output

That is precisely the hazard #8737 had to navigate: is `atomicBinOp`'s `undef` coordinate a
defect or a structural placeholder? #8737's worker, who had never seen #3009, resolved it the
same way — by finding a case where the identical encoding is *correct* (`RWTexture2D`, which
`DXIL.rst` gives two active coordinates) and showing the multisampled case is lowered
identically. Independent re-derivation of a known trap, by the same method, is a useful signal
about how learnable the trap is.

The pair also suggests a **systemic gap in DXC rather than in the method**: in both issues a
module carrying `undef` in a semantically-required operand passes validation and is written to
a container. Two issues, three years apart, different subsystems, same missing check.

### Patterns across the five verdicts

1. **Three of five issues have a title or report that no longer describes the behaviour.**
   #2188 (not `static const`, but const-vector components), #8527 (not case, but spelling),
   #8737 (the ICE is the reported half; the silent half is worse). This is the highest-value
   output of the batch, and it is a triage-quality finding rather than a compiler finding.
2. **Every "surprising" release result was an artefact of measurement, not of the compiler.**
   #2191's 20 clean releases (asserts compiled out), #2202's v1.8.2403 (crashed, not clean),
   #2202's `main` (rejected by a newer default `-HV`), #8527's v1.4.1907 as-filed probe
   (profile predates `cs_6_6`). Four distinct ways to record "no symptom here" when the
   compiler never looked. All four are now classified `invalid-probe`.
3. **Two of five defects survive validation.** #8737's `undef` atomic and #2202's `-Vd` output
   both produce containers a runtime will reject. The validator is not a backstop for
   codegen mistakes of this shape.
4. **Old issues age into *different* bugs.** #2202's repro no longer reaches the reported code
   path at the default language version. An issue filed in 2019 and never touched is not
   guaranteed to still be testable as filed, and "does not reproduce" is the wrong conclusion
   to draw from that.

## Proposed label changes

| # | Now | Add | Remove | Rationale |
| --- | --- | --- | --- | --- |
| #2188 | `bug`, `fxc-disagrees` | `type-system`, `hlsl-next` | — | A change to what HLSL treats as a constant expression; `fxc-disagrees` re-confirmed by running FXC |
| #2191 | `bug` | `crash` | — | It is an assert; `bug` alone loses it in crash searches |
| #2202 | `bug` | `type-system`, `fxc-disagrees`, `diagnostic` | — | HLSL type DXIL cannot lower; FXC compiles in float; surfaces as a post-codegen validation error. **Deliberately not `validation`** — the validator is correct here and the label would misroute it |
| #8527 | `bug`, `needs-triage` | `usability`, `check-in-clang` | `needs-triage` | Rules out `#pragma once` across a codebase; the defective lookup is DXC's own filesystem emulation, so Clang likely does not share it |
| #8737 | `bug`, `needs-triage` | `crash`, `incorrect-code`, `diagnostic`, `sm6.7` | `needs-triage` | Internal failure plus silent wrong code; correct behaviour is a diagnostic, so **not** `correctness` |

## What batch 004 taught us about the method

### 1. The parallel per-issue session model — assessment

**What it caught that a single session would not have.**

- The **#2188/#2191 reconciliation**. A single session triaging both would very likely have
  read them as one issue, seen the scalar case compile, and concluded #2191 was stale. The
  isolation produced two independent measurements of the same construct with opposite results,
  and the contradiction is what forced the correct mechanism out.
- **Five independent method reports.** Convergence across isolated observers is evidence in a
  way that one observer repeating itself is not. All five workers independently reported that
  `reindex` is destructive; three independently hit the predicate-filename collision. Neither
  could have been weighted that way from a single session.
- **Sustained scrutiny on issue five.** `SKILL.md` predicts that "after four issues that still
  reproduce, the fifth gets less scrutiny". Nothing in the artifacts suggests any of the five
  received less attention than another; #8737, alphabetically and numerically last, has the
  deepest `notes.md` in the batch.

**What it cost.**

- **Redundant work.** Five workers each re-derived the same tooling defects and each wrote them
  up at length. The five `method-notes.md` files total ~78 KB, most of it overlapping. That
  redundancy is what produced the convergence signal, so it is not pure waste — but it is paid
  every batch, and it will not keep paying.
- **A much heavier collation session.** Collation had to read five sets of artifacts cold,
  adjudicate overlapping and occasionally contradictory method claims, and do all cross-issue
  work from scratch. This session, not the workers, is now the bottleneck.

**What it broke.** Three incidents, all shared-state:

- **`reindex` as a shared-state write.** `SKILL.md` told workers to run it; its `--reset` flag
  was declared `action="store_true", default=True`, so a bare `reindex` *always* took the
  destructive path (`DELETE FROM issues; DELETE FROM runs;`). All five workers ran it — 4, 2,
  4, 3 and 2 times respectively. **#2191 arrived at collation with a NULL title, url,
  created_at and `batch`**, and since `render_comments.py` selects on `batch`, it would have
  been silently omitted from this report. Detected only because collation checked; nothing
  warned.
- **The predicate/filename collision.** `execute()` derived the output path from
  compiler + label only, so a second `--match` overwrote the first predicate's entire release
  history. #2191 is the live casualty: 20 of its 21 `out-*.txt` carry
  `# match: match-rejected.json`. #2188 declined to run a second predicate *because of* this;
  #2202 worked around it with labels. Three of five workers hit one edge in one batch.
- **An orchestration incident the model caused rather than prevented.** Per the orchestrator
  notes, a `write_agent scope=children` broadcast reached a worker outside the batch and
  triggered an unrequested re-triage of **#3768** (batch 002). The failure mode is specific to
  fan-out orchestration: a message intended for a group is delivered to a wider group than
  intended, and the recipient has no way to know it was not meant for it. Address messages to
  explicit agent IDs, not to a scope.

  **Postscript — the unrequested work was mostly right, and was adopted.** Reviewed after
  collation: the committed #3768 hit-rates (`27/40`, `33/40`) existed only as prose in
  `comment.md`, with no capture behind them, and `notes.md` said 110 clean runs where
  `verdict.json` said 105. The re-triage's figures (`33/40` at v1.6.2104, `28/40` at
  v1.6.2106) are backed by a 425 KB capture of every attempt, recounted independently from
  raw exit codes before adoption. Five of its six file changes were taken, along with the
  capture and the upstream-fix metadata; the `match.json` note was **rejected** for dropping
  the "E_FAIL alone is not an internal failure" caveat and narrowing the documented signature
  to `0xC0000374`, against the signature-independence rule. `kind` was never modified, so no
  score changed. The durable lesson is in `SKILL.md` step 5: a quoted rate must be countable
  from a file in the issue directory.

**Verdict on the model: keep it, with the tooling fixed.** The #2188/#2191 result alone
justifies it, and it is not reproducible by a single session at any effort level. But note what
made the batch expensive: three of the four defects it exposed were *caused* by parallelism
rather than revealed by it. The next parallel batch should be much cheaper. If it is not, that
is the signal to revisit.

### 2. `reindex` is collation's command; workers get `audit` (new)

Converged independently by all five workers and the orchestrator — the strongest convergence in
the batch, and the only defect every observer found. The fix is not a warning:

- **`triage.py audit [--issue N]`** is new. It runs the same completeness check, reads no
  tables and writes none, so it is safe under any amount of concurrency. `audit_issue()` now
  takes `collated`, so a worker is no longer told it is missing `reviewed_by` — a step
  `SKILL.md`'s own phase table assigns to collation. **Previously a correctly-executed worker
  could not get a clean run**, which taught workers to ignore the audit's output.
- **`reindex` no longer discards database-only columns.** It snapshots `issues` before the
  reset and restores any column the rebuild leaves NULL, printing what it kept so the operator
  knows to mirror it into `verdict.json`.
- **`--reset` no longer lies.** It was a flag that could not be turned off by its own name; it
  is now `argparse.SUPPRESS`ed, with `--no-reset` as the real control.
- `SKILL.md` and `README.md` now say plainly which command belongs to which phase.

### 3. A probe is identified by its predicate, not just by its compiler (new)

Three workers hit this; one lost 20 captures to it. Two fixes:

- `probe_path()` files a non-default predicate's probes as `out-<compiler>--<predicate>.txt`.
  `match.json` keeps the bare name, so nothing already committed moves.
- `execute()` now **refuses** to overwrite a capture whose recorded `# match:` differs from the
  current run's, before running the compiler, pointing at `--label` or `--force`.

The general lesson is in `SKILL.md` step 4: two predicates over one release are two
measurements, and a tool that cannot represent that will silently discard one.

### 4. A crashed probe measured nothing (new)

#2202's v1.8.2403 access violation scored `no-repro`. `classify()` now returns `invalid-probe`
for any `no-repro` that was an internal failure — the guard cannot fire when the crash *is* the
symptom, because an `internal_failure` predicate scores that probe `repro`.

This is the fourth distinct way a probe can measure nothing (after: profile too old, feature
too new, absence-predicate satisfied by a failed parse). All four now classify the same way.

### 5. The feature-absence trap runs forwards in time too (new)

Every marker in the `unsupported` set means "you used something that does not exist yet".
#2202 is the mirror image: a **newer** compiler rejecting an **older** repro because the
default language version moved. `for non-scalar types use 'select'` is now in the set, and
`SKILL.md` step 6 says to pin `-HV` on any repro older than the current default.

Worth stating as a general principle: *"reproduces on every old release but not on `main`"* is
the exact signature of both a genuine fix and this trap, and they are told apart only by
reading the `main` output.

### 6. `never-repro'd-in-releases` is only a finding if a release could show the symptom (new)

#2191's 20 clean releases are a property of `NDEBUG`, not of the code. `bisect` now warns when
`never-repro'd-in-releases` coincides with a ground-truth probe that failed with an assert-only
status (`0x80000003`, `0xE0000001`). The verdict text has to say "silent by construction", and
this must never become a `close-fixed`.

### 7. `invalid-probe` did not violate `--expect no-match` (new)

`expectation_violated` was `(verdict == "repro") != (expect == "match")`, so an `invalid-probe`
silently satisfied `no-match`. #8527's as-filed control — rejected by v1.4.1907 because
`cs_6_6` did not exist — passed a check designed to catch exactly that. `invalid-probe` is now
a third declarable value and violates both `match` and `no-match`.

Four stale declarations were corrected as a result (three in #2202, one in #8527), which
exposed the next gap.

### 8. A reported disagreement you cannot close is a disagreement that hides the next one (new)

`reindex` re-scores every probe and reports where the archived verdict and the re-derived one
differ — the mechanism that caught items 4, 5 and 7 above. But it offered **no way to accept a
correction**, so improving a predicate meant choosing between a permanently noisy audit and
hand-editing captures. Both are how a mechanical check stops being read.

Two commands close the loop, and neither can touch a measurement:

- **`reindex --accept`** restamps `# verdict:` headers to today's scoring. The verdict is
  derived from the captured text, so nothing is lost.
- **`triage.py expect --issue N --capture F --expect V`** revises a control's declared
  expectation and **refuses if the new declaration would itself be false**:

  ```
  $ python scripts\triage.py expect --issue 2202 --capture variant-hv2021-main-debug.txt --expect match
  refusing: variant-hv2021-main-debug.txt scores 'invalid-probe', so declaring 'match' would
  be false on the next reindex
  ```

`# cmd:`, `# exit:` and the captured output are observations. Editing them is falsification,
and `README.md` now says so.

### 9. `--repeat`'s evidence did not survive a rebuild (new, latent)

A `--repeat` aggregate wrote a `runs` row with `cmd = '(see single runs)'` and no backing file.
`reindex` rebuilds `runs` from `out-*.txt` only, so **the hit rate — which for a
nondeterministic bug *is* the evidence — was destroyed by any rebuild.** Not triggered in this
batch; found by reading the code while fixing item 2. `stamp_repeat()` now writes `# attempts:`
and `# hits:` into the surviving capture's header, and `reindex` carries them into the run note.

Worth recording that batch 003's #3768 result (a two-release window found with
`--linear --repeat 10`) was already stored this way. The number in that report was correct when
written and could not have been re-derived afterwards.

### 10. The independent review's best output was arithmetic, not concision

The reviewer (`gpt-5.6-sol`, on drafts by `claude-opus-5`) produced ~35 suggestions. The three
worth the exercise were all **counting errors**, not style:

| draft | claim | reality |
| --- | --- | --- |
| #2188 | "the third error" | the capture has **four** error lines |
| #8527 | "every release back to v1.4.1907" | `bisect` short-circuited; **two** releases probed |
| #8737 | "with other atomics" | exactly **one** other atomic (`InterlockedAdd`) was tried |

A reviewer reading for words to cut checks every quantifier; a domain reader skims them. This
is now in `SKILL.md` step 10, together with the instruction to **give the reviewer the evidence
files, not just the drafts** — it cannot check a count it cannot see.

Accepted, in addition to the three above: trimming #2188's label rationale, compressing
#8737's rhetoric ("One thing not in the report:", "your analysis"), and #2202's opening-line
qualifier. Rejected: several cuts that would have removed actionable caveats (#8527's
Windows-only measurement, #8527's rejected-CE-fold explanation, #2202's `-HV 2018` instruction),
consistent with the failure mode `SKILL.md` already documents.

**What the reviewer structurally could not do:** notice that #2188 and #2191 are related.
Nothing in either draft said so. Cross-issue claims have to be settled by collation *before*
the review, not after — which is a new ordering constraint the parallel model creates.

### 11. Convergence across isolated observers is itself data (new)

Five workers, no shared context, each writing method notes independently:

| defect | reported by |
| --- | --- |
| `reindex` is destructive shared state | **all five** + orchestrator |
| predicate/filename collision | #2188, #2191, #2202 + orchestrator |
| `audit` demands `reviewed_by` a worker cannot supply | #2188, #2191, #2202, #8737 |
| `verdict` should record `dxc --version` | #2202, #8737 |

Under a single session none of these would carry more weight than one observation. The count is
only meaningful *because* the observers could not see each other, and it is what determined
which fixes were worth writing. Recorded here because it does not survive in the artifacts:
after this report, the `method-notes.md` files read as five copies of one complaint.

### Method claims rejected

Three claims were verified against the source and deliberately **not** acted on:

- **"A positive predicate cannot self-detect an invalid probe" (#2188).** True as description,
  but the proposed rule — `verdict == "repro" and unsupported → invalid-probe` — is unsafe.
  #1627's reported symptom *is* an `unrecognized argument` diagnostic, so the rule would
  destroy that verdict. (#2188's own diagnostic, "variable length arrays **are** not
  supported", escapes the regex only by a hair.)
- **"Grep `notes.md` for claims not found in any capture" (#2188, #2202, #8737).** High
  false-positive rate on legitimate paraphrase and on quotes from issue text; #2202's own note
  called it crude. The `--expect` mechanism already covers the case that matters.
- **"Refuse a Compiler Explorer link for multi-file repros" (#8527).** Contradicts `SKILL.md`,
  which explicitly permits a partial multi-file link with the limitation stated. #8527's
  decision to skip was correct on its own facts; the general rule is not.

One claim was **deferred**: recording `dxc --version` in `verdict.json` (#2202, #8737). It is a
good idea and `compiler` already stores the string, but it cannot be honestly backfilled for
batches 001–003, and a field populated for one batch and NULL for three is worse than no field.
Worth adding at the start of a batch, not the end of one.

## Proposed issue comments

These are **drafts for review, not posted**. No comment, label or state change
has been made on any issue. Each is written to be postable as-is by a maintainer, and every
claim in them is backed by captured evidence in `issues/<nnnn>/`.

They deliberately avoid promising fixes or timelines, and where the next step is a product or
language decision they say so rather than pre-empting it. Quoted compiler output was
re-verified before being written down.

Each draft ends with a trailer disclosing that it came from an assisted triage pass.

Source of each is `issues/<nnnn>/comment.md` — edit there, then re-run
`scripts/render_comments.py <batch>` to refresh this section.


### Draft — [#2188](https://github.com/microsoft/DirectXShaderCompiler/issues/2188) fxc.exe vs dxc.exe:  "static const int" use as compile time constant

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2188](https://github.com/microsoft/DirectXShaderCompiler/issues/2188).

Still reproduces on `main` (1.9.0.15422, `eff900d54`), and in every release from
**v1.4.1907** (2019-07) to **v1.9.2607** — 20 releases, linear scan, no transition.

```
repro.hlsl:10:27: error: variable length arrays are not supported in HLSL
groupshared float4      S1[cThread];
repro.hlsl:12:2: error: 'numthreads' attribute requires an integer constant
[numthreads(c2Thread.x, c2Thread.y, 1)]
```

Compiler Explorer, FXC beside DXC and clang: **https://godbolt.org/z/nvqTPYffM**
FXC compiles it and folds the constants (`dcl_thread_group 8, 8, 1`); the same is true of
a local FXC 10.1 from the Windows SDK.

**The trigger is narrower than the title suggests.** `static const` is not the problem —
reading a *component of a const vector* is. Each of these was compiled separately:

| construct | DXC |
| --- | --- |
| `static const uint cThread = 64; groupshared float4 S1[cThread];` | compiles |
| `static const uint eight = 8; [numthreads(eight, 8, 1)]` | compiles |
| `static const uint2 c2Thread = {8,8}; groupshared float4 S1[c2Thread.x*c2Thread.y];` | error |
| `[numthreads(c2Thread.x, c2Thread.y, 1)]` | error |

So both halves of the report are one defect: a component read of a `const` vector is not
a constant expression. The `uint2(8,8)` constructor is not involved (brace-init fails the
same way), and `-HV 2021` makes no difference.

Not the same as #2191, despite the shared function: there a `static const` **scalar**
passes the constant-expression check and the failure is an assert in later bookkeeping.
Here the check itself fails, on every release. Related, but separate fixes.

This is codified in DXC's own tests — `tools/clang/test/SemaHLSL/const-expr.hlsl`:

```
// Note: here dxc is different from fxc, where a const integral vector can be used in ICE.
// It would be desirable to have this supported.
float arr_vc_One[vc_One.x];  /* expected-error {{variable length arrays are not supported
                                in HLSL}} fxc-pass {{}} */
```

with the same pattern for attributes at `attributes.hlsl:659`
(`[maxvertexcount (sc_count4.w)]`). Any fix has to update those expectations.

Mechanically: `ValidateAttributeIntArg` (`SemaHLSL.cpp:13889`) tests `isCXX11ConstantExpr`
and returns `0` when it fails — once per component, which is why the `numthreads` error
appears twice. `numthreads` then computes a group size of 0, warns
`Group size of 0 (0 * 0 * 1) is outside of valid range`, and drops the attribute, which
produces a fourth error, `compute entry point must have a valid numthreads attribute`.
The array bound reaches `err_hlsl_vla` (`SemaType.cpp:2144`) for the same reason.

Two things that have changed since 2019:

- That warning and the fourth error first appear in **v1.8.2403** (2024-03); v1.7.2308
  (2023-08) and earlier print only the three errors. The rejection itself is unchanged.
- `clang-dxc` **rejects it too**, with a clearer explanation
  (`note: initializer of 'cThread' is not a constant expression`). The inlined-constant
  version compiles there, so this is the same gap rather than an unrelated front-end
  limitation. Whatever is decided here likely needs deciding for both compilers.

The `#define` workaround from @tristanlabelle's 2019 comment still applies.

Suggested labels: add **`type-system`** and **`hlsl-next`** — this is a change to what HLSL
treats as a constant expression. No removals; `fxc-disagrees` is confirmed by running FXC.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#2191](https://github.com/microsoft/DirectXShaderCompiler/issues/2191) Assert when a static const uint is used with [numthreads]

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2191](https://github.com/microsoft/DirectXShaderCompiler/issues/2191).

**Still reproduces** on `main` (`1.9.0.15422 (main, eff900d54)`), Debug build, with the repro
exactly as filed:

```
$ dxc -T cs_6_0 -E main repro.hlsl
Internal compiler error: LLVM Assert          # exit 0xE0000001
```

The message only reaches `OutputDebugString`, so under a debugger:

```
assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")
tools\clang\lib\Sema\SemaDecl.cpp(11156)   in clang::Sema::ActOnFinishFunctionBody
```

Three things the original report does not say:

**It is not specific to `[numthreads]`.** `[maxvertexcount]` on an empty-bodied geometry
shader trips the same assert:

```hlsl
static const uint three = 3;
struct GSOut { float4 pos : SV_Position; };
[maxvertexcount(three)]
void main(inout TriangleStream<GSOut> s) {}     // -T gs_6_0 -E main -> same assert
```

Both go through `ValidateAttributeIntArg` (`SemaHLSL.cpp:13858`), which resolves an
identifier argument by looking up the `VarDecl` and folding its initialiser; 28 attributes
route through it in total.

**The empty body is load-bearing.** Any statement in the body suppresses the assert — the
body does not have to mention the constant, so this is not about the constant being
odr-used:

```hlsl
static const uint eight = 8;
RWBuffer<uint> buf;
[numthreads(eight, 8, 1)]
void main() { buf[0] = 1; }                     // compiles clean
```

(`variant-body-no-const.hlsl`; `variant-odr-used.hlsl`, which does reference `eight`, is
also clean.) That points at the full-expression cleanup rather than the attribute: an
empty body reaches `ActOnFinishFunctionBody` with nothing having drained the entries
`ValidateAttributeIntArg` left in `MaybeODRUseExprs`. Adding a statement is a workaround,
but not a targeted one.

**No shipped compiler is affected.** All 20 releases from v1.4.1907 (2019-07) to v1.9.2607
compile the repro successfully, with the right thread-group size in the DXIL
(`!{i32 8, i32 8, i32 1}`; from v1.7.2207 also `; NumThreads=(8,8,1)`), because release builds
have asserts compiled out (`assert.h`: `#ifdef NDEBUG` → `((void)0)`) and the leftover
bookkeeping is harmless to codegen. So the bisection is silent here by construction, not
because anything was fixed — the assert path and `ValidateAttributeIntArg`'s identifier
branch are unchanged since the first public commit in 2016.

[Compiler Explorer](https://godbolt.org/z/dGK17oobT) shows the Release side: `dxc_1_6_2112`
and `dxc_trunk` both succeed, and so does `hlsl_clang_assertions_trunk` — an assertions build
of the successor HLSL front end — emitting metadata identical to a literal `[numthreads(8,8,1)]`
control. CE carries no assertions-enabled DXC, so it cannot show this issue's symptom.

Two side notes on the linked threads: the rejection reported in #4032 ("compiler emits error
message and rejects input") does not reproduce on any release for this construct — DXC has
accepted a `static const uint` here for as long as is checkable. **#2188 is a different
defect in the same function**: it passes a *component of a const vector* (`c2Thread.x`),
which fails `isCXX11ConstantExpr` outright and is diagnosed; the scalar case here passes
that check and then leaves the odr-use bookkeeping behind. Fixing one will not fix the
other.

Suggested label: add **`crash`** — the issue is currently only `bug`, and this is an assert.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#2202](https://github.com/microsoft/DirectXShaderCompiler/issues/2202) Validation error "DXIL intrinsic overload must be valid"

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2202](https://github.com/microsoft/DirectXShaderCompiler/issues/2202).

Still reproduces on `main` (`1.9.0.15422 (main, eff900d54)`), and on every release from
v1.4.1907 to v1.9.2607 that diagnoses it at all — v1.8.2403 crashes instead, see below.

**Compiler Explorer:** https://godbolt.org/z/v7WofnW4f

One caveat on repro'ing it today: the attached shader must be compiled with `-HV 2018`. At
the current default (`-HV 2021`) the front end rejects it first, for an unrelated reason —
`error: condition for short-circuiting ternary operator must be scalar, for non-scalar types
use 'select'` — so the validator never runs and the bug looks fixed.

Saving the attachment as `repro.hlsl`:

```
$ dxc -T ps_6_0 -E ps_main -HV 2018 repro.hlsl
error: validation errors
repro.hlsl:11:13: error: DXIL intrinsic overload must be valid.
note: at '%13 = call double @dx.op.dot3.f64(i32 55, double %10, double %11, double %12,
      double 1.000000e+00, double 1.000000e+00, double 1.000000e+00)' in block '#0' of
      function 'ps_main'.
```

### The validator is right; codegen is not

Worth separating, since they have different owners. With `-Vd` the compile **succeeds** and
emits:

```llvm
%10 = select i1 %7, double 1.500000e+02, double 1.000000e+02
%13 = call double @dx.op.dot3.f64(i32 55, double %10, double %11, double %12, ...)
```

`Dot3` is declared with overloads `"hf"` — half and float ([`hctdb.py`][1]) — so there is no
`f64` `Dot3` and `Instr.Oload` is correct to reject it. `-Vd` does not work around this; it
just emits DXIL no runtime will accept. @tristanlabelle's 2019 diagnosis holds: the
literal-float ternary resolves to `double`, and `dot` is declared over `numeric`
([`gen_intrin_main.txt`][2]), which includes `double` — a type HLSL accepts and DXIL cannot
express.

FXC compiles the same source in float —
`dp3 o0.xyz, r0.xyzx, l(1.000000, 1.000000, 1.000000, 0.000000)` — as the fourth pane in the
link shows.

### Two things that have changed since 2019

**The error message now has a source location** — that half of the original ask is done:

| | |
| --- | --- |
| v1.4.1907 | `at 0x1e216e8f720 inside block #0 of function ps_main DXIL intrinsic overload must be valid` |
| v1.5.2010 | `Function: ps_main: error: … Use /Zi for source location.` |
| v1.6.2104 → `main` | `repro.hlsl:11:13: error: DXIL intrinsic overload must be valid.` |

**v1.8.2403 crashes on this input** rather than diagnosing it —
`Internal compiler error: access violation. Attempted to read from address 0x00000000000000B0`
(`0xC0000005`), with `-Vd` too. It is the only release that does; fixed in v1.8.2403.1 by the
revert of #6302/#6342, and superseded on `main` by #6543. Worth noting because a linear
release scan scores that release as "clean".

### Related

- **#8208** (open) reaches the same `DXIL intrinsic overload must be valid` through
  `mul` on two `double4`s → `call double @dx.op.dot4.f64`. Same gap, one layer down, without
  any literal-float promotion — probably worth looking at together.
- **#2432** was closed as fixed in HLSL 202x, and `-HV 202x` does compile this repro clean.
  That does not close this one: the promotion still happens in the default language mode, and
  `-HV 2021` only avoids it here because of the unrelated `?:` restriction above.
- PR **#2636** (`Fixes #2432`, "Fix bug in implicit cast involving literal float expressions")
  was closed unmerged in 2023.

### Labels

Suggest adding **`type-system`** (an HLSL type resolves to something DXIL cannot lower),
**`fxc-disagrees`** (measured, above) and **`diagnostic`** (the failure surfaces as a
post-codegen validation error naming a DXIL instruction, not the expression). Deliberately
**not** suggesting `validation`: the validator is behaving correctly here, and the label would
route this to the wrong place. Keeping `bug`. I may be missing history behind the current
labels.

[1]: https://github.com/microsoft/DirectXShaderCompiler/blob/main/utils/hct/hctdb.py
[2]: https://github.com/microsoft/DirectXShaderCompiler/blob/main/utils/hct/gen_intrin_main.txt

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#8527](https://github.com/microsoft/DirectXShaderCompiler/issues/8527) pragma once is case sensitive

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8527](https://github.com/microsoft/DirectXShaderCompiler/issues/8527).

Confirmed. Still reproduces on `main` (1.9.0.15422, `eff900d54`), Windows/NTFS. Both ends of
the release range reproduce it too — v1.4.1907 (the oldest release with a usable `dxc`) and
v1.9.2607 — so it has been there the whole time rather than regressing.

As reported (`dxc -T cs_6_0 -E main repro.hlsl`, exit `0x80004005`):

```
In file included from repro.hlsl:6:
In file included from ./includeB.hlsli:3:
./cs_Pragma.hlsli:3:8: error: redefinition of 'Foo'
struct Foo
       ^
./cs_pragma.hlsli:3:8: note: previous definition is here
```

**But the title understates it: this is not about letter case.** Keeping the case
identical and spelling the second include `"./cs_pragma.hlsli"` fails the same way:

```
In file included from dotslash.hlsl:5:
In file included from ./includeB-dotslash.hlsli:3:
././cs_pragma.hlsli:3:8: error: redefinition of 'Foo'
struct Foo
       ^
./cs_pragma.hlsli:3:8: note: previous definition is here
```

`#pragma once` is keyed on the **path as spelled**, not on file identity. Case is just the
spelling difference Windows users hit first. `-P` shows the body emitted twice, once under
`#line 1 "./cs_pragma.hlsli"` and once under `#line 1 "./cs_Pragma.hlsli"`.

Where it comes from: `DxcArgsFileSystemImpl::TryFindOrOpen` matches an already-loaded
include by `wcscmp` on the spelled name, so a second spelling gets a second slot in
`m_includedFiles`; `GetFileInformationByHandle` then reports that slot's handle as the
file index with a zero volume serial, so `FileManager`'s `UniqueRealFiles[UniqueID]`
deduplication sees two different files and `#pragma once` is recorded against only one of
them. (`tools/clang/tools/dxcompiler/dxcfilesystem.cpp:256`, `:287`, `:468`;
`tools/clang/lib/Basic/FileManager.cpp:275`.) The `#ifndef _WIN32` branch of the same
class synthesises `st_ino` from the same handle, so this looks platform-independent —
though only Windows was measured here.

Controls: the identical repro with matching case compiles clean (exit 0, DXIL emitted), so
the failure is the spelling and nothing else. A classic `#ifndef`/`#define` include guard
also compiles clean with the case mismatch left in, which is the workaround until this is
fixed.

No Compiler Explorer link: the repro needs a header plus two includers and CE is
single-file. Folding it into one file that includes itself under a different spelling
*looks* like it works, but the same construction with a matching spelling fails
identically — both print `warning: #pragma once in main file` first, so that device
measures clang's rule that `#pragma once` is ignored in the main file, not this bug.

Suggested labels: keep `bug`, add `usability` (as reported, this rules out `#pragma once`
across a codebase) and `check-in-clang` (the defective lookup is DXC's own file-system
emulation, so the Clang HLSL front end likely does not share it — worth confirming);
remove `needs-triage`. Whether case folding, path normalisation or real file identity is
the right fix is a product decision — normalising the key would change which spelling
appears in diagnostics and dependency output.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#8737](https://github.com/microsoft/DirectXShaderCompiler/issues/8737) Atomics on RWTexture2DMS result in silent UB or ICE

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8737](https://github.com/microsoft/DirectXShaderCompiler/issues/8737).

Both symptoms reproduce on `main` (`1.9.0.15422 (main, eff900d54)`), and both have been present
since **v1.7.2207** — the first release with SM 6.7. Not a regression: no release that can
compile the repro has ever behaved differently. Compiler Explorer, including your 1.10.2605.24:
<https://godbolt.org/z/ea91a6vnj>

**ICE.** `InterlockedMax(tex.sample[s][uv], …)` exits `0x80004005` with

```
error: llvm::cast<X>() argument of incompatible type!
```

This is an internal failure, not a diagnosed error — `llvm::llvm_cast_assert_internal` throws
`hlsl::Exception(DXC_E_LLVM_CAST_ERROR, …)` (`lib/Support/ErrorHandling.cpp:143`), so it is
identical in Debug and Release. It also fires with `InterlockedAdd` and a constant sample index,
and on `RWTexture2DMSArray`. A `tex.sample[s][uv] = v` **store** compiles clean, so the double
subscript itself is fine; only an atomic through it fails.

**Silent case — the analysis in the report checks out, and the DXIL shows it.** The
implicit-sample form compiles with exit 0 and no diagnostic at all, not even a warning:

```llvm
; tex                                   UAV     u32        2dMS      U0             u0     1
%6 = call i32 @dx.op.atomicBinOp.i32(i32 78, %5, i32 7, i32 %3, i32 %4, i32 undef, i32 -559038737)
                                                                       ^^^^^^^^^^
call void @dx.op.textureStoreSample.i32(i32 225, %7, i32 %3, i32 %4, i32 undef, …, i8 15, i32 0)
call void @dx.op.textureStoreSample.i32(i32 225, %8, i32 %3, i32 %4, i32 undef, …, i8 15, i32 %2)
```

The stores carry a `sampleIdx` operand; the atomic has none and its last coordinate is `undef` —
not a defaulted 0. The same `InterlockedMax` on a non-multisampled `RWTexture2D` emits a
byte-identical instruction, which is correct there: `docs/DXIL.rst:1876-1887` gives `RWTexture2D`
two active coordinates. **DXC lowers the multisampled and non-multisampled cases identically.**
`TranslateAtomicBinaryOperation` (`lib/HLSL/HLOperationLower.cpp:4906`) initialises all three
coordinates to `undef` and fills only as many as the address vector has, with no multisample
branch, so there is no path that could supply a sample index.

`RWTexture2DMSArray` is worse rather than equivalent: the address is a `uint3`, so all three
coordinate slots hold x/y/slice and there is no free operand at all.

**This is invalid input DXC fails to diagnose, not valid input DXC miscompiles.**
`docs/DXIL.rst:1876-1887` does not list `Texture2DMS` or `Texture2DMSArray` among `AtomicBinOp`'s
valid resource types, and `RWTexture2DMSMethods` (`utils/hct/gen_intrin_main.txt:927`) declares
no interlocked method — both forms reach the free `InterlockedMax(ref …)` overload, so Sema never
sees the resource kind. The Desired Outcome in the report is the right shape of fix; no codegen
change can substitute for it while `atomicBinOp` has no sample-index variant.

Nothing downstream catches it either. The validator's `AtomicBinOp` case
(`lib/DxilValidation/DxilValidation.cpp:2412`) checks the overload type and that the handle
is a UAV, but not the resource *kind*, so `-Fo` on the implicit form produces a validated
container. A validation rule may be worth considering alongside the front-end diagnostic.

Label suggestion: add `crash` (an internal failure — `bug` alone understates it),
`incorrect-code`, `diagnostic`, `sm6.7`; remove `needs-triage`. Not proposing `correctness`,
since correct behaviour here is rejection rather than different codegen. We may be missing
history behind the current labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is deliberately unrepresentative, and doubly so this batch.** Two 2019 issues plus
  three 2025–2026 issues, chosen partly to test whether isolated workers converge on related
  issues. All five still reproduce, which is what you would expect from a sample that
  over-weights old unfixed issues and recent filings — it is not a measurement of the backlog.
- **#2191's release history is unfalsifiable with release binaries.** Proving it was always
  present would need assert-enabled builds of past releases, which do not ship. The claim rests
  on source inspection (`ValidateAttributeIntArg`'s identifier branch unchanged since 2016) and
  is stated as such.
- **#8527 was measured on Windows/NTFS only.** The Linux path looks identical in source and the
  draft says "looks", but it was not run.
- **#2202's v1.8.2403 attribution to #6302/#6342** comes from release notes and the issue
  thread, not from building the revert.
- **#8737's ICE and silent cases were measured; the "UB" in the title was not.** Whether a
  runtime actually misbehaves needs a GPU. The draft claims only what the DXIL shows.
- **The bisection floor is v1.4.1907.** #2188, #2191 and #2202 (all May 2019) predate it, so
  "always reproduced" means "for as long as it is possible to check".
- **#2191's release probes are recorded under the wrong predicate.** 20 of 21 `out-*.txt` carry
  `# match: match-rejected.json` because of the collision described in item 3. The
  *measurements* are intact and the primary predicate's result was re-derived from the archived
  text (0 of 20 match), but the recorded scoring history for `match.json` is gone and was not
  reconstructed. Re-running is now possible without collision; it was not done, so that this
  report describes the tree as the batch left it.
- **Four `# expect:` declarations and one `# verdict:` header were revised during collation**,
  using `triage.py expect` and `reindex --accept`. No captured output, command line or exit
  status was altered. The changes are listed in items 7 and 8.

## Suggested next step

The workflow has now produced a wrong verdict in **every batch**, always in a newly sampled
category. Batch 004's wrong verdicts were `no-repro` on a crashed probe and `no-repro` on a
front-end rejection by a *newer* compiler — both fixed, both invisible until something
disagreed with something else.

Two things to test next:

1. **A second parallel batch, to see whether it is cheaper.** Batch 004 spent most of its
   collation budget on defects parallelism caused. If batch 005 does not, the model is
   established; if it does, the shared-state surface is larger than four fixes.
2. **An issue whose reported symptom is a *diagnostic*.** Item 4's rejected claim shows the
   `invalid-probe` heuristics and issues like #1627 are on a collision course, and no batch has
   yet triaged an issue where the expected output is an error message. That is where the
   current classifier is least trustworthy.

An automated pass over the backlog remains inadvisable, for the reason batch 003 gave and this
batch reinforced: three of five issues here have titles that no longer describe their
behaviour, and a plausible verdict against a stale title reads exactly like a correct one.
