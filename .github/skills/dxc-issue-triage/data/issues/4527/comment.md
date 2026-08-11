> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4527](https://github.com/microsoft/DirectXShaderCompiler/issues/4527).

The underlying defect is still present, but the issue body's statement that
the shader “compiles successfully with no errors” no longer matches stock DXC
behaviour. `main` (1.9.0.5433, `13730886e`) rejects the attached file and
writes no object:

```
error: validation errors

error: External declaration '\01?kValues@?1??GetTestValue@MyClass@@QAA?AV?$vector@M$02@@I@Z@4QBV3@B' is unused.
error: Vector type '<3 x float>' is not allowed.
repro.hlsl:93:16: error: Instructions must be of an allowed type.
note: at '%6 = extractelement <3 x float> %5, i64 0' in block '#0' of function 'mainPS'.
Validation failed.
```

The attachment reproduces from v1.5.2010 through v1.9.2607. v1.4.1907 cannot
parse its unused mesh entry point, but a mesh-free restatement produces the
same validation failure there. The pixel and mesh entry points fail alike,
and all three workarounds in the report still compile.

The static local is serialized as a `linkonce_odr` global:

```llvm
@"\01?kValues@..." = linkonce_odr constant [3 x <3 x float>] ...
```

`dxilutil::IsStaticGlobal()` requires `InternalLinkage`
(`lib/DXIL/DxilUtil.cpp:114`), so `LowerTypePass` skips this global and never
flattens the `<3 x float>` element type. The global-scope control instead
reaches the container as `internal constant [9 x float]`.

`-Vd` is the only tested configuration that emits a container; it is unsigned
and standalone `dxv` rejects its DXIL. The issue does not record the original
command line, so the configuration that produced the reported object cannot
be recovered.

Compiler Explorer: <https://godbolt.org/z/oYrbGzGq3>. Suggested label: `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
