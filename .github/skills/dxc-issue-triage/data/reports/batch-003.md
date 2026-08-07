# DXC issue triage — batch 003

**Ground truth:** clean `main` **Debug** build, `dxc` 1.9.0.15422, commit `eff900d5`.
**History:** 20 official release binaries, v1.4.1907 → v1.9.2607.
**FXC comparisons:** real `fxc.exe` from Windows SDK 10.0.26100.
**Nothing was posted, edited, labelled or closed. No DXC source was modified.**

## Headline

**#3038 is fixed** — the second closable issue in three batches. It crashed for five years
(v1.5.2010 → v1.8.2502) and has been clean since **v1.8.2505**, almost certainly as a
side-effect of PR #7440, which was filed against a different issue. Nobody noticed, so it
stayed open.

**#2427's fix has lapsed.** The behaviour is correct platform behaviour and was diagnosed as
such in 2019; the agreed remedy was a new flag. That flag was never added, and the PR carrying
it (`Fixes #2427`) was **closed unmerged on 2026-01-22** by an inactivity sweep — six weeks
before this triage. The issue is also completely unlabelled.

This batch deliberately sampled the two categories batches 001 and 002 never touched: issues
with **no usable repro** and issues that are **not compiler-verifiable**. That was the right
call — it produced three verdict shapes the workflow had never emitted, and exposed two more
wrong-verdict bugs in the tooling.

## Summary

