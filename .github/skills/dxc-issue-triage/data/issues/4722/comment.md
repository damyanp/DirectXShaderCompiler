> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4722](https://github.com/microsoft/DirectXShaderCompiler/issues/4722).

Still reproduces on `main` (`dxcompiler.dll 1.9.0.5433`, `13730886e`) and all
16 stable releases that can compile HLSL 2021 templates, from **v1.6.2112**.
The four older releases are unmeasurable, not clean.

There are two failures, depending on how orientation is requested.

**1. `#pragma pack_matrix` is silently dropped.** Both members below are 4x4 float matrices in
one cbuffer under one pragma; only the non-template one gets the requested layout:

```
;   struct hostlayout.CB
;       struct hostlayout.struct.ThroughTemplate<float, 4, 4>
;           column_major float4x4 M;                  ; Offset:    0
;       } A;
;       struct hostlayout.struct.Directly
;           row_major float4x4 M;                     ; Offset:   64
;       } B;
```

[Compiler Explorer](https://godbolt.org/z/16hP1TjKK) (dxc 1.6.2112 and trunk agree). Compiling
the template's `row_major`, `column_major`, and no-pragma forms produces
byte-identical containers. The same concrete pair differs, so the instrument
can detect orientation and the template is the discriminating variable.

**2. The test case in the report doesn't compile.** The two lines expected to succeed are
rejected:

```text
repro-explicit-qualifier.hlsl:18:3: error: 'row_major' can only be used with a matrix type
  row_major matrix<T, X, Y> RowMajor;
```

This fires at template *definition* time, so it also rejects `row_major T M;` when `T` is
instantiated as `float4x4` — it is testing dependence, not matrix-ness. Conversely, the four
`expected-error` directives in the filed test all fire, so its
missing-diagnostic half does not reproduce.

**`-Zpr` works correctly on template-dependent members.** That may be the useful lead: per the
comment at `SemaType.cpp:4353`, the flag is applied through the codegen default while
`#pragma pack_matrix` is applied by annotating the type in `GetTypeForDeclarator`, guarded by
`hlsl::IsHLSLMatType`. That guard canonicalises and asks for a `RecordType`
(`HlslTypes.cpp:56`), which a dependent `matrix<T,X,Y>` is not — so the pragma never attaches.
`SemaType.cpp:5820` uses the same matrix-ness test to *reject* an explicit qualifier, which is
failure 2. One predicate, two consequences.

Suggested labels: **correctness** (silently wrong layout) and **type-system**
(the parse-time matrix test on a dependent type).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
