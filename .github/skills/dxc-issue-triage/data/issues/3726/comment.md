> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3726](https://github.com/microsoft/DirectXShaderCompiler/issues/3726).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`) and all 20 measured
releases from v1.4.1907 through v1.9.2607.

Compiler Explorer: **https://godbolt.org/z/77EjzsnP9** (a compute restatement
verified against the as-filed pixel-shader repro).

The front end remains silent; DXIL lowering performs the rejection:

```console
$ dxc -T ps_6_0 -E main repro.hlsl
error: exported library functions cannot have resource parameters or return value. Value: ?x0@@3V?$Texture2D@V?$vector@M$03@@@@A
repro.hlsl:15:10: error: local resource not guaranteed to map to unique global resource.
    a0 = r0;
         ^

$ dxc -T ps_6_0 -E main -fcgl repro.hlsl
# exit 0, empty stderr
```

Both messages come from
[`DxilCondenseResources.cpp`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/lib/HLSL/DxilCondenseResources.cpp#L697-L702),
via `LegalizeResourceUseHelper` in `DxilLowerCreateHandleForLib`. The first is
a catch-all fallback; its source comment says “Most likely storing to output
parameter,” while the diagnostic mentions library functions.

`-spirv` exits 0 without a diagnostic on all 19 SPIR-V-capable measured
releases. Its module binds `x0`/`x1`/`x2`, the assignment targets, while
`r0`/`r1`/`r2` do not appear. Because this issue asks for the as-filed source
to be rejected, that is evidence of acceptance and lowering shape, not a
miscompile claim. Clang trunk also accepts the construct, but lowers through
`r0`.

There is a re-checking trap:

| `x0`/`x1`/`x2` form | DXIL | SPIR-V |
| --- | --- | --- |
| global, as filed | lowering error | exit 0; binds `x0`/`x1`/`x2` |
| `static`, per the 2024 comment | exit 0; binds `r0`/`r1`/`r2` | exit 0; resource operands become `OpUndef` |
| function-local | exit 0 | exit 0 |

Applying the standing “should be static” correction therefore makes the DXIL
half appear fixed, while the as-filed bound-global form still reproduces.
Scoping any Sema rule across these forms is a language-design decision.

Suggested labels: `diagnostic` and `check-in-clang`. I am not proposing
`correctness`, because the as-filed input is expected to be rejected, nor
re-adding `spirv`, which was deliberately removed during the 2024 reframing.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
