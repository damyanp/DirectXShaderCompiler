# Issue 4722 — `column_major` and `row_major` don't apply correctly to template-dependent types

**Verdict: reproduces**, on every DXC release that can compile the construct at all, and on
today's `main`.

Ground truth: `<repo>/build/Debug/bin/dxc.exe` at commit `13730886e6a9019e4e0823746470f3ab75341d6b`,
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433)`. Command: `dxc -T ps_6_0 -E main -HV 2021 repro.hlsl`
(`cmd.txt`).

---

## 1. What was tested, and the one correction to `expected.md`

`expected.md` was written before any compiler ran. It predicted a single, purely silent
defect: an orientation qualifier on a template-dependent matrix is dropped without a
diagnostic. **That prediction was half right, and the half it got wrong matters.**

The issue in fact has **two distinct faces**, and which one you meet depends on *how* the
orientation is requested:

| how the orientation is requested | what happens on a template-dependent matrix | what happens without the template |
|---|---|---|
| `#pragma pack_matrix(row_major)` | **silently dropped** — compiles, emits the default | applied correctly |
| `row_major` on a template **argument** (`S<row_major float4x4>`) | **silently dropped** | n/a |
| `row_major` written directly on the member | **hard error**, at template *definition* time | applied correctly |
| `-Zpr` on the command line | **applied correctly** | applied correctly |

The third row is the issue's own test case, and the author marked those lines as *expected to
compile*. They do not. So the report's headline ("don't apply correctly") is right, but the
mechanism is not uniformly a silent drop — one spelling miscompiles and another is rejected
outright. `expected.md` is left exactly as written; this is the divergence.

The fourth row is the sharpest part of the finding and is discussed in §5.

---

## 2. The decisive evidence — byte-identity (`manual-case-identity.txt`)

Rather than read an orientation out of one output and argue about whether it is the right one,
compile the `row_major` spelling and the `column_major` spelling of the *same* shader and
compare the emitted containers. If they are identical, one of the two requests was provably
ignored — and that conclusion does not depend on knowing which layout is correct.

```
case                    asked for     emitted       sha256 of the DXIL container
----------------------  ------------  ------------  ----------------------------------------
template row_major      row-major     column_major  82f4fbd7…7eb640f
template column_major   column-major  column_major  82f4fbd7…7eb640f
template (no request)   default       column_major  82f4fbd7…7eb640f
concrete row_major      row-major     row_major     eed9092e…0ee0f102
concrete column_major   column-major  column_major  8d92eb6e…5855ffe7
concrete (no request)   default       column_major  8d92eb6e…5855ffe7
```

Three readings, in increasing strength:

1. **template row_major == template column_major.** Two opposite requests, one output. One of
   them is being ignored.
2. **template row_major == template (no request).** The `row_major` request had *no effect at
   all* — the member landed on the default. This says *which* one is ignored.
3. **concrete row_major != concrete column_major** (the instrument self-test). Matrix
   orientation demonstrably works in this compiler, in this cbuffer, on this matrix type. The
   only thing removed between the working and broken case is the template. Without this row,
   the first two would be equally consistent with "orientation never works here".

The fourth row of the table also **measures** the default (`concrete column_major == concrete
default`) instead of assuming it: the default is column-major, so the template case is landing
on the default rather than on some third behaviour.

Human-readable form of the same thing — the two members side by side in one cbuffer, under one
pragma, differing only by the template (`variant-godbolt-source-main-debug.txt`):

```
;   struct hostlayout.CB
;       struct hostlayout.struct.ThroughTemplate<float, 4, 4>
;           column_major float4x4 M;                  ; Offset:    0
;       } A;
;       struct hostlayout.struct.Directly
;           row_major float4x4 M;                     ; Offset:   64
;       } B;
```

This is not cosmetic. The two forms load different cbuffer components into the `mul`, so the
shader computes a different result at runtime.

---

## 3. Predicates and controls

Three predicates, each with at least one control that is required **not** to match. Every
`--expect` declaration held.

`match.json` — the silent face. Deliberately a **presence** predicate: it requires
`column_major float4x4 M;` in the layout block *and* `!dx.entryPoints`. The obvious
formulation ("`row_major` is absent") would be satisfied for free by any compiler that failed
to produce output at all; `!dx.entryPoints` only exists after successful codegen, so a failed
compile can never score as a repro.

