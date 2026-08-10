> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3189](https://github.com/microsoft/DirectXShaderCompiler/issues/3189).

**Still reproduces exactly as filed**, on `main` (1.9.0.5433, `13730886e`) and on all 19 tested
releases from v1.5.2010 to v1.9.2607. v1.4.1907 cannot answer — `SPIR-V CodeGen not available` —
so this has reproduced for as long as it is measurable. Nothing in the issue text is stale.

Repro: https://godbolt.org/z/48nqT9roE — **all three panes compile successfully; the finding is
in the `OpDecorate` lines.** The shader is the issue body's, with the "shift functionality"
reconstructed as `-fvk-auto-shift-bindings -fvk-t-shift 100 0 -fvk-s-shift 200 0`, which yields
the reported numbers. Cbuffers `a` and `b` have no `OpVariable`, `OpName` or `OpDecorate` at
all:

```
               OpDecorate %g_texture2D DescriptorSet 0
               OpDecorate %g_texture2D Binding 100
               OpDecorate %g_sampler DescriptorSet 0
               OpDecorate %g_sampler Binding 200
               OpDecorate %c DescriptorSet 0
               OpDecorate %c Binding 2
```

**It is not specific to the shift options.** With a plain `-T ps_6_0 -E mainPS -spirv` the same
shader puts `c` at `Binding 4`, after `g_texture2D` 0, `g_sampler` 1, `a` 2, `b` 3.

**The mechanism is exactly what the title says.** `decorateResourceBindings()` runs at
`SpirvEmitter.cpp:840`; the module first reaches `spirvToolsLegalize`/`spirvToolsOptimize` —
where spirv-opt's performance passes delete the unused variables — at lines 972 and 988.
`DeclResultIdMapper::decorateResourceBindings` walks `resourceVars` in declaration order and
consults nothing about liveness. At `-O0`, where no spirv-opt pass runs, `a` and `b` are still
there holding the numbers they were given:

```
               OpDecorate %a DescriptorSet 0
               OpDecorate %a Binding 0
               OpDecorate %b DescriptorSet 0
               OpDecorate %b Binding 1
               OpDecorate %c DescriptorSet 0
               OpDecorate %c Binding 2
```

`c` gets `Binding 2` either way; optimisation only deletes `a` and `b` afterwards.

@damyanp's DXIL observation checks out — the same shader without `-spirv` puts `c` at `cb0` and
omits `a`/`b` from the binding table (pane 3 of the link). Note the two are not directly
comparable: DXIL registers are per-type (`cb0`/`s0`/`t0`) whereas SPIR-V has one binding
namespace per descriptor set, which is why the shift flags are needed here at all.

@s-perron's position is that the default must not change and that the route forward is an opt-in
`spirv-opt` renumbering pass, so this is a feature request rather than a bug, and whether to add
such an option is a product decision. DXC already has a flag pointing the *opposite* way:
`-fspv-preserve-bindings` keeps `a` and `b` in the module at bindings 0 and 1, so the module
matches the numbering (`c` stays at 2 either way).

Two documentation gaps, actionable regardless of that decision. `docs/SPIR-V.rst` describes
implicit assignment as *"next available binding number ... in the declaration order"* and never
says that a resource removed by optimisation keeps its number, or that this is intentional. And
`-fspv-preserve-bindings` is not listed in the Vulkan-specific options section at all — only
`-fspv-preserve-interface` is. Both belong where the shift options are described.

**Labels:** suggest adding `enhancement` (the ask is an opt-in option, not a fix),
`up-for-grabs` (the implementation route is named and reviewers are offered) and `docs`.
No removals — `spirv` is correct.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
