> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5823](https://github.com/microsoft/DirectXShaderCompiler/issues/5823).

Tested against `main` (`1.9.0.5465`, `89e2f98e2`).

The original SIGSEGV is fixed — since `v1.7.2308` (2023-08-14), this exact repro no longer
crashes. It now exits `0x80004005` with a diagnosed error instead:

```
repro.hlsl:12:1: error: casting to type 'void' unimplemented
```

That fix is **PR #8079**, which stops the SPIR-V backend from emitting a variable for the
un-instantiated template-declaration `VarDecl` (detected via
`CXXRecordDecl::getDescribedClassTemplate()`). That guard only matches a **primary**
(non-specialized) template's declaration context — it does not match a
`ClassTemplatePartialSpecializationDecl`, so the original repro's partial-specialization
member (`GaussLegendreValues<2, float_t>::wi`) still falls through to the same
"casting to type 'void' unimplemented" codepath as before, just without crashing. Bisecting
the crash-only signature gives `fixed-in v1.7.2308`; bisecting "crash or this diagnosed
text" gives `always-repro'd` across every probeable release `v1.7.2207`..`v1.9.2607` —
this input has never successfully compiled.

That also explains the December retitle and the two February complaints, which are a second,
related but distinct bug. Testing the full matrix on `main-debug`:

| Template kind | OOL spelling | Result |
|---|---|---|
| Primary template or full/explicit specialization | illegal duplicated `static` | compiles clean |
| Primary template or full/explicit specialization | correct (single `const`) | `'const' is not a valid modifier for a field` |
| Partial specialization | either spelling | `casting to type 'void' unimplemented` |
| Non-template struct | illegal duplicated `static` | compiles clean, **no diagnostic at all** |

So for a full/explicit specialization or a plain (non-specialized) template, DXC's parser
keys off the presence of the (illegal) `static` token to recognize an OOL specialization
definition; drop it — the standards-correct spelling — and it's misparsed as a new in-class
field and rejected. This matches what `devshgraphicsprogramming` already reported on **#6677**
(2025-12-10, `'const' is not a valid modifier for a field`), where they asked whether to track
it here — the same defect. `#6677`'s narrower ask
(fully generic C++11-style deduced OOL initializers) was correctly closed `NOT_PLANNED` per
`llvm-beanz`'s explanation there (HLSL templates are intentionally C++98-shaped); that part
is a language feature gap, not a bug. But the bogus `'const'` diagnostic reproduces even for
a **full/explicit** specialization, where no deduction is involved at all, so it isn't
covered by that rationale.

And separately, DXC really does silently accept the illegal duplicated `static` — confirmed
on a plain non-template struct with no diagnostic and the constant genuinely folded into
SPIR-V — matching Clang, which rejects the equivalent construct with `'static' can only be
specified inside the class definition`.

Compiler Explorer: **https://godbolt.org/z/dsK39nrKE** (`dxc_1_6_2112`, `dxc_trunk`).
`dxc_trunk` still shows the "casting to void" text for the primary repro (its Release build
lags the local ground truth, which shows the same text for this repro but the newer
`'const'`-field text on corrected-syntax variants — text is not portable across builds, but
"still fails to compile" holds either way).

Suggest keeping `bug`, `spirv`; consider adding `diagnostic` (missing diagnostic for the
illegal `static`, and the bogus `'const'` diagnostic when the syntax is corrected).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
