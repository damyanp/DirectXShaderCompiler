> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3927](https://github.com/microsoft/DirectXShaderCompiler/issues/3927).

Still reproduces on `main` (1.9.0.5433, `13730886e`), unchanged.

The shader in the report compiles to the same four lines it did in 2021:

```
OpDecorate %Tex0 DescriptorSet 0
OpDecorate %Tex0 Binding 0
OpDecorate %SS0 DescriptorSet 0
OpDecorate %SS0 Binding 1
```

`%Tex1`/`%SS1` are gone, as reported. `%Tex0`/`%SS0` stay because the sampled value feeds the
`if` condition, and the branch is not folded even though both of its targets end in `OpKill`.

**Compiler Explorer:** https://godbolt.org/z/eqxrve7j7 — `dxc_1_6_2112` and `dxc_trunk`. The
two modules differ (the older one still evaluates `&&` eagerly), but both keep the two
bindings.

**History.** A linear scan of all 20 stable releases from v1.4.1907 to v1.9.2607 reproduces
it in the 19 that have a SPIR-V backend, i.e. everything from v1.5.2010 onward. v1.4.1907 is
not evidence either way: it answers `SPIR-V CodeGen not available` even for a trivial pixel
shader.

Two details from re-running it that may be worth having on the thread:

- The repro reproduces the reporter's module *exactly* — the disassembly quoted in the issue
  body matches this triage's v1.6.2106 capture (`dxc_2021_07_01`) line for line, all 64 lines.
- Compiled with `-O0`, all four resources keep bindings. So every elimination visible here is
  spirv-opt's, none of it the SPIR-V emitter's — consistent with the 2024-08-22 comment
  placing a fix in spirv-opt. `SpirvEmitter::spirvToolsOptimize` registers
  `RegisterPerformancePasses` and nothing issue-specific, so DXC-side changes would not be
  involved. Of the `-fspv-*` and `-fvk-*` flags, the only binding-related one points the other
  way: `-fspv-preserve-bindings` keeps *more* bindings. There is no flag asking for more
  aggressive elimination.

**Labels:** the issue is still only `spirv`. Suggest adding `enhancement` (the module is
correct, just not minimal — nothing miscompiles) and `up-for-grabs`, which is what the
2024-08-22 comment already says in prose. I may be missing context from outside this thread.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
