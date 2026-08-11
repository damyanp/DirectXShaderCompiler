> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4549](https://github.com/microsoft/DirectXShaderCompiler/issues/4549).

Still reproduces on `main` (1.9.0.5433, `13730886e`). The filed
`ps_6_5`/`RayQuery` form is measurable from v1.6.2104; a `lib_6_3`
restatement shows the same register-class bug back to v1.4.1907.

The `u` is not merely omitted from the diagnostic; it is ignored in the
binding. With the acceleration structure at `register(u0)` and nothing at
`t0`, DXC compiles without a diagnostic and emits:

```
; opaque_as                         texture     i32         ras      T0             t0     1
```

The reported overlap appears only when that `t0` is occupied. With `-Zi`, the
caret points at the correctly declared resource:

```
repro.hlsl:13:1: error: resource depth_buffer at register 0 overlaps with resource opaque_as at register 0, space 0
Texture2D<float> depth_buffer : register(t0);
^
```

`hlsl::DiagnoseRegisterType` has no
`AR_OBJECT_ACCELERATION_STRUCT` case (`SemaHLSL.cpp:11866`), so the invalid
register class is not diagnosed. `InitFromUnusualAnnotations`
(`CGHLSLMS.cpp:3172`) keeps the number but drops the letter; allocation later
sees two SRVs at `t0`.

DXC already emits the useful diagnostic for another SRV-class resource:

```
error: invalid register specification, expected 't' binding
```

Compiler Explorer: <https://godbolt.org/z/5z1YfdTPE>. Suggested labels:
add `bug` and `incorrect-code`; keep `diagnostic`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
