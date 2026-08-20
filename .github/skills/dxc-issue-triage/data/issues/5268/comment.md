> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5268](https://github.com/microsoft/DirectXShaderCompiler/issues/5268).

Still reproduces on `main` (build at `89e2f98e2`, `dxr.exe`). Running the repro exactly as
filed:

```
dxr -E VSMain -remove-unused-globals test.hlsl
```

drops the `POINT_SIZE` declaration but keeps `POINT_SIZE_3`, whose initializer still references
it. Recompiling the rewritten output fails:

```
test.hlsl:1:60: error: use of undeclared identifier 'POINT_SIZE'; did you mean 'POINT_SIZE_3'?
static const float3 POINT_SIZE_3 = float3(1.F, 1.F, 1.F) * POINT_SIZE;
                                                           ^~~~~~~~~~
```

**Root cause:** `VarReferenceVisitor::VisitDeclRefExpr` in
`tools/clang/tools/libclang/dxcrewriteunused.cpp` marks a kept global's initializer references
as used only when that initializer is exactly an `InitListExpr`, `ImplicitCastExpr`, or
`DeclRefExpr`. `POINT_SIZE_3`'s initializer, `float3(1,1,1) * POINT_SIZE`, is a binary/operator
expression — none of those three forms — so the visitor never walks into it and the reference
to `POINT_SIZE` is never discovered. This isn't specific to multiplication: any compound
initializer (vector construction, arithmetic, a function call) on a kept global can hide a
transitive reference to another global the same way.

**History:** reproduces identically on every stable release that can run this flag at all —
v1.5.2010 through the current v1.9.2607 — as well as `main`. v1.4.1907's `dxr.exe` can't be used
as a control here: `-remove-unused-globals` fails there with a generic
`Compilation failed - error code 0x80070057` on any input, including a known-good existing
rewriter test, so that release is excluded as unprobeable rather than as evidence of a fix.

No Compiler Explorer link: this is a `dxr.exe`-only rewriter defect, and `dxc.exe` itself
rejects `-remove-unused-globals` (`Unknown argument`), so no CE pane can exercise it.

Suggest keeping current labels (`bug`, `rewriter`) — no changes needed there.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