| # | Title | Repro | Status | History | Action | Link |
| --- | --- | --- | --- | --- | --- | --- |
| [#1803](https://github.com/microsoft/DirectXShaderCompiler/issues/1803) | `[RW]StructuredBuffer<matrix>` ignores orientation | complete | **repros** | always (v1.4.1907+) | keep open | [4K5T5G5Wf](https://godbolt.org/z/4K5T5G5Wf) |
| [#1877](https://github.com/microsoft/DirectXShaderCompiler/issues/1877) | Struct cast ignored writing to `AppendStructuredBuffer` | complete | **repros** | always (v1.4.1907+) | keep open | [az56sPvs7](https://godbolt.org/z/az56sPvs7) |
| [#2427](https://github.com/microsoft/DirectXShaderCompiler/issues/2427) | Quoted folder parameters ending in `\` | complete | repros *(correctly)* | always | keep open — **revive PR #2660** | n/a |
| [#3038](https://github.com/microsoft/DirectXShaderCompiler/issues/3038) | `TraceRayInline` after `TraceRay` crashes compilation | agent-constructed | **does-not-repro** | **fixed in v1.8.2505** | **close-fixed** | [6s1W5rfKx](https://godbolt.org/z/6s1W5rfKx) |
| [#3150](https://github.com/microsoft/DirectXShaderCompiler/issues/3150) | Unspecified behavior from `sdiv` | prose-only | **not-compiler-verifiable** | n/a | needs-human-judgement | n/a |

Confidence is `high` on all five.

## Per-issue findings

### #1803 — `row_major` is discarded, not mis-applied

Reproduces on every release from v1.4.1907 to v1.9.2607.

The decisive evidence is not the operand order but a **control**: compiling the same shader
with `column_major` substituted for `row_major` produces **byte-identical DXIL**. The
attribute has no effect whatsoever, which confirms the reporter's 2018 diagnosis that it is
stripped during template-argument canonicalisation.

FXC still emits `store_structured u0.xyzw, l(0), l(0), l(11,12,21,22)` — verbatim what the
issue quoted seven years ago.

There is a genuine design question underneath (FXC rejects `RWStructuredBuffer<row_major
int2x2>` and ignores `/Zpr`), but no reading of it makes silently dropping the attribute
correct.

### #1877 — silent wrong code on the `Append` path

Reproduces on every release from v1.4.1907 to v1.9.2607.

`(I32)f32` emits no `fptosi`. The sharper detail is that the cbuffer load is
`cbufferLoadLegacy.**i32**` — the float's bit pattern is read as an integer, so the value is
never a float at any point in the module.

The reporter supplied the control themselves: the same cast through `RWStructuredBuffer` does
emit `%5 = fptosi float %4 to i32`. That both validates the predicate and confirms the defect
is `Append`-specific.

No diagnostic; the module validates. Worse than a crash, because nothing surfaces it.

### #2427 — the behaviour is correct; the fix lapsed

Measured through `cmd.exe` (PowerShell re-quotes arguments and masks the bug entirely):

| command | result |
| --- | --- |
| `-Fd "dbgdir\"` | `dxc failed : Required input file argument is missing.` |
| `-Fd "dbgdir"\` | works |
| `-Fd "dbgdir\\"` | works |
| `-Fd dbgdir\` | works |

@pow2clk established in 2019 that the trailing backslash escapes the closing quote during
**argv splitting**, before dxc runs, and that FXC behaves identically. So it must reproduce,
and "still broken" is a misleading summary.

What actually changed:

- No `-Fdd`, `-Fad` or `DebugDir` option exists in `dxc --help` or `HLSLOptions.td`.
- PR #2430 ("Add Fdd option") — closed unmerged 2020-01-23.
- PR #2660 ("Fad option", `Fixes #2427`) — open for six years, **closed unmerged 2026-01-22**
  by an inactivity sweep.

@damyanp's June 2024 note that a PR was still open and could be finished was accurate then.
It no longer is. The issue has no route to resolution and **no labels at all**.

### #3038 — fixed in v1.8.2505

The repro is **agent-constructed** (the body elides every argument), which is normally weak
evidence for a *fix*. Here it is anchored by reproducing both signatures the thread reported,
each on the release that matches its report:

| build | result |
| --- | --- |
| v1.5.2010 (nearest release to the 2020 report) | `0xC0000005` access violation |
| v1.8.2502 | `error: llvm::cast<X>() argument of incompatible type!` (@donguklim, 2022) |
| CE `dxc_1_6_2112` (Linux, Release) | `Internal Compiler error: cast<X>() argument of incompatible type!` |
| `main` Debug | clean |

@tex3d's 2020 workaround also behaves exactly as predicted — on v1.8.2502 the shared-`RayDesc`
shader crashes while the copied-`RayDesc` one compiles — confirming the repro isolates the
reported trigger, and that the workaround is now unnecessary.

Linear scan over all 20 releases: unprobeable at v1.4.1907, crashing v1.5.2010 → v1.8.2502
(14 consecutive releases), clean from v1.8.2505.

**Likely fix: PR #7440**, "Refactor udt intrinsic arg copy to before SROA, flatten RayDesc"
(@tex3d, merged 2025-05-16). Verified by ancestry check to be in the v1.8.2505 release commit
and not in v1.8.2502; its description names this root cause. It was filed against #7434, whose
repro also reuses one `RayDesc` across two intrinsics — the same defect wearing a different
intrinsic pair. **The window contains 162 commits, so this is a strong attribution, not a
proven one.**

### #3150 — not a bug; an unwritten specification

Active design discussion (14 comments, latest 2026-01-22). No verdict is appropriate; three
checkable facts were established instead:

1. **The planned doc change never landed.** @damyanp's 2024-07-03 plan was to note in
   `DXIL.rst` that `sdiv` divide-by-zero is undefined. `DXIL.rst` still documents
   divide-by-zero only for the DXIL `UDiv` *operation*.
2. **DXC emits the LLVM instructions**, `sdiv i32` / `udiv i32`, not the DXIL operation.
3. **`INSTR.NOIDIVBYZERO` / `NOUDIVBYZERO` are unreachable from DXC.** They fire only on a
   literal constant zero denominator, which DXC never emits — `a / 0` is const-folded to
   `undef` first, yielding `error: Assignment of undefined values to UAV.` instead. Still true
   at `-Od`. No comment in the thread mentions these rules exist.

## What batch 003 taught us about the method

Two more wrong-verdict bugs, both fixed, both tested. That is five found across three batches,
and **every one of them was found by sampling a kind of issue the previous batch had not
covered** — never by running more issues of the same shape.

### 1. Feature-absence diagnostics faked a transition (new)

`invalid-probe` detection caught releases that reject a *profile*, but not releases that
predate a *language feature*. v1.4.1907 answers `use of undeclared identifier 'RayQuery'` —
DXR 1.1 did not exist — and that scored as a clean run. The scan therefore reported "transition
at v1.5.2010 → repro", implying a regression that never happened. In a binary search it would
have been worse than cosmetic. The detector now also matches `use of undeclared identifier`,
`unknown type name`, `no member named` and `no matching function for call to`.

### 2. Absence-based predicates are satisfied by failure (new)

#1877's predicate is `not_contains fptosi` — "the symptom is that the conversion is missing".
Any release that failed to *parse* the repro also emits no `fptosi`, and would have scored as a
perfect reproduction. Those probes were checked by hand and did compile, so no verdict was
wrong, but the hazard is structural and would eventually fire unattended. The runner now
reclassifies such a probe as `invalid-probe` when the compile also failed, and prefers a
positive predicate where one exists.

### 3. A negative result from a command that errored is not a negative result

`git merge-base --is-ancestor <sha> origin/release-1.8.2505` exited non-zero, which was
briefly read as refuting the #7440 attribution. The ref simply did not exist locally — the
release branches had never been fetched. The command was answering a different question
entirely. This is the `invalid-probe` trap one layer out: a tool that never ran the test still
returns something shaped like an answer. **Check that every input to a negative resolved
before believing it.**

### 4. "Still reproduces" can be the uninteresting half

#2427 reproduces, and saying so would have been true and useless. The thread had diagnosed the
behaviour six years ago; the live question was what happened to the fix. Where a thread has
already reached a diagnosis, re-confirming it adds nothing — check the resolution instead. The
issue timeline API lists every linked PR, and in this case revealed that the fix PR had been
swept closed weeks earlier.

### 5. Not every repro is a shader

`cmd.txt` assumes one dxc invocation over HLSL. #2427's repro *is* an argument string, and the
shell rewrites the thing under test: run through PowerShell, the bug vanishes. It had to be
driven through `cmd.exe` verbatim. Worth recording which shell produced a result whenever the
repro is a command line rather than a program.

### 6. Agent-constructed repros can support a "fixed" verdict — but only when anchored

Normally a constructed repro is weak evidence that something is fixed: it may simply never have
reproduced. #3038 is the exception because it reproduces **both** signatures the thread
reported, each on the release contemporary with its report, and because the workaround
documented in 2020 behaves as predicted. Reconstructing the *history* is what makes the
construction trustworthy — and the trigger came from a comment, not the issue body.

### 7. The independent review caught two real errors — and introduced one

Two catches were substantive rather than stylistic, both in the "wrong about what correct
behaviour would be" category the skill already warns about:

- #1803 said a row-major store "should write 11,12,21,22". But FXC *rejects*
  `RWStructuredBuffer<row_major int2x2>` outright, so rejecting the syntax is a defensible
  correct behaviour and the draft was quietly presupposing the design answer. Reworded to
  "honouring `row_major` would store …".
- #1803 also claimed the reporter's `Sema` canonicalisation diagnosis "still holds". That
  mechanism was never independently verified — only its observable consequence. Reworded to
  "consistent with your diagnosis".

Two suggestions were **rejected**:

- It rewrote every disclosure trailer to drop "please flag anything that looks wrong", reading
  it as apologetic. The skill has already ruled the opposite way: the invitation is the part a
  reader can act on. This is the documented over-cutting pattern, now seen in three batches.
- Tightening #2427, it produced "Through `cmd.exe`, the trailing backslash escapes the closing
  quote" — which misattributes the cause. The escaping is CRT/shell argv splitting generally,
  not a `cmd.exe` quirk; `cmd.exe` was merely the harness. **A reviewer optimising for
  concision can introduce a technical inaccuracy while removing a true one**, so review output
  needs checking in both directions, not just for over-cutting.

### 8. Committing the evidence found two stale-evidence gaps

Moving the workspace into `.github/skills/dxc-issue-triage/data/` forced a decision about
what is *derived* and what is *evidence*. Making the database derived — rebuilt from the tree
by `triage.py reindex`, with run verdicts **re-scored rather than restored** — turned the
rebuild into a regression test over every batch so far. It immediately found two things:

- **#3873 kept three `-T ps_6_7` probes** after the profile was corrected to `ps_6_0`.
  `bisect` short-circuits once both endpoints agree, so it never revisited the middle of the
  range. Re-probed at `ps_6_0`, all three **hang** — so `always-repro'd` is now verified
  across the range instead of only at its endpoints.
- **All 21 of #3768's probes still carried `-fcgl -Vd`** after that workaround was removed
  from `cmd.txt` in batch 002. The removal had been confirmed by hand but never re-recorded,
  so the published history rested on a configuration the report said was no longer in use.
  Re-scanning without it reproduces the identical window — regressed at v1.6.2104, fixed at
  v1.6.2112 — so the verdict was right, but it was right by luck rather than by evidence.

Neither changed a verdict, and that is the part worth keeping: **"the verdict survived" is
not the same as "the evidence supported it"**, and only a mechanical check tells them apart.
Both now run on every `reindex`.

A third, smaller lesson: `out-<compiler>.txt` implicitly means "the primary repro, scored by
`match.json`". Controls and translated variants stored under that name get scored with the
primary predicate and generate spurious disagreements — #1702's compute-shader variant
legitimately emits an error its pixel-shader original does not. Those are now `variant-*.txt`,
and hand-captured command-line evidence is `manual-case-*.txt`.

### 9. A blind re-derivation test found a claim resting on nothing

Asked whether these analyses are reproducible or are quietly leaning on conversation context,
we measured it rather than answered it. A fresh agent on a different model was given **only**
`data/issues/3038/`, with `notes.md`, `verdict.json` and `comment.md` withheld, and asked to
derive the verdict.

It independently reproduced the transition (v1.8.2502 → v1.8.2505), the repro quality, the
suggested action, and the rejection of v1.4.1907 as unprobeable. It diverged on one field only
because the status vocabulary lived in `SKILL.md`, which it could not read — since fixed by
putting the taxonomy in `README.md`, next to the data it describes.

Then it found a real defect. #3038's control shader existed, but **its output had never been
captured**. The control had been run by hand, and its result — "the control compiles clean at
v1.8.2502 where the repro crashes" — was published in both this report and the draft comment
on the strength of a number nobody had written down. It was true; it has now been captured
(control exits `0`, repro exits `0x80004005` with `llvm::cast<X>()`); and it was unsupported
for as long as it took someone to check.

The fix is tooling, not vigilance: `run --shader X --label Y` reuses the repro's exact
arguments against a different source, so capturing a control is now cheaper than not capturing
one. A step that depends on remembering to do it by hand is a step that gets skipped.

Two provenance gaps closed alongside it: `verdict.json` now records **which model triaged** the
issue and **which model ran the mandatory independent review**. The review was required from
batch 001 onward and genuinely happened every time, but nothing on disk said so — a required
step that leaves no trace is one you cannot later tell was skipped.

**On session boundaries:** the initial recommendation here — one session per batch — was wrong,
and checking it is what showed that. Of the 16 method lessons in these three reports, **13 were
discovered inside a single issue**, two came from the batch-level draft review, and one from
`reindex`, which uses no session context at all. What crossed issues was *re-recognising* a
known trap, which is collation work. Meanwhile long sessions cost real quality: scrutiny decays
across a batch, and a batch-length session gets compacted mid-flight — batch 003's later issues
were analysed against a summary of the method rather than the method.

The workflow is now **one session per issue, run in parallel, plus a collation session per
batch**. Two rules keep it safe: a per-issue session never writes shared state (method
observations go to `method-notes.md`; collation promotes them), and collation runs `reindex`
first, which re-scores everything and so applies any lesson learned late in the batch
retroactively to issues triaged before it.

### 10. The completeness audit found six issues with uncaptured evidence

Parallel triage removes the human who would have noticed a missing step, so `reindex` gained a
fourth check: **evidence a completed triage should have left behind.** On its first run it
flagged 6 of 15 issues, and every flag was real:

- **#3150 had no captured output at all.** It is legitimately `not-compiler-verifiable` — a
  specification gap with nothing to reproduce — but its verdict makes two *compiler-measured*
  claims: that DXC emits LLVM `sdiv`/`udiv` rather than the DXIL `UDiv` operation that
  `DXIL.rst` documents divide-by-zero for, and that `INSTR.NOIDIVBYZERO` is unreachable because
  `a / 0` is const-folded to `undef` first. Both were published on the strength of numbers
  measured by hand and never written down. Now captured: `%7 = sdiv i32 %5, %6`, and at `-Od`
  the store becomes `i32 undef` and validation rejects it — the divide never survives to be
  validated as a divide.
- **#3009, #3048 and #3873's compute translations** — the shaders adopted for the Clang panes —
  had no captured output, so the requirement that a translation still reproduces before being
  adopted was unverified. All three do.
- **#1702, #1803, #1877 and #3009's variants** had output, but with **corrupted provenance
  headers**: the batch-003 rename left `# compiler: colmajor`, `# exe: <cache>/.`, and empty
  `cmd`/`exit`/`verdict` fields. They were excluded from probe scoring, which was the point,
  but that also meant nothing ever looked at them again.

The deeper fix is that a control now carries a **declared expectation**, recorded in its header
and re-checked on every `reindex`. That turns it from an observation into a permanent
assertion, and it runs in both directions — a distinction the first implementation got wrong:

- `--expect no-match` — a **negative** control, a known-good input the predicate must not fire
  on. This is #3009's, and the case that motivated controls in batch 002.
- `--expect match` — an **identity** control. #1803's shader declared `column_major` must
  produce *identical* DXIL to the `row_major` original, because that identity is precisely what
  proves the attribute is ignored.

A blanket "warn if a control matches" rule — which is what was written first — reports #1803's
central finding as a predicate bug. Two other errors surfaced the same way: `repro-pow2clk.hlsl`
was labelled a control when it is the maintainer's *second repro*, and the live `run` path
crashed on an issue with no `match.json` while `reindex` tolerated it, so the two disagreed
about a case that had never arisen before.

The pattern across all of it: **evidence that nothing re-checks decays silently.** Every gap
here had existed for at least one batch, none had changed a verdict, and none was visible until
something mechanical looked for it.

## Proposed label changes

Validated against the live taxonomy (58 labels, re-fetched this run — batch 002's list was
already stale).

| # | Now | Add | Rationale |
| --- | --- | --- | --- |
| #1803 | `bug`, `matrix-bug` | `correctness`, `fxc-disagrees`, `type-system` | Silent wrong storage layout; FXC honours it; attribute lost via template canonicalisation (same root cause as #1722) |
| #1877 | `bug` | `correctness`, `fxc-disagrees` | Silent wrong code; FXC emits `ftoi` |
| #2427 | *(none)* | `enhancement`, `usability`, `up-for-grabs` | Not a codegen bug; the work exists in PR #2660 and mainly needs a rebase |
| #3038 | `bug` | `crash` | Was a compiler crash; recorded for searchability if closed |
| #3150 | `docs` | `dxil` | `docs` is right; `dxil` groups it with related spec discussions |

No removals proposed this batch. #2427 being **unlabelled** is itself a finding — it is
plausibly why the issue went quiet.

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


### Draft — [#1803](https://github.com/microsoft/DirectXShaderCompiler/issues/1803) [RW]StructuredBuffer<matrix> ignores orientation

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1803](https://github.com/microsoft/DirectXShaderCompiler/issues/1803).

**Still reproduces** on `main` (1.9.0.15422, eff900d5), and on every release from v1.4.1907
to v1.9.2607.

Substituting `column_major` for `row_major` produces **byte-identical DXIL**:

```
call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 0,
                                 i32 11, i32 21, i32 12, i32 22, i8 15)
```

`int2x2(11,12,21,22)` gives m[0][0]=11, m[0][1]=12, m[1][0]=21, m[1][1]=22; honouring
`row_major` would store 11,12,21,22. FXC (SDK 10.0.26100) emits
`store_structured u0.xyzw, l(0), l(0), l(11,12,21,22)`, matching the original report.

Repro with an FXC pane: https://godbolt.org/z/4K5T5G5Wf

This is consistent with your diagnosis that template-argument canonicalisation strips the
typedef attribute, yielding `RWStructuredBuffer<matrix<int,2,2>>`.

FXC rejects `RWStructuredBuffer<row_major int2x2>` and ignores `/Zpr` here, so the intended
behaviour still needs a design decision.

Suggested labels: `correctness`, `fxc-disagrees`, `type-system`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
````

### Draft — [#1877](https://github.com/microsoft/DirectXShaderCompiler/issues/1877) DXC ignores struct cast when writing to an AppendStructuredBuffer

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1877](https://github.com/microsoft/DirectXShaderCompiler/issues/1877).

**Still reproduces** on `main` (1.9.0.15422, eff900d5), and on every release from v1.4.1907
to v1.9.2607.

Current DXIL contains no `fptosi` conversion:

```
%3 = call %dx.types.CBufRet.i32 @dx.op.cbufferLoadLegacy.i32(...)
%4 = extractvalue %dx.types.CBufRet.i32 %3, 0
call void @dx.op.bufferStore.i32(..., i32 %4, ...)
```

`cbufferLoadLegacy.**i32**` reads the float's bit pattern as an integer; the value is never
treated as a float.

`RWStructuredBuffer` remains a control: the identical cast emits
`%5 = fptosi float %4 to i32`. FXC still emits `ftoi r0.y, cb0[0].x`.

Repro with an FXC pane: https://godbolt.org/z/az56sPvs7

No diagnostic is emitted, and the module passes validation.

Suggested labels: `correctness`, `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
````

### Draft — [#2427](https://github.com/microsoft/DirectXShaderCompiler/issues/2427) Compiler fails on quoted folder parameters finishing with '\\' 

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#2427](https://github.com/microsoft/DirectXShaderCompiler/issues/2427).

The original command still fails on `main` (1.9.0.15422, eff900d5). As @pow2clk explained in
2019, the trailing backslash escapes the closing quote during argv splitting, before dxc sees
the arguments. Measured by issuing each line through `cmd.exe` verbatim:

| command | result |
| --- | --- |
| `-Fd "dbgdir\"` | `dxc failed : Required input file argument is missing.` |
| `-Fd "dbgdir"\` | works |
| `-Fd "dbgdir\\"` | works |
| `-Fd dbgdir\` | works |

The command-line behaviour is unchanged; the proposed directory-option fix has not landed:

- No `-Fdd`, `-Fad` or equivalent directory option exists in current `dxc --help` or in
  `HLSLOptions.td`.
- #2430 ("Add Fdd option") was closed unmerged in Jan 2020.
- #2660 ("Fad option for automatic debug output", `Fixes #2427`) stayed open until it was
  closed unmerged on 2026-01-22 by an inactivity sweep.

@damyanp's 2024 note that a PR was still open was accurate at the time; #2660 is now closed.
Reviving it remains a concrete next step.

The issue is currently unlabelled. Suggested labels: `enhancement`, `usability`,
`up-for-grabs`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
````

### Draft — [#3038](https://github.com/microsoft/DirectXShaderCompiler/issues/3038) DXR 1.1: Using TraceRayInline(...) right after TraceRay(...) crashes shader compilation

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3038](https://github.com/microsoft/DirectXShaderCompiler/issues/3038).

**Fixed:** the crash is present in **v1.5.2010 through v1.8.2502**, absent from **v1.8.2505**
onward, and does not reproduce on `main` (1.9.0.15422, eff900d5).

Because the body elides the arguments, the repro was reconstructed using @tex3d's observation
that both calls must share one `RayDesc`. It reproduces both reported signatures:

| build | result |
| --- | --- |
| v1.5.2010 | access violation (`0xC0000005`) - matches the original report |
| v1.8.2502 | `error: llvm::cast<X>() argument of incompatible type!` - matches @donguklim's 2022 report |
| `main` | compiles cleanly |

On v1.8.2502, the shared-`RayDesc` version crashes while the copied-`RayDesc` control
compiles. Both compile on current builds, so **the workaround is no longer needed**.

Before/after on Compiler Explorer: https://godbolt.org/z/6s1W5rfKx (`dxc_1_6_2112` crashes,
`dxc_trunk` is clean).

#7440 ("Refactor udt intrinsic arg copy to before SROA, flatten RayDesc") is in v1.8.2505 but
not v1.8.2502. It says RayDesc args "weren't copied in when necessary" and was filed against
#7434, whose repro also reuses one `RayDesc` across two intrinsics. Because the fix window
contains 162 commits, #7440 is a strong candidate, not a proven attribution.

Suggested action: close as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
````

### Draft — [#3150](https://github.com/microsoft/DirectXShaderCompiler/issues/3150) Unspecified behavior from new-to-DXIL sdiv instruction

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3150](https://github.com/microsoft/DirectXShaderCompiler/issues/3150).

**1. The planned documentation note is still absent.** @damyanp's 2024-07-03 plan was to
document in `DXIL.rst` that `sdiv` divide-by-zero is undefined. Current `DXIL.rst` mentions
divide-by-zero only for the DXIL `UDiv` *operation* ("returns 0xffffffff for both quotient and
remainder"), not the LLVM `sdiv`/`udiv` *instructions*.

**2. DXC still emits the LLVM instructions, not the DXIL operation** (`main`, 1.9.0.15422):
`sdiv i32 %5, %6` / `udiv i32 %9, %10`, matching @llvm-beanz's description.

**3. DXC-produced DXIL does not reach the validator's div-by-zero rules.**
`INSTR.NOIDIVBYZERO` / `INSTR.NOUDIVBYZERO` in `DxilValidation.cpp` apply only to a *literal
constant* zero denominator. DXC folds `a / 0` to `undef` before validation; for the tested
shader, the diagnostic is:

```
error: Assignment of undefined values to UAV.
```

This still holds with `-Od`; the rules can therefore fire only on DXIL from other producers.

Suggested label: `dxil`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is deliberately unrepresentative.** This batch over-weights no-repro and
  non-verifiable issues by design. Three of five needed evidence from *outside* the compiler
  (PR states, branch ancestry, documentation), which will not generalise.
- **#3038's fix attribution is strong, not proven.** 162 commits sit in the window. Building
  at `053e7ac65^` and `053e7ac65` would settle it.
- **#1803 has an unresolved design question** underneath the defect; the label and comment
  say so rather than pre-empting it.
- **#3150 is live.** The draft is deliberately three facts and no opinion.
- **The bisection floor is v1.4.1907.** "Always reproduced" means "for as long as it is
  possible to check". #1803 (2018) and #1877 (Jan 2019) both predate the floor.

## Suggested next step

Batches 001–003 have covered old/prose issues, SPIR-V and crashes, and now no-repro and
non-verifiable issues. The workflow has produced a wrong verdict in **every** batch so far,
always in a newly sampled category, so the next batch should keep sampling rather than scale up.

The two shapes still untested are:

1. **Issues with an attached file or multi-file repro** — the workspace and Compiler Explorer
   are both effectively single-file today, and `cmd.txt` has never been exercised with
   includes, `-I`, or a second translation unit.
2. **Recently-filed issues (2025–2026)**, where "still reproduces" is nearly certain and the
   useful output is triage quality — duplicate detection, missing labels, missing repro steps —
   rather than history. That is also the population an automated pass would spend most of its
   time on.

An automated pass over the whole backlog is still not advisable. The failure mode is not that
verdicts come out wrong at random; it is that a plausible-looking verdict comes out wrong in
a category nobody has sampled yet, and reads exactly like the correct ones.