| label | shader | expect | result |
|---|---|---|---|
| *(primary)* | `repro.hlsl` | match | **repro** |
| `template-column-major` | same, `column_major` | match | repro — identity control |
| `nontemplate-row-major` | template removed | **no-match** | **no-repro** ✓ |
| `nontemplate-column-major` | template removed | match | repro |
| `nontemplate-default` | no pragma | match | repro — measures the default |
| `template-default` | no pragma | match | repro |
| `template-default-zpr` | `-Zpr` | **no-match** | **no-repro** ✓ |
| `nontemplate-default-zpr` | `-Zpr` | **no-match** | **no-repro** ✓ |
| `template-argument` | `Matrices<row_major float4x4>` | match | repro |
| `feature-templates` | templates, no matrix | **no-match** | **no-repro** ✓ |

`control-feature-templates.hlsl` is the anti-vacuity control in the other direction: an HLSL
2021 template that has nothing to do with matrices must not score as a repro, or the predicate
would just be detecting "templates compiled".

`match-rejects-qualifier.json` — the loud face. Requires the diagnostic text *and* the source
echo of the offending declaration.

| label | shader | expect | result |
|---|---|---|---|
| `explicit-qualifier` | `row_major matrix<T,X,Y> M;` in a template | match | **repro** |
| `explicit-qualifier-nontemplate` | the template removed | **no-match** | **no-repro** ✓ |
| `dependent-matrix-arg` | `row_major T M;`, instantiated `T = float4x4` | match | repro |

`dependent-matrix-arg` is the interesting one: `T` *is* a matrix at instantiation, and the
declaration is still rejected. The check is testing **dependence**, not matrix-ness.

`match-verify.json` — the author's own test case, run verbatim under `-verify`
(ground-truth-only; its wording is not claimed portable across releases).

---

## 4. The issue's ask B (the missing diagnostic) does **not** reproduce

The filed test case expects four diagnostics. Running it verbatim
(`dxc -T ps_6_0 -E fn -HV 2021 -verify issue-testcase.hlsl`) produces exactly:

```
error: 'error' diagnostics seen but not expected:
  Line 19: 'row_major' can only be used with a matrix type
  Line 20: 'column_major' can only be used with a matrix type
```

and **no** "expected but not seen". So all four `expected-error` directives fire — the
diagnostics the author wanted are present. What the test case actually exposes is the
*opposite* problem: two **extra** errors on lines 19–20, which are the `row_major matrix<T,X,Y>`
member declarations the author expected to compile silently.

`control-verify-nontemplate.hlsl` is the control: the same four members with the template
removed, exit 0 and empty output — the diagnostics land on exactly the right two members
there.

Two defects in the filed test case, recorded in `expected.md` before it was run: both structs
declare the member name `RowMajor` twice (the second is evidently meant to be `ColumnMajor`),
and `-fsyntax-only` cannot observe the headline defect at all since it has no diagnostic.

---

## 5. Root cause, from source

Both faces are the same bug in two places: **the orientation machinery asks "is this a matrix?"
while the type is still dependent, and a dependent type is never a matrix.**

`hlsl::IsHLSLMatType` (`tools/clang/lib/AST/HlslTypes.cpp:74`) delegates to `getAttr<HLSLMatrixAttr>`
(`HlslTypes.cpp:56`), which canonicalises and then requires `type->getAs<RecordType>()`. A
dependent `matrix<T, X, Y>` canonicalises to a dependent `TemplateSpecializationType`, not a
`RecordType`, so it returns null → **false**.

*Silent face.* `#pragma pack_matrix` is applied in `GetTypeForDeclarator`
(`tools/clang/lib/Sema/SemaType.cpp:4350–4363`), guarded by
`hlsl::IsHLSLMatType(T) && !hlsl::HasHLSLMatOrientation(T)`. For a dependent member that guard
is false, so the pragma's orientation is never attached to the type. Instantiation later
substitutes a concrete matrix, but the pragma is file-position state on the `DeclSpec`
(`ParseDecl.cpp:3589`, `SemaAttr.cpp:269`) and is long gone by then — nothing re-consults it.
The member falls through to the codegen default.

*Loud face.* An explicitly written qualifier is checked in `SemaType.cpp:5818–5823`:

