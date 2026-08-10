> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4273](https://github.com/microsoft/DirectXShaderCompiler/issues/4273).

**Still current on `main`** (`1.9.0.5433`, `13730886e`): `-remove-unused-globals`
does not remove an explicit `cbuffer` block, so this remains an open feature
request exactly as @tex3d framed it in 2022 — not a bug, and nothing has drifted
since.

Reproducing needs `dxr.exe`, not `dxc.exe`: `dxc` rejects these options outright
(`Unknown argument: '-remove-unused-globals'`), even though `dxc --help` prints a
`Rewriter Options:` section listing them. `dxr` forwards its argv straight to
`IDxcRewriter2::RewriteWithOptions`, the API in the report.

```hlsl
cbuffer cbA
{
  float4 gA;
};

cbuffer cbB
{
  float4 gB;
};

float4 gLooseUnused;
float4 gLooseUsed;

float4 vsMain(float4 pos : POSITION) : SV_Position
{
  return pos * gA + gLooseUsed;
}

float4 psMain() : SV_Target
{
  return gB;
}
```

```
dxr -E vsMain -remove-unused-globals -remove-unused-functions -extract-entry-uniforms repro.hlsl
```

```
cbuffer cbA {
  const float4 gA;
}
;
cbuffer cbB {
  const float4 gB;
}
;
const float4 gLooseUsed;
float4 vsMain(float4 pos : POSITION) : SV_Position {
  return pos * gA + gLooseUsed;
}
```

`psMain` removed, loose `gLooseUnused` removed, `cbB` — reachable only from the
removed entry point — kept. An unused member *inside* an otherwise-used block is
also kept, so the carve-out is "explicit `cbuffer` contents are never removal
candidates", not just "whole blocks survive".

**History: constant.** Driving each release's own `dxcompiler.dll` through a fixed
`dxr.exe`, the behaviour is identical from v1.5.2010 through v1.9.2607 and `main`
(19 releases). v1.4.1907 can't express the repro at all — its option table has no
`RewriteOption`/`remove-unused-globals`, and `-unchanged` already fails there with
`0x80070057` while a bare rewrite succeeds. So there's no regression here, and
nothing to bisect. That matches the code: in `dxcrewriteunused.cpp`, top-level
`VarDecl`s go into `unusedGlobals` (the set removal consumes) while `HLSLBufferDecl`s
go into a separate `cbufferDecls` list that is only traversed *"to save types for
cbuffer constant"* — they're never removal candidates.

**Implementation note:**
`tools/clang/test/HLSLFileCheck/rewriter/remove-unused-globals.hlsl` has asserted
the current behaviour since 2020 (`a408139da`) —

```
// Unused cbuffers are not removed at this time
// CHECK: cbuffer UnusedCBuffer
```

— plus a `// CHECK: float UnusedFloat;` for the unused-member case. Both `CHECK`s
have to flip, so the test will fail *because* the fix works.

On the measured DXC/SM6 path, the retained block does not consume a slot: compiling the
rewriter's own output for `vs_6_0` binds only `$Globals` at `cb0` and `cbA` at `cb1`,
reflection reports `ConstantBuffers: 2`, and `cbB` is dropped. DX11/SM5.x uses FXC and was not
tested; the source-cleanliness request @tex3d accepted still stands.

Labels look right as-is (`enhancement` + `rewriter`); no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
