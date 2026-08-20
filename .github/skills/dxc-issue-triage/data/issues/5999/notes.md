# Notes — issue #5999: "An issue with template type deduction and globallycoherent?"

## Summary

Reported 2023-11-09 by @simonwongms: a global `globallycoherent RWByteAddressBuffer` passed
into an HLSL function template (`template<typename BufferType> uint TemplateFunction(BufferType
AutoParam)`) triggers a compiler warning, and the reporter asks whether that warning is a false
positive (their PIX disassembly inspection of the generated code "looked correct").

The thread already contains a full, correct maintainer answer (llvm-beanz, 2024-01-18/22;
confirmed by pow2clk): the warning is **not** a false positive. `globallycoherent` (like
`row_major`) is implemented as an attribute, not a true type qualifier, so it is dropped
whenever the compiler computes the parameter's "canonical type" during template argument
deduction / overload resolution — here, that happens when `BufferType` is deduced for
`TemplateFunction`. DXC's code generation happens to still *propagate* `globallycoherent` back
onto the (nominally non-coherent) resolved resource in the cases tested here, so the emitted
DXIL/ISA is usually still functionally correct — merely with an extra, possibly-unwanted memory
barrier the compiler cannot otherwise justify without the warning. Fixing this properly requires
turning `globallycoherent`/matrix-orientation into real type qualifiers, which the maintainers
describe as a breaking, future-language-version redesign, not a small patch. No commit or PR
that resolves this is referenced anywhere in the thread.

This triage's job was therefore not to re-derive that conclusion (already correct and
uncontested since Jan 2024), but to (a) confirm the warning still fires unchanged on current
`main`, (b) establish how far back in the stable-release history it can be checked, and
(c) check whether labels/release-note coverage need anything.

## Repro

`repro.hlsl` reproduces the maintainer's own distilled example
(https://github.com/microsoft/DirectXShaderCompiler/issues/5999#issuecomment-1899072242,
itself https://godbolt.org/z/z4TnxrKqr — fetched via `godbolt.org/api/shortlinkinfo` and
transcribed verbatim) rather than the reporter's own (shader-playground-hosted, not fetchable
here) source, because llvm-beanz's link is explicitly presented as reproducing the same
reported behavior and is directly quotable. `cmd.txt` targets `-T cs_6_0` (the repro does not
depend on shader-model-6.6-only features; lowering the target profile from the CE link's
implicit `cs_6_6` extends the checkable release range without changing the observed behavior —
confirmed identical warning text at both `cs_6_0` and `cs_6_6` locally).

## Predicate

`match.json` matches the literal current diagnostic text `loses globallycoherent annotation`
(Sema, `warn_hlsl_impcast_coherence_mismatch`,
`tools/clang/include/clang/Basic/DiagnosticSemaKinds.td`). This exact wording was introduced by
commit `e50393e49` ("Enhance `globallycoherent` mismatch diagnostics", PR #5121, 2023-05-23),
which moved the check out of CodeGen (`CGHLSLMS.cpp`'s `isGLCMismatch()`, which previously
emitted a plain custom warning `"global coherent mismatch"`) and into Sema, adding directional
wording (loses/gains/demotes/promotes). See `git show e50393e49^:tools/clang/lib/CodeGen/CGHLSLMS.cpp`
for the pre-PR text.

The older wording is **not** included as an `any_of` branch: HLSL function templates
(`template<typename T>`) — required by this repro — were not accepted by dxc until v1.7.2308
(2023-08-14). Every earlier probeable release answers
`error: 'template' is a reserved keyword in HLSL` (see `out-v1.7.2212.1.txt`), which is a hard
parse failure recognized by the classifier's feature-absence markers
(`use of undeclared identifier`) and correctly demoted to `invalid-probe`. Since template
support postdates the wording change by three months, no release that can even parse this
repro could have emitted the pre-#5121 text, so a branch for it would be untested dead code
for this issue's history specifically. (It would matter for a *different* globallycoherent
issue whose repro does not require templates.)

**Control:** `control-no-coherence.hlsl` is the identical repro with every `globallycoherent`
removed (both the global and the explicit-function parameter), so there is nothing for the
predicate to match. Run with `--expect no-match`, confirmed on ground truth (`no-repro`,
`variant-control-no-coherence-main-debug.txt`) — the predicate does not fire on
non-mismatching code.

## Ground truth

`main-debug` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`) still emits:

```
repro.hlsl:18:5: warning: implicit conversion from 'globallycoherent RWByteAddressBuffer' to 'RWByteAddressBuffer' loses globallycoherent annotation [-Wconversion]
    TemplateFunction(SomeBuffer);
    ^
