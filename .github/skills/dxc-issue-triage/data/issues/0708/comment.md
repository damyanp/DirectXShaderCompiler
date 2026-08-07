> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#708](https://github.com/microsoft/DirectXShaderCompiler/issues/708).

On `main` (1.9.0.15422, `eff900d5`), `register(t1[27])` still binds at `t1` with no
diagnostic, silently discarding the `[27]`. Unchanged from v1.4.1907 (2019-07) through
v1.9.2607.

Repro: https://godbolt.org/z/MsfE6b1v8

```hlsl
Texture2D tex : register(t1[27]);
float4 main() : SV_Target { return tex.Load(int3(0, 0, 0)); }
```

```
; Name                                 Type  Format         Dim      ID      HLSL Bind  Count
; tex                               texture     f32          2d      T0             t1     1
```

`RegisterAssignment::RegisterOffset` is parsed (`ParseDecl.cpp`), stored (`HlslTypes.h`),
dumped (`DeclPrinter.cpp`, `ASTDumper.cpp`) and checked for conflicts (`SemaHLSL.cpp`), but
never read by binding assignment or codegen.

Clang trunk does not accept the syntax at all (`error: expected ')'`), so the silent-accept
behaviour is DXC's alone.

The clear defect is that DXC accepts syntax it does not implement without diagnosing it. What
it *should* do is a separate question: `register(t<n>[<offset>])` is undocumented for SRVs, so
whether the offset shifts the binding or the form should be rejected outright likely belongs
with HLSL 202x — though Clang has effectively already answered "reject".

Suggest keeping this open; a diagnostic is warranted regardless of how the semantics land.

**Labels:** suggest adding `diagnostic` and `hlsl-next`; keep `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
