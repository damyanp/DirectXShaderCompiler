> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4540](https://github.com/microsoft/DirectXShaderCompiler/issues/4540).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 20 stable
releases from v1.4.1907 to v1.9.2607.

```llvm
; static groupshared uint storeTile;
@storeTile = internal unnamed_addr addrspace(3) global i1 false
  store i1 false, i1 addrspace(3)* @storeTile, align 4

; groupshared uint storeTile;
@"\01?storeTile@@3IA" = external addrspace(3) global i32, align 4
  store i32 0, i32 addrspace(3)* @"\01?storeTile@@3IA", align 4, !tbaa !12
```

`docs/DXIL.rst` defines `i32`, `f32` and `f64` memory accesses for
groupshared memory; `i1` is listed only for thread-local memory.

The validator/spec contradiction is also reproducible. Across 22 builds
(20 stable releases, v1.5.2003 and `main`), validation accepts the `i1`
groupshared module on 22/22. A 64 KB groupshared control is rejected on 22/22;
current `main` reports:

```
control-tgsm-overflow.hlsl:13:2: error: Total Thread Group Shared Memory used by 'main' is 65536, exceeding maximum: 32768.
```

`dxopt` measurements isolate the change to `-globalopt`: the front-end module
and a no-pass control contain `i32`; `-globalopt` alone and the full pipeline
produce `i1`; removing `-globalopt` from the full pipeline preserves `i32`.
This matches `TryToShrinkGlobalToBoolean`
(`lib/Transforms/IPO/GlobalOpt.cpp:1595`).

Compiler Explorer: <https://godbolt.org/z/7Kexss5x8>. The reported GPU
behaviour was not tested here. The existing `bug`, `correctness` and
`validation` labels remain appropriate.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
