> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5292](https://github.com/microsoft/DirectXShaderCompiler/issues/5292).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`dxcompiler.dll` version `1.9.0.5465 (triage, 7665270b9)`).

Running the exact repro and command from the issue through
`IDxcRewriter2::RewriteWithOptions` (the API `dxr.exe -remove-unused-functions
-remove-unused-globals -E ps_main` drives) produces:

```
typedef PSOutput PSPointOutput;
float4 ps_main(VSOutput psIn) {
  return float4(0.F, 0.F, 0.F, 1.F);
}
```

`struct PSOutput {};` is removed, `typedef PSOutput PSPointOutput;` is left
dangling — exactly as reported. Feeding that output back into `dxc -T ps_6_0
-E ps_main` confirms the claimed downstream compile error:

```
error: unknown type name 'PSOutput'
typedef PSOutput PSPointOutput;
        ^
```

**Root cause:** `CollectRewriteHelper` in
`tools/clang/tools/libclang/dxcrewriteunused.cpp` only tracks `VarDecl`s
(`unusedGlobals`), `FunctionDecl`s (`unusedFunctions`) and `TagDecl`s
(`unusedTypes`) for removal. A `TypedefDecl` is never added to any of those
sets, so it can never be considered for removal — independent of whether the
type it names survives.

**History:** reproduces on every stable release able to run this probe,
from v1.5.2010 (2020-10-22) through v1.9.2607, plus current `main`.

Related observation: the rewriter also drops `struct VSOutput {};` in every run
here, even though it's `ps_main`'s parameter type. `VarReferenceVisitor` does
not mark signature types as used unless something in the body references them.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
