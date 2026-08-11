# What "this reproduces" means — issue 4722

`column_major` and `row_major` don't apply correctly to template-dependent types
(filed 2022-10-12 by llvm-beanz, a project collaborator).

Written **before** running any compiler.

## What the issue actually claims

The body is a `clang_cc1 -HV 2021 -fsyntax-only -verify` test case, not a runnable dxc
command line. It contains a template struct and a concrete struct declaring the *same four*
members, and asserts they should behave *identically*:

```c++
template <typename T, int X, int Y>
struct Matrices {
  row_major matrix<T, X, Y> RowMajor;
  column_major matrix<T, X, Y> RowMajor;      // (sic — see "defects in the filed test case")

  row_major T NotAMatrix;        // expected-error {{'row_major' can only be used with a matrix type}}
  column_major T AlsoNotAMatrix; // expected-error {{'column_major' can only be used with a matrix type}}
};

struct AlsoMatrices { /* the same four, with float / float4x4 spelled concretely */ };
```

The author's own follow-up comment names the mechanism: *"The problem is attributes getting
dropped during type canonicalization"* (2024-08-17), and an earlier comment adds that the
same drop affects `typedef row_major float4x4 …`. He also states the orientation attribute
"just changes how it is read from or written to device or shared memory" — so the observable
effect lives in buffer layout, not in thread-local storage.

So the report decomposes into two separately-scorable asks.

### Ask A — silent wrong code (the headline)

`row_major` / `column_major` written on a **template-dependent** matrix type
(`matrix<T, X, Y>` inside a template) is dropped. Nothing is diagnosed; the shader compiles;
the emitted DXIL describes the **default** orientation instead of the requested one.

**Reproduces if:** with the member declared `row_major`, the emitted DXIL records the matrix
as column-major (DXC's default), i.e. the requested orientation is absent from the output —
while the identical *non-template* declaration does record `row_major`.

**Decisive form of the evidence (identity control):** compile the `row_major` spelling and
the `column_major` spelling of the *same* template and compare the emitted DXIL. If the two
are **byte-identical**, one of the two qualifiers is provably being ignored, and that
conclusion does not depend on my knowing which layout is "correct". The mirror measurement on
the non-template spelling of the same construct **must differ** between the two orientations;
without that second control I cannot separate "templates break this" from "matrix orientation
never worked here at all".

**Does not reproduce if:** the template form's `row_major` and `column_major` DXIL differ from
each other and each matches its non-template counterpart.

### Ask B — missing diagnostic

`row_major T` / `column_major T`, where `T` is a template parameter later instantiated as a
non-matrix type (`float`), should produce
`'row_major' can only be used with a matrix type`, exactly as the concrete `row_major float`
does in the same test case.

**Reproduces if:** the template form compiles with no such diagnostic while the concrete form
emits it.

**Does not reproduce if:** both forms emit the diagnostic (or neither does — which would be a
different, third defect and would be reported as `changed-behavior`).

## Hazards I am committing to control for, before I see any output

- **Nothing fails.** There is no error text and no exit code to test for ask A; a predicate
  has to be written on the emitted DXIL. Exit status carries no information here, and a
  nonzero exit would *not* mean a crash (E_FAIL 0x80004005 is an ordinary diagnosed error).
- **A predicate satisfied by an absence is satisfied for free by a release that never
  compiled.** Every clause must be anchored on something only successful codegen can emit,
  and every probe must be confirmed to have produced DXIL.
- **The default orientation is a confounder.** HLSL has a default matrix orientation and
  `-Zpr` / `-Zpc` override it. I must *measure* the default on the build under test rather
  than assume it, or I will report a global default as a template-path defect.
- **Templates are HLSL 2021.** `-HV 2021` must be pinned explicitly, and releases that
  predate HLSL 2021 will reject the repro before reaching the code under test; those are
  invalid probes, not clean results.
- **Prereleases are out of scope** — the issue names no prerelease.

## Defects in the filed test case (recorded before running it)

1. Both structs declare the member name `RowMajor` **twice**; the second is evidently meant to
   be `ColumnMajor`. As written the test case cannot compile — the second declaration is a
   redefinition — so it cannot be used verbatim as a compile repro.
2. It is a `-fsyntax-only -verify` cc1 test, which exercises only ask B. Ask A (the dropped
   orientation) is invisible to `-fsyntax-only`, since it has no diagnostic; it needs codegen.

Both are recorded here so the constructed repro's deviations from the filed text are visible.
The filed text is still compiled verbatim as a captured variant.

## Repro quality

**`partial`.** The issue supplies a precise, maintainer-authored test case that pins ask B
exactly, but (a) it does not compile as written, (b) it is a cc1 `-verify` test rather than a
dxc command line, and (c) it contains no codegen case at all for ask A, which is the issue's
title. The shaders that measure ask A are agent-constructed from the issue's own wording and
from the author's comment about buffer layout.
