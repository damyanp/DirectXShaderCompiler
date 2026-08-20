# Issue #5823 — notes

Ground truth: `main-debug`, registered `git_commit` = `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(confirmed ancestor of `upstream/main`; local `dxc.exe --version` matches the registry
exactly). Batch: batch-019.

## Summary of what's actually going on

The issue conflates (at least) three distinct things, decomposed up front in `expected.md`:

1. **The original 2023 SIGSEGV** under `-spirv` for an out-of-line (OOL) definition of a
   **partial-specialization**'s `static const` array member
   (`GaussLegendreValues<2, floating_point_t>::wi`), reported against a stale CE `dxc_trunk`
   pin (`v1.7.2207`, 2022-07-18).
2. **A December 2025 retitle** ("also affects DXIL") reporting that a *syntactically corrected*
   OOL definition of the same kind of member fails with `error: casting to type 'void'
   unimplemented`.
3. **Two February 2026 complaints**: (a) DXC silently accepts an illegal, C++-invalid
   duplicated `static` at the OOL definition site instead of diagnosing it, the way Clang
   does for the equivalent C++ construct; (b) OOL definition of templated-struct members
   doesn't work at all, even for a full/explicit specialization.

## Primary repro and predicates

`repro.hlsl` is the reporter's own minimal 2023 repro (`dWMfjxza1`), run via `cmd.txt`
(`-HV 202x -T ps_6_7 -E PSMain -spirv repro.hlsl`). Two predicates:

- `match-crash.json` — `internal_failure` only, isolating the reported *crash* signature.
- `match.json` — `any_of[internal_failure, contains("casting to type 'void' unimplemented")]`,
  covering "crashes or is diagnosed with the historically-reported text", since the exact
  presentation (crash vs. E_FAIL) is known (see below) to have changed across releases.

### The crash is fixed; the underlying defect is not

Against ground truth, `repro.hlsl` exits `2147500037` = `0x80004005` (`E_FAIL`), **not** a
crash — confirmed with `cdb -c "g;kn 40;q"` that the process reaches an ordinary
`exit()`/`ExitProcessImplementation` path from `dxc.cpp`'s error handling, not a hardware
trap. stderr is `error: casting to type 'void' unimplemented`, the exact text
`cassiebeckley` reported in the original issue thread.

- `match-crash.json` bisects to **fixed-in `v1.7.2308`** (2023-08-14), last-repro'd
  `v1.7.2212.1` (2023-03-01) — see `out-main-debug--match-crash.txt` and the bisect log. This
  is *before* the issue was even filed (2023-10-03) and before `cassiebeckley`'s
  investigation, which is consistent with the reporter's CE pin (`v1.7.2207`, 2022-07-18)
  being stale relative to trunk at filing time.
- `match.json` (crash-or-diagnosed-text) bisects to **always-repro'd** across every
  probeable release `v1.7.2207`..`v1.9.2607` through `main-debug` (5 pre-2022 releases were
  invalid probes — `-HV 202x`/`ps_6_7` unsupported; 5 prereleases excluded by policy). So the
  crash's specific manifestation changed, but this exact input has never successfully
  compiled in any release that could be probed.

### Source-level attribution: PR #8079 fixed the crash, but only for primary-template context

The issue's own cross-reference timeline names the fix directly: **PR #8079**,
"`[SPIR-V] Fix crash with out-of-line template decl`" (merged `df50f51f8` into `main`,
2026-01-26, commit message says `Fixes #5823`). Its root commit `d4940f5c3` adds, in
`tools/clang/lib/SPIRV/SpirvEmitter.cpp`:

```cpp
if (decl->getInit() && decl->getInit()->getType()->isVoidType())
  return;
```

