> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3706](https://github.com/microsoft/DirectXShaderCompiler/issues/3706).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and in all 20 bisectable releases measured
from v1.4.1907 through v1.9.2607, including v1.6.2104, which shipped two days before filing.

Repro: https://godbolt.org/z/n9YeYKT3W

`dxc -T vs_6_2 -E main` on the shader as filed exits 0, emits no diagnostic, and produces the
reported line verbatim:

```llvm
%2 = call %dx.types.ResRet.i32 @dx.op.rawBufferLoad.i32(i32 139, %dx.types.Handle %1, i32 undef, i32 0, i8 1, i32 4)  ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
```

The module passes DXIL validation and is signed.

**DXC already has the check — it is just not on by default:**

```
$ dxc -T vs_6_2 -E main repro.hlsl -Wall
repro.hlsl:10:19: warning: variable 'j' is uninitialized when used here [-Wuninitialized]
repro.hlsl:9:11: note: initialize the variable 'j' to silence this warning
```

`warn_uninit_var` is `DefaultIgnore` in `DiagnosticSemaKinds.td`; `-Wall` or
`-Wuninitialized` enables it. One caveat if that looks like the whole fix: it does
**not** fire on a partially-initialized index (`int2 j; j.x = 1;` then
`stbuf[j.y]`), which emits the same `undef` index and is silent even under `-Wall`.

Same source, other compilers:

| Compiler | Result |
| --- | --- |
| FXC (`/T vs_5_0`) | `error X4000: variable 'j' used without having been completely initialized` |
| DXC 1.6.2112 / trunk | exit 0, no diagnostic, `undef` index |
| Clang trunk (`-fsyntax-only`) | no diagnostic for `j` — it does warn on that same statement (`-Wsign-conversion`), so Sema reached the expression |

The validator rejects `undef` stored to a UAV (`Instr.UndefinedValueForUAVStore`), but
`RawBufferLoad` checks `elementOffset` and alignment, not the index. The slot matters: for a
ByteAddressBuffer, `elementOffset` on the same op must be `undef`
(`Instr.CoordinateCountForRawTypedBuf`).

The policy choice is among enabling the warning by default, adding a validator rule, or making
this a language-level error as FXC did. `microsoft/hlsl-specs#272` tracks the validator option
and cites this issue.

**Labels:** suggest adding `diagnostic` (the ask is a diagnostic, and one exists but is off),
`fxc-disagrees` (measured above) and `incorrect-code`. Not suggesting `validation` — it was
removed here deliberately in July 2024.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
