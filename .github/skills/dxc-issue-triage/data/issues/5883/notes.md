# Notes — #5883

## What was tested

`repro.hlsl` is the issue body's compute shader, using the *const* variant
(`const S a = {m};`, the "invalid" branch the reporter describes on the
commented-out line 14). `variant-noconst.hlsl` is the same shader with the
reporter's own "valid" branch (`S a = {m};`, no `const`), used as a control.
Both compile with `-T cs_6_0 -E main` and no other flags. `match.json`
anchors on the first `BufferStore` call's literal payload: the
declaration-time constants `42,43,44` (row 0 of the `float2x3` initializer)
mean the bug fired; the post-mutation values `1,2,3` mean it did not.

## Result: reproduces, and always has

- **Ground truth** (`main-debug`, `89e2f98e2`, self-reports
  `1.9.0.5465 (triage, 7665270b9)`): `repro`. `out-main-debug.txt` shows
  `bufferStore.i32(..., i32 0, i32 undef, i32 42, i32 43, i32 44, ...)` and
  `..., i32 16, i32 undef, i32 45, i32 46, i32 47, ...)` — the matrix's
  *declaration-time* values, exactly as the reporter describes, not the
  `1,2,3`/`4,5,6` written immediately before the const init.
- **Control** (`variant-noconst.hlsl`, same command, `main-debug`):
  `no-repro`, `--expect no-match` holds. `variant-control-noconst-main-debug.txt`
  shows the correct `1,2,3`/`4,5,6` payload, confirming the predicate
  discriminates the const-vs-non-const behavior rather than matching every
  compile of this shader.
- **Release bisection**: `always-repro'd across v1.4.1907..v1.9.2607`
  (`v1.4.1907` = oldest bisectable release, `v1.9.2607` = newest stable at
  time of triage; 5 prereleases excluded from the search by policy, none
  named by the issue). Every probed release (`v1.4.1907`, `v1.5.2010`,
  `v1.6.2104`, `v1.6.2112`, `v1.8.2403`, `v1.9.2607`) plus `main-debug`
  scores `repro`. This is a silent-miscompile issue, not a diagnostic or a
  crash, so no release is `invalid-probe` here — every one of them compiles
  the repro to completion and emits DXIL; the question is only which
  payload it contains.
- **Compiler Explorer**: `dxc_1_6_2112` (CE's oldest DXC) and `dxc_trunk`
  both emit the same buggy `42,43,44`/`45,46,47` payload
  (`manual-case-godbolt-verify.txt`). Link: https://godbolt.org/z/s7WdTna8d.
  CE's DXC panes run Release builds and only reach back to v1.6.2112, so
  they corroborate the local Debug/release-matrix measurement above rather
  than substituting for it, but they do independently confirm the bug is
  still present in a current rolling trunk build (Release configuration),
  which is the configuration most users actually run.

## A predicate anchor bug, found and corrected in-issue

The first bisection run used a predicate anchored on the literal SSA
register name `%1` (`%dx.types.Handle %1, i32 0, ...`). It reported
`regressed-in v1.5.2010`, i.e. `v1.4.1907` scoring `no-repro`. Inspecting
`out-v1.4.1907.txt` directly showed this was wrong: v1.4.1907's disassembly
carries the **identical** buggy `42,43,44`/`45,46,47` payload as every other
release, but names the handle `%buffer_UAV_rawbuf` instead of `%1` — DXC's
older releases print named SSA values, and numbered values became the norm
only from `v1.5.2010` onward. This is exactly the "IR/disassembly text is
no more portable than diagnostics" trap already documented in `SKILL.md`
(structural anchors such as `%[\w.]+` are needed, not a modern build's
spelling), re-encountered here rather than a new finding. The anchor was
corrected to `%dx\.types\.Handle %[\w.]+` and every probe (`main-debug`,
the control, and both bisection endpoints) was re-run; all six release
probes and `main-debug` agree on `repro` under the corrected predicate, and
`bisect` now reports `always-repro'd` on the second run. Recorded in
`method-notes.md` for collation.

## Assessment

This is a genuine, long-standing silent-miscompile bug, not a diagnostic-
quality or feature-request issue. The reporter (a project collaborator)
supplied a complete, minimal, standalone repro and did a substantial amount
of the root-cause analysis themselves, tracing it to
`CodeGenFunction::EmitVarDecl`'s HLSL "treat local const as static global"
optimization: when a `const`-qualified local aggregate is initialized from
a `DeclRefExpr` naming another local variable,
`CGMSHLSLRuntime::EmitHLSLConstInitListExpr` → `ScanConstInitList` (source
still present, `tools/clang/lib/CodeGen/CGHLSLMS.cpp`, unchanged in this
area since the issue was filed — `git log` shows only two commits ever
touching this file, neither in `ScanConstInitList`) calls
`CodeGenModule::EmitConstantInit` on that variable's own *declaration*,
without checking whether the variable was mutated between its declaration
and the point where it is read into the const initializer list. The 2024
follow-up comment states the defect generalizes to struct/array-of-any-type
(not just matrix), which this triage did not separately re-verify with a
new repro (out of scope for revalidating an already-detailed report), but
which is consistent with the code path identified — `ScanConstInitList`'s
`DeclRefExpr` branch has no type-specific gating, so the same "read the
declaration, not the current value" defect applies uniformly to any
element type reached that way.

No maintainer response or fix attempt appears in the thread; the two
open-ended threads (the reporter's own attempted patch, which they say
broke `staticGlobals3.hlsl`) remain unresolved. No cross-references found in
the issue timeline.

Suggested action: **still-valid-keep-open**. This is squarely a
`correctness` defect (valid, well-formed source silently miscompiled, no
diagnostic) rather than an `incorrect-code` one (`incorrect-code`'s
description and sampled usage on this repo are about the compiler's
handling of *invalid* input, e.g. crashes/missing diagnostics on malformed
code, which is not this issue) — one of the more consequential classes of
bug this backlog carries precisely because nothing warns the user.