```

on the templated call, with **no** warning on the adjacent `ExplicitFunction(SomeBuffer)` call
(explicitly-typed `globallycoherent` parameters retain the qualifier fine) — exactly the
asymmetry the issue describes. `out-main-debug.txt` and `variant-control-no-coherence-main-debug.txt`
hold the full captures.

## Release history (`bisect --linear`)

```
skipped 1 release (no usable dxc asset): v1.2.0-alpha
skipped 5 prereleases from search by policy: v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24
v1.4.1907      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.5.2010      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2104      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2106      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2112      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.7.2207      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.7.2212      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.7.2212.1    n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.7.2308      repro
v1.8.2403      repro
v1.8.2403.1    repro
v1.8.2403.2    repro
v1.8.2405      repro
v1.8.2407      repro
v1.8.2502      repro
v1.8.2505      repro
v1.8.2505.1    repro
v1.9.2602      repro
v1.9.2602.24   repro
v1.9.2607      repro

result: always-repro'd across v1.7.2308..v1.9.2607
```

All 8 skipped releases (v1.4.1907 through v1.7.2212.1) are `invalid-probe` for the same reason:
`'template' is a reserved keyword in HLSL` (confirmed per-release in `out-v1.X.txt`), i.e. HLSL
function templates did not exist yet, not that the repro was malformed. v1.7.2308 (2023-08-14),
the oldest release that can even parse the repro, already reproduces — so the defect has always
reproduced for as long as it is possible to check with this repro shape, and specifically
throughout the compiler's whole life *since function templates existed*. The reporter's own
environment (`dxcompiler.dll 1.7 - 2310.11301.10016`, filed 2023-11-09) postdates v1.7.2308, so
this is consistent with, not contradicting, their report.

No prerelease opt-in was requested (the issue names no specific prerelease), so
v1.8.2306-preview is correctly excluded by policy even though it also postdates the template
feature and the wording change.

## Compiler Explorer

https://godbolt.org/z/E16q13zKa — `dxc_1_6_2112` (CE's oldest DXC; fails identically to the
local pre-v1.7.2308 releases, corroborating that the local release history cannot be pushed
back further with this repro), `dxc_trunk` (still reproduces, same wording as ground truth),
`hlsl_clang_trunk` (fails before it can even test the point at issue: Clang's HLSL front end
does not yet parse the `globallycoherent` keyword at all — `error: unknown type name
'globallycoherent'` — so this cannot currently show whether the successor compiler's
qualifier-vs-attribute redesign, discussed by llvm-beanz in the thread, has begun; it is a
negative result about feature parity, not about this specific defect). Read-back verified
(the tool warns on any short-link mismatch; none was reported). Full pane text in
`manual-case-godbolt-verify.txt`; `godbolt-note.txt` is the prepended banner.

CE limitation: it runs Release builds and its DXC panes always append `-Zi -Qembed_debug -Fc -`,
neither of which affects this diagnostic (it fires in Sema, independent of debug-info flags and
build configuration).

## Labels

Current: `bug`, `hlsl2021`, `shader-linking`, `type-system`. All four are accurate given the
finding — this is a genuine, reproducing bug (not a false positive), specific to the type
system's handling of a qualifier-as-attribute across template/overload resolution, explicitly
called out by llvm-beanz as mattering more once cross-translation-unit shader linking is
supported. No label change proposed.

## Release note

No release-note entry exists for this and none should be added by this triage: nothing has
changed in compiler behavior since the report (`always-repro'd`), and the maintainers have
explicitly deferred the real fix to a future, breaking, type-system redesign that has not
landed. A release note tracks a *shipped* change; there is not yet one to record. Per
CONTRIBUTING.md's release-note policy, this is exactly the case where none is warranted.

## Verdict

- status: `repros`
- repro-quality: `complete`
- history: `always-repro'd` (across v1.7.2308..v1.9.2607, i.e. for as long as it can be
  checked given that HLSL function templates did not exist before v1.7.2308)
- confidence: `high`
- suggested-action: `still-valid-keep-open` — this is an accurate, already-diagnosed, open
  design limitation with a maintainer-acknowledged fix path (turning `globallycoherent`/
  `row_major` into real type qualifiers) that has not been implemented; nothing here suggests
  closing it or asking the reporter for anything further.
- text-stale: none — the issue body and every comment remain an accurate description of
  current behavior; there is no maintainer comment left standing that contradicts current
  behavior (contrast with issues like #3055).
