> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4501](https://github.com/microsoft/DirectXShaderCompiler/issues/4501).

Still open and still unimplemented on `main`
([13730886e](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e); the local
Debug build used here self-reports `1.9.0.5433` with a fork-local build identifier rather
than the public commit above).
Neither `DebugBuildIdentifier` nor `DebugStoragePath` is emitted in any mode, and `git grep`
finds no emitter, enumerator, test or doc for either anywhere in the tree.

In the richest mode DXC offers, `-fspv-debug=vulkan-with-source`, the module carries 16 kinds
of `NonSemantic.Shader.DebugInfo.100` instruction — including `DebugEntryPoint`, opcode **107**,
the immediate neighbour of the two requested ones. The gap is in what DXC emits, not in the
instruction set: 105 and 106 have been in SPIRV-Headers since 2021-03-24, and SPIRV-Tools
validates both (`source/val/validate_extensions.cpp`).

Measured on all 20 stable releases: 16 of them (v1.6.2112 2021-12 → v1.9.2607 2026-07) emit
`NonSemantic.Shader.DebugInfo.100` and none emits either instruction. The four older stable
releases cannot answer the question rather than answering it cleanly — v1.4.1907 has no SPIR-V
codegen, and v1.5.2010/v1.6.2104/v1.6.2106 predate `-fspv-debug=vulkan*` and emit
`OpenCL.DebugInfo.100`, whose opcodes stop at 36.

One thing has changed since 2022 and it changes the shape of the request. `-Fd` is now
rejected outright:

```
$ dxc -T ps_6_0 -E main -spirv -fspv-debug=vulkan-with-source -Fd spirv-pdb\ -Fo out.spv repro.hlsl
dxc failed : -Fd is not supported with -spirv
```

That explicit diagnostic was added on 2022-06-20, first shipped in v1.7.2207, 17 days after
this issue was filed. On v1.6.2112, current at filing, `-spirv -Fd` was accepted and then
failed with
`Unable to find required part in blob` — DXC looking for a DXIL debug part in a SPIR-V blob. So
there is no `-Fd` path for SPIR-V to extend: the ask is really "add split debug info to the
SPIR-V backend", with these two instructions as its module-side half.

Compiler Explorer, both panes emitting NonSemantic debug info and neither emitting the
requested instructions: <https://godbolt.org/z/cj44aEcbj>

Suggested labels: **`enhancement`** and **`debug info`**, alongside the existing `spirv`.
Nothing here is broken; this is a capability that was never built. Whether to build split
debug info for SPIR-V is a product decision, not something this triage can settle.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