with a comment describing exactly the AST duplication `cassiebeckley` originally diagnosed
(a template-declaration `VarDecl` with a `void`-typed `InitExpr`, alongside the real
instantiation's `VarDecl`). PR #8079 was later refined in a follow-up commit ("change
detection method") to key off declaration context instead of the init's type; ground truth's
current `SpirvEmitter.cpp` reads:

```cpp
auto *RC = dyn_cast<clang::CXXRecordDecl>(decl->getDeclContext());
auto *TC = RC ? RC->getDescribedClassTemplate() : nullptr;
if (decl->getInit() && TC)
  return;
```

`CXXRecordDecl::getDescribedClassTemplate()` is only non-null when `RC` is the **primary**
template's pattern record — it is null for `ClassTemplatePartialSpecializationDecl` and for
explicit/full specializations. The fix's own added regression test,
`tools/clang/test/CodeGenSPIRV/template.static.var.split.hlsl`, exercises exactly this
primary-template, non-specialized case (`template<typename T> const static T
MyClass<T>::array[2] = {1, 2};`, array unused, `CHECK-NOT: OpVariable`) — confirmed
reproduced verbatim here as `variant-primary-template-fix-test.hlsl`
(`variant-primary-template-illegal-static-unused-main-debug--match-crash.json`... see
`variant-primary-template-illegal-static-unused-main-debug--match-crash.txt`): exit 0, no
crash, hypothesis supported.

This precisely explains the empirical split found below: the fix suppresses the crash for
*primary-template* and *full/explicit-specialization* OOL declarations, but **a partial
specialization's member (`RC` is a `ClassTemplatePartialSpecializationDecl`, so
`getDescribedClassTemplate()` is null) is never matched by this guard** — so the exact class
of input in the original repro (and in the 2025-12 retitle) still reaches the "casting to
type 'void' unimplemented" codepath as a diagnosed E_FAIL, not a crash, but still a failure
to compile.

## Variant matrix (all against `main-debug`, ground truth)