```cpp
if ((Kind == AttributeList::AT_HLSLColumnMajor || Kind == AttributeList::AT_HLSLRowMajor) &&
    !hlsl::IsMatrixType(&S, Type)) {
  S.Diag(Attr.getLoc(), diag::err_hlsl_matrix_layout_wrong_type) ...
```

Same predicate, opposite consequence: instead of skipping the attribute it rejects the
declaration, at template *definition* time, before anyone knows what `T` is. This is
`err_hlsl_matrix_layout_wrong_type` (`DiagnosticSemaKinds.td:7828`) and it is what the
`explicit-qualifier` and `dependent-matrix-arg` captures show.

**Why `-Zpr` behaves differently, and why that is the strongest hint for a fixer.** The comment
directly above the pragma-application site says so outright:

> *"For codegen, it'd be nice to annotate everything here, but it causes error messages to have
> pack orientation added to types, so we handle it through the codegen option's default packing
> orientation flag."* — `SemaType.cpp:4353–4357`

`-Zpr` takes the codegen-default route and never asks Sema whether the type is a matrix, so it
reaches template-dependent members correctly (measured: `template-default-zpr` → no-repro).
`#pragma pack_matrix` takes the type-annotation route and does not. Two mechanisms documented
as equivalent, diverging on exactly this input. That divergence is measured, not inferred.

This is consistent with, and slightly sharper than, the author's own 2024-08-17 comment
("attributes getting dropped during type canonicalization"): the attribute is not dropped
*during* canonicalization so much as **never attached**, because the attach-time test uses a
canonicalizing matrix-ness query on a type that is not yet canonicalizable.

---

## 6. History (`manual-case-release-history.txt`, `bisect --linear`)

Every one of the **16 stable releases that can compile the construct** reproduces both faces,
back to `v1.6.2112` (2021-12-08) — the first release with HLSL 2021 templates. Today's `main`
reproduces. There is no regression window: this has never worked.

Four older stable releases (`v1.4.1907`, `v1.5.2010`, `v1.6.2104`, `v1.6.2106`) reject the repro
with `dxc failed : Unknown HLSL version: 2021` before reaching the code under test. They are
recorded as **invalid probes**, not as clean results — the construct did not exist for them to
get wrong. Five prereleases in the catalog are excluded by policy; the issue names none.

Each release ran **its own** `dxc.exe` over all six shaders, so every row carries its own
instrument self-test: the concrete `row_major` / `column_major` pair differs on every release
that compiled anything. A release where that pair had come out identical would have been an
instrument failure, not a stronger result.

---

## 7. Compiler Explorer

<https://godbolt.org/z/16hP1TjKK> — `dxc_1_6_2112` and `dxc_trunk`, both
`-T ps_6_0 -E main -HV 2021`, on `godbolt-source.hlsl`. The source puts the template-dependent
and the concrete member in **one cbuffer under one pragma**, so the Buffer Definitions block
shows `column_major` above `row_major` in adjacent lines — the bug is visible without running
anything or comparing two panes. The oldest available and the newest DXC agree, which is the
"never worked" result in one screen.

A third `hlsl_clang_trunk` pane was tried and dropped: it compiles the shader cleanly but emits
no layout annotations at all, so the evidence is simply invisible there and the pane could not
be interpreted either way. Recorded rather than shipped.

---

## 8. Assessment

Real, current, and unfixed. The severity is that the silent face produces **wrong results with
no diagnostic**: a shader that says `#pragma pack_matrix(row_major)` and then wraps its matrices
in any template gets column-major layout, and nothing anywhere reports it. Templates plus
`pack_matrix` is not an exotic combination — a matrix wrapped in a generic container is close to
the point of having templates.

The loud face is arguably worse for a user's day, since `row_major matrix<T,X,Y>` — the
spelling anyone would try first, and the one the issue's test case uses — is simply rejected,
with a message that is untrue for the code as written.

Keep open. The report is accurate about *what* is wrong; the entry above is the material that
was missing: which spellings fail which way, that `-Zpr` is the one that works and why, and that
the test case as filed does not compile.

`text_stale` is **not** claimed. The title is accurate and the maintainer's diagnostic comment
still points at the right area. The refinement in §5 sharpens it rather than contradicting it.
