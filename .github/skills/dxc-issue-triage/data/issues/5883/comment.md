> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5883](https://github.com/microsoft/DirectXShaderCompiler/issues/5883).

Still reproduces on `main` (commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df),
self-reported version `1.9.0.5465`), and a release bisection shows it
always has: every stable release from `v1.4.1907` (2019, the oldest
release with a usable `dxc`) through `v1.9.2607` reproduces it, with no
clean release anywhere in between.

Compiling the repro's `const S a = {m};` branch still emits `m`'s
declaration-time constants into the buffer store, discarding the two
writes made to `m` beforehand:

```
call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 undef, i32 42, i32 43, i32 44, ...)
call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 16, i32 undef, i32 45, i32 46, i32 47, ...)
```

The non-`const` variant on the same shader (`S a = {m};`, no `const`)
correctly emits the mutated values `1,2,3`/`4,5,6`, confirming the
const-qualified path specifically is at fault, as the original report
describes. Compiler Explorer's oldest DXC (1.6.2112) and current `dxc_trunk`
both show the same buggy payload: https://godbolt.org/z/s7WdTna8d

@amaiorano's root-cause analysis in this thread (the `EmitVarDecl` →
`EmitHLSLConstInitListExpr` → `ScanConstInitList` path in
`CGHLSLMS.cpp`) still matches the current source — the `DeclRefExpr` branch
of `ScanConstInitList` folds a referenced local variable's own declaration
initializer via `EmitConstantInit`, without checking whether that variable
was written again between its declaration and this read. Nothing in that
code path has changed since this was filed.

Suggested label: no change — `bug`, `correctness` and `matrix-bug` all
still fit (the January 2024 follow-up shows the same defect for
struct/array of any type, not only matrix, so `matrix-bug` covers one
manifestation rather than the whole scope, but nothing here justifies
removing it).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
