> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5105](https://github.com/microsoft/DirectXShaderCompiler/issues/5105).

Still an open gap on `main` (built locally at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`dxc --version`: `1.9.0.5465 (triage, 7665270b9)`). With an explicitly-registered but unreferenced
resource (`Texture2D unusedTex : register(t1);`, never read by the entry point), the disassembly's
`Resource Bindings` table only lists the resources that are actually used:

```
; Name                                 Type  Format         Dim      ID      HLSL Bind  Count
; ------------------------------ ---------- ------- ----------- ------- -------------- ------
; samp                              sampler      NA          NA      S0             s0     1
; usedTex                           texture     f32          2d      T0             t0     1
```

`-O0`, tried as suggested in the report, does not change this. This has been the case in every
stable release checked back to v1.4.1907 (2019) — it isn't a regression, the option has simply
never existed.

There's now active, in-progress work in this exact area, surfaced by this issue's own
cross-reference timeline:

- [#7643](https://github.com/microsoft/DirectXShaderCompiler/pull/7643) — open, unmerged —
  `-fhlsl-unused-resource-bindings=reserve-all`, for consistent binding assignment.
- [#7734](https://github.com/microsoft/DirectXShaderCompiler/pull/7734) — open, unmerged,
  explicitly titled step 2/2 for this issue — `-keep-all-resources`, to keep unused resources
  visible in reflection without emitting `createHandle` for them.

Neither flag is recognised by the current build (`Unknown argument: '-keep-all-resources'` /
`Unknown argument: '-fhlsl-unused-resource-bindings=reserve-all'`), so the request is not yet
satisfied, but it does look like it's being actively worked rather than sitting idle. Compiler
Explorer corroborates the current-`main` state on the DXC trunk build:
https://godbolt.org/z/snfK4ebdG

Suggest keeping this open (`still-valid-keep-open`) and adding the `reflection` label, since the
whole ask is about reflection data stability.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
