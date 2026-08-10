> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4486](https://github.com/microsoft/DirectXShaderCompiler/issues/4486).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **every stable release that has a
SPIR-V backend** — all 19 from v1.5.2010 to v1.9.2607, with no clean release in between.
v1.4.1907, the oldest release here with a usable `dxc`, cannot answer at all: it exits 1 with
`dxc failed : SPIR-V CodeGen not available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.`,
on the trivial control as much as on the repro. So "always" means as far back as it is
possible to check, not back to the first release.

Compiler Explorer: <https://godbolt.org/z/dYWfKGE1o> (`-T ps_6_0 -E PS_bright_pass -spirv`,
with the DXIL output beside it).

```
               OpLoopMerge %114 %112 Unroll
               OpBranchConditional %113 %115 %114
...
               OpLoopMerge %122 %119 Unroll
               OpBranchConditional %121 %123 %122
```

Both `[unroll]` loops survive as real loops with back-edges; the `Unroll` loop control is
emitted and then not acted on. One `OpFOrdGreaterThan` remains where the unrolled nest would
have six. The workaround from the thread produces zero `OpLoopMerge` on the same builds, and
the sibling `[unroll] for (i < 4)` sampling loop in the same function *is* unrolled — so this
is not "`-spirv` ignores `[unroll]`".

s-perron's 2023-03-10 explanation holds up against the source
(`external/SPIRV-Tools/source/opt/loop_unroller.cpp:1113`, `// Can only unroll inner loops.`),
with one refinement worth recording: **nesting alone is not the blocker.** The same nest with
the inner bound changed from `4 - j - 1` to a constant unrolls completely — 0 `OpLoopMerge`, 9
comparisons, no branches. The failing ingredient is the inner trip count depending on the
outer induction variable: the inner loop's iteration count is not computable, so it is never
removed, so the outer never becomes inner-most either, and neither level is ever eligible.

A separate diagnostic gap appeared while checking pow2clk's DXIL claim, which is correct:
the repro fully unrolls to DXIL. Take the same nest with a uniform rather than literal outer
bound, so no `[unroll]` here can be honoured:

```
$ dxc -T ps_6_0 -E PS_bright_pass control-nonconst-nested.hlsl
control-nonconst-nested.hlsl:24:27: error: Could not unroll loop. Loop bound could not be deduced at compile time. Use [unroll(n)] to give an explicit count. Use '-HV 2016' to treat this as warning.

$ dxc -T ps_6_0 -E PS_bright_pass -spirv control-nonconst-nested.hlsl
[exit] 0                      # empty stderr, two surviving OpLoopMerge
```

An `[unroll]` that provably cannot be honoured is a hard error on one back end and silent on
the other.

This verifies compiler output only. I did not test the reported Mali/Adreno timing,
divergence or malioc results.

Suggested labels: **`performance`** (the generated SPIR-V retains runtime loops) and
**`up-for-grabs`** (recording the 2024-08-23 invitation, so someone looking for work can find
it). Whether `wont-fix` or `external` also apply is a call for a maintainer — the change would
land in SPIRV-Tools rather than in DXC's emitter.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
