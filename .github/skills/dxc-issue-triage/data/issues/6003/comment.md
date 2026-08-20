> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6003](https://github.com/microsoft/DirectXShaderCompiler/issues/6003).

Re-checked both findings against `main` at commit `89e2f98e2` (built Debug, Windows; no
Valgrind/MSan-equivalent tool available in this environment).

**The `SemaHLSL.cpp:6465` out-of-bounds/uninitialised-index read (second finding) is confirmed
still fixed**, and was already fixed before this issue was filed: `108c34654` ("Fix asan stack
use after return (#5628)", 2023-09-14) added the bounds check
`if (pIntrinsic->pArgs[0].uTemplateId < MaxIntrinsicArgs)` around exactly the quoted line.
Reading `SemaHLSL.cpp` at `89e2f98e2` directly shows the same call site still guarded (now via
`CAB(pIntrinsic->pArgs[0].uTemplateId < MaxIntrinsicArgs, 0);`), so this stays fixed on current
`main`.

**The `TypeLoc::getBeginLoc()` uninitialised-value finding (first finding) is unconfirmed, not
fixed-looking.** `clang::TypeLoc::getBeginLoc()` (`TypeLoc.cpp`) and the
`TreeTransform`/`SubstType`/`TemplateDeclInstantiator` chain above it are unmodified since
import, and no commit touching `NewSimpleAggregateType`, `GetOrCreateVectorSpecialization` or
`LookupVectorType` in `SemaHLSL.cpp` (the HLSL-side caller that synthesizes the vector
template's `FieldDecl`s) addresses source-location initialisation. Compiling the repro on the
Windows ground-truth build (both the filed SPIR-V command and a DXIL-targeted variant) exits 0
with no crash either way — consistent with Valgrind's own report, which is a conditional-jump
warning on "still reachable" memory, not a fault a plain run would show. Without a
Valgrind/MSan-capable build to re-run, this can't be confirmed fixed or refuted in this
environment.

Labels (`bug`, `sanitizer`) already fit; no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
