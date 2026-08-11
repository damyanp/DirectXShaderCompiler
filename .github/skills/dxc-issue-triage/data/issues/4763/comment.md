> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4763](https://github.com/microsoft/DirectXShaderCompiler/issues/4763).

Still reproduces on `main` (`13730886e`) and all 20 stable releases from
v1.4.1907 through v1.9.2607. The original offsets and sizes are still exact:

```text
;           uint myInt;                               ; Offset:   12
;   } __cbModelData2;                                 ; Offset:    0 Size:    16
;           uint myInt;                               ; Offset:   64
;   } __cbModelData3;                                 ; Offset:    0 Size:    68
```

Exit 0, no diagnostic. `dxv` on the container returns `Validation succeeded.`, so nothing
downstream catches it either.

Compiler Explorer, four panes on one source — `fxc_10_0_19041 /T ps_5_0`, `dxc_1_6_2112`,
`dxc_trunk`, and `hlsl_clang_trunk -fsyntax-only`: <https://godbolt.org/z/q9vnhdroE>

The report's two asks resolve differently. The missing diagnostic reflects a
deliberate compatibility decision: commit
[`2b4f3e4`](https://github.com/microsoft/DirectXShaderCompiler/commit/2b4f3e4801fa602322111f0a28357a400b4a6ab5)
made scalar resources in cbuffers legal and retained an error only for view
arrays. That array control is diagnosed on every release:
`error: object types not supported in cbuffer/tbuffer view arrays.` Whether
scalar resources should instead be rejected remains a language decision tracked
by [hlsl-specs#225](https://github.com/microsoft/hlsl-specs/issues/225).

The layout is a concrete bug. FXC is also silent, but gives every cbuffer
`Size: 4` with `myInt` at offset 0. DXC's
`CGMSHLSLRuntime::AddTypeAnnotation` condition at `CGHLSLMS.cpp:1282`
excludes `StructuredBuffer<T>` from the zero-size resource rule and charges
`sizeof(T)`.

`Buffer<T>` had the same bug until
[`e6ba792`](https://github.com/microsoft/DirectXShaderCompiler/commit/e6ba792e2);
the measured transition is v1.6.2104 to v1.6.2106, while
`StructuredBuffer<T>` remains wrong.

Suggested labels: `bug`, `correctness` (a host writing at the FXC-derived offsets writes to
the wrong place), `diagnostic`. Keeping `fxc-disagrees`, which the layout comparison
justifies directly.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
