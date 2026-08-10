> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3092](https://github.com/microsoft/DirectXShaderCompiler/issues/3092).

**Still absent.** Tested on `main` (`1.9.0.5433`, 13730886e) and on all 19 SPIR-V-capable
releases in the catalog from v1.5.2010 (2020-10) to v1.9.2607 — every one rejects it with the
same error. v1.4.1907, the only older one probed, answers `SPIR-V CodeGen not available` and is
not a valid probe.

Using the syntax @s-perron [proposed in 2023](https://github.com/microsoft/DirectXShaderCompiler/issues/3092#issuecomment-1792858686):

```hlsl
[[vk::constant_id(1)]] const uint TGSIZE_X = 4;
RWStructuredBuffer<uint> Out;

[numthreads(TGSIZE_X, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) { Out[tid.x] = tid.x; }
```

```
repro.hlsl:14:2: error: 'numthreads' attribute requires an integer constant
[numthreads(TGSIZE_X, 1, 1)]
 ^          ~~~~~~~~
repro.hlsl:14:2: warning: Group size of 0 (0 * 1 * 1) is outside of valid range [1..1024] - attribute will be ignored [-Wignored-attributes]
[numthreads(TGSIZE_X, 1, 1)]
 ^~~~~~~~~~~~~~~~~~~~~~~~~~
repro.hlsl:15:6: error: compute entry point must have a valid numthreads attribute
void main(uint3 tid : SV_DispatchThreadID) {
     ^
```

[Compiler Explorer](https://godbolt.org/z/5dG5M5EnP) — dxc 1.6.2112, dxc trunk, and Clang.

**Two measurements narrow the ask.** `[numthreads]` already accepts a *named* compile-time
constant: the same shader with `static const uint TGSIZE_X = 4;` compiles and emits
`OpExecutionMode %main LocalSize 4 1 1`. But `[[vk::constant_id(1)]] static const uint` gives
`error: specialization constant must be externally visible`. What is missing is not
compile-time constants in `numthreads` but a dimension that is *not* known at compile time.

**Clang trunk emits the same first diagnostic**, verbatim. Its controls compile cleanly there —
`static const uint` as a `numthreads` argument, and a `[[vk::constant_id(1)]]` constant used
with a literal group size — so this is the feature being absent, not incomplete Clang support.

**Since the [2025-01 checklist](https://github.com/microsoft/DirectXShaderCompiler/issues/3092#issuecomment-2612831968),**
item 3 has landed: #7378 "[SPIRV] Refactor OpExecutionModeId" (e866b4bac). As a result
`LocalSizeId` is now reachable from inline SPIR-V — `vk::ext_execution_mode_id(38, TGSIZE_X, 1u, 1u)`
with `-fspv-target-env=vulkan1.3` compiles and emits:

```
OpExecutionMode %main LocalSize 1 1 1
OpExecutionModeId %main LocalSizeId %TGSIZE_X %uint_1 %uint_1
```

Not a substitute: `[numthreads]` is still mandatory on a compute entry point, so the module
carries both execution modes. It passes DXC's bundled SPIR-V validation; I have not tested it
on a driver.

Items 1 and 2 remain open HLSL spec questions. The compute-derivatives coupling is still in the
code — `addDerivativeGroupExecutionMode` picks the quad layout by reading back the
already-emitted `LocalSize` operands (`SpirvEmitter.cpp`). Nothing measured here bears on what
the answer should be. #7084 (draft) and #7439 (`Fixes #3092`) are both still open.

**Labels:** suggest adding `enhancement` and `hlsl-next`, keeping `spirv` — the remaining
blocker is a language spec decision rather than an implementation defect.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
