> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4168](https://github.com/microsoft/DirectXShaderCompiler/issues/4168).

This no longer reproduces on `main` (1.9.0.5433, `13730886e`), and it was fixed in
**v1.7.2308**.

Using the configuration from your 2022-01-23 comment — a library compiled `-T lib_6_x`, linked
to `ps_6_0`, then reflected:

```
dxc -T lib_6_x -Fo lib.dxo repro.hlsl
dxl -T ps_6_0 -E main -Fo linked.dxo lib.dxo
dxa -dumpreflection linked.dxo
```

On `main` the linked shader's cbuffer reflects both of its members:

```
  D3D12_SHADER_BUFFER_DESC: Name: CB0
        Type: D3D_CT_CBUFFER
        Size: 80
        uFlags: 0
        Num Variables: 2
```

On v1.6.2112 — the release current when you filed — the same three commands give
`Num Variables: 0`, with the cbuffer still bound and still sized `80`. So the report was
accurate.

Running the same chain across every stable release, with each release producing the container
and a fixed `dxa` reading it:

| | |
| --- | --- |
| v1.6.2106 – v1.7.2212.1 | `Num Variables: 0` |
| v1.7.2308 – v1.9.2607 | `Num Variables: 2` |

(v1.4.1907, v1.5.2010 and v1.6.2104 predate `-link` in `dxc.exe`, so they cannot run the
configuration at all. On every release, the same source compiled straight to `ps_6_0` with no
library and no link reflects both variables — that control is what makes the rows above a
statement about linking rather than about the reader.)

At v1.6.2112, the `lib_6_x` container alone reflects both variables correctly; only the linked
output loses them, localizing the loss to linking.

The fix looks like `bf015d2e1` ("Fix loss of buffer type info with libraries and linker",
#5197, 2023-05-10), which lands inside the v1.7.2212.1 → v1.7.2308 window. It adds the
`CopyTypeAnnotation(res->GetHLSLType(), …)` in `DxilLinkJob::AddGlobals` that your Problem 1
proposed, changes the SM 6.6 gating in `DxilMDHelper::EmitDxilResourceBase` for Problem 2, and
adds `preserve_cb_types.hlsl` / `preserve_sb_types.hlsl` covering this shape. That window holds
257 commits, so this is attribution by release boundary plus source content, not a build
bisect; six other commits touch the same file set, but none introduces the annotation copy.

Worth noting for coverage: `preserve_cb_types.hlsl` tests `vs_6_5`/`vs_6_6`/`vs_6_7`, not your
`ps_6_0`. `ps_6_0` measures clean on every release from v1.7.2308 onward, so it works; it just
has no regression test of its own.

Suggested action: close as fixed in v1.7.2308. Existing labels (`bug`, `reflection`,
`shader-linking`) are all correct; no change proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
