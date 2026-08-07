> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1877](https://github.com/microsoft/DirectXShaderCompiler/issues/1877).

**Still reproduces** on `main` (1.9.0.15422, eff900d5), and on every release from v1.4.1907
to v1.9.2607.

Current DXIL contains no `fptosi` conversion:

```
%3 = call %dx.types.CBufRet.i32 @dx.op.cbufferLoadLegacy.i32(...)
%4 = extractvalue %dx.types.CBufRet.i32 %3, 0
call void @dx.op.bufferStore.i32(..., i32 %4, ...)
```

`cbufferLoadLegacy.**i32**` reads the float's bit pattern as an integer; the value is never
treated as a float.

`RWStructuredBuffer` remains a control: the identical cast emits
`%5 = fptosi float %4 to i32`. FXC still emits `ftoi r0.y, cb0[0].x`.

Repro with an FXC pane: https://godbolt.org/z/az56sPvs7

No diagnostic is emitted, and the module passes validation.

Suggested labels: `correctness`, `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