| Template kind | OOL spelling | Array used? | Result | Capture |
|---|---|---|---|---|
| Non-template struct | correct (`const`) | n/a | **compiles clean** | `variant-nontemplate-const-main-debug.txt` |
| Non-template struct | illegal dup `static` | n/a | **compiles clean, no diagnostic**, constant genuinely folded into SPIR-V (`%float_1 %float_0`) | `variant-nontemplate-static-ool-main-debug.txt` |
| Primary (generic) template | illegal dup `static` | unused | **compiles clean** (matches PR #8079's own regression test) | `variant-primary-template-illegal-static-unused-main-debug--match-crash.txt` |
| Primary (generic) template | illegal dup `static` | used | **compiles clean**, correct codegen | `variant-primary-template-illegal-static-used-main-debug.txt` |
| Primary (generic) template | correct (`const`) | used | **fails**: `'const' is not a valid modifier for a field` | `variant-primary-template-correct-used-main-debug.txt` |
| Full/explicit specialization | illegal dup `static` | used | **compiles clean**, correct codegen | `variant-full-spec-used-array-spirv-main-debug.txt`, `variant-full-spec-used-array-dxil-main-debug.txt` |
| Full/explicit specialization | correct (`const`) | used | **fails**: `'const' is not a valid modifier for a field` | `variant-full-spec-used-array-correct-main-debug.txt` |
| Full/explicit specialization | correct (`const`) | unused | **fails**: `'const' is not a valid modifier for a field` | `variant-full-explicit-spec-*-main-debug.txt` |
| Partial specialization | illegal dup `static` | unused (primary repro) | **fails**: `casting to type 'void' unimplemented` (E_FAIL, was SIGSEGV before v1.7.2308) | `out-main-debug.txt` |
| Partial specialization | illegal dup `static` | used | **fails**: `casting to type 'void' unimplemented` | `variant-partial-spec-used-array-spirv-main-debug.txt` |
| Partial specialization | correct (single `const`, no duplicate `static`) | unused | **fails**: `'const' is not a valid modifier for a field` (not the historical "casting to void" text — different failure signature for the corrected syntax) | `variant-corrected-dxil-main-debug.txt` |

Conclusion from the matrix: for a **partial specialization**'s member, OOL definition never
compiles, regardless of `static` duplication or array usage — this is the persisting defect
behind claims 2 and 3(b). For a **primary template** or a **full/explicit specialization**'s
member, OOL definition compiles *only if* the illegal duplicated `static` is present; the
standards-correct spelling (single `const`) is misparsed as a new in-class field declaration
and rejected with `'const' is not a valid modifier for a field` — this is claim 3(a)'s flip
side: DXC's parser is keying off the (illegal) `static` token as its "is this an OOL
specialization definition" signal, so the reporter's complaint that "DXC wrongly *requires*
static at the OOL site" is, empirically, correct for the full/explicit-specialization and
primary-template cases (though not for the partial-specialization case, which fails either
way).

## External corroboration

**Issue #6677** ("Out of line initialization of static data members of templated structs
won't compile", closed `NOT_PLANNED` 2024-06-10) is the same underlying area. Maintainer
`llvm-beanz` there explains the root cause authoritatively: *"HLSL has C++98's templates...
[the reporter's generic OOL init] depends on C++11 template resolution"* — i.e., DXC's
template model deliberately does not implement the C++11-style OOL-definition matching that
would make a **generic** (non-specialized) templated OOL initializer resolve against its
in-class declaration; that gap is tracked as a language feature request
(`hlsl-specs#109`/`#21`), not a bug. Separately, in a 2025-12-10 comment on that same issue,
the reporter posted **the identical `'const' is not a valid modifier for a field` bogus
diagnostic** for a syntactically-correct OOL full-specialization definition, and explicitly
asked *"should we open a new issue or #5823 with the changed title is sufficient?"* —
confirming #5823 is the intended forward-tracking issue for that specific bogus-diagnostic
defect, which is corroborated by our variant matrix above as a genuine parser bug (not a
C++98-vs-C++11 template-resolution feature gap): it reproduces even for a **full/explicit**
specialization, where no generic template-argument deduction is required at all.

Clang (C++) diagnoses the equivalent illegal-`static`-at-OOL-site construct with `'static'
can only be specified inside the class definition` (public godbolt link `M9hajz5eE`, already
quoted in the issue body) — confirming DXC's silent acceptance (claim 3(a)) is a genuine gap
relative to the language DXC's HLSL syntax is modeled on, independently of the parser-bug
finding above.

## Compiler Explorer

Published `https://godbolt.org/z/dsK39nrKE` (compilers `dxc_1_6_2112,dxc_trunk`, with
`godbolt-note.txt` banner). CE's public `dxc_trunk` (Release build, lags/differs from local
ground truth) shows exit 5 (Linux-truncated `0x80004005`) with the older `casting to type
'void' unimplemented` text for the primary repro — external corroboration that the input
still fails to compile, though (per the skill's standing warning) diagnostic text is not
portable across builds; several ground-truth variants above show the newer `'const' is not a
valid modifier for a field` text for the same underlying "won't compile" fact.

## Timeline cross-reference check

`gh api repos/microsoft/DirectXShaderCompiler/issues/5823/timeline` cross-references:
`hlsl-specs#109`, `hlsl-specs#180`, `#5859` (closed, "[SPIR-V] template specialization"),
`#6677` (discussed above), `#8079` (the fix, discussed above), and an external
`Devsh-Graphics-Programming/Nabla-Examples-and-Tests#224`. No unexpected cross-reference from
this triage session itself.

## Assessment

- Status: **changed-behavior**. The reported crash is fixed (`v1.7.2308`), but the underlying
  "OOL definition of a class-template static member" defect family is still broken on
  `main-debug` for both the originally-reported partial-specialization case (now a diagnosed
  E_FAIL instead of a crash) and, more broadly, for the standards-correct spelling of
  full/explicit-specialization and even primary-template OOL definitions (a distinct, still
  fully live bogus-diagnostic bug, independently corroborated on issue #6677 and by direct
  source reading of the `SpirvEmitter.cpp` guard added in PR #8079).
- Confidence: **high** — precise bisections for both predicates, a source-level fix
  attribution that exactly predicts the empirical scope of what the fix does and does not
  cover, and multiple independent corroborating controls (non-template baseline, CE,
  `#6677`, Clang's own diagnostic for the illegal-`static` construct).
- Suggested action: **still-valid-keep-open** — real compiler defects remain: (1) partial
  specialization OOL member definitions never compile; (2) full/explicit-specialization and
  primary-template OOL member definitions only compile via an illegal, non-conforming
  `static` duplication, and are otherwise misdiagnosed as an in-class field; (3) that illegal
  `static` duplication is never itself diagnosed, unlike Clang. Note `#6677`'s narrower ask
  (fully generic, C++11-style deduced OOL initializers) was correctly closed `NOT_PLANNED` as
  a template-model feature gap, not a bug — that specific ask is out of scope here.
