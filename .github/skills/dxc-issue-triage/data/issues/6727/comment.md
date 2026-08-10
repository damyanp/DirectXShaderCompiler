> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6727](https://github.com/microsoft/DirectXShaderCompiler/issues/6727).

Still absent on `main` at
[13730886e](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e6a9019e4e0823746470f3ab75341d6b)
(the Debug build used here self-reports a fork-local commit, but its compiler
source is identical to that one).

**What HLSL produces today.** In `cs_6_0`, the high half of a 32x32 multiply is
reachable only by widening to `uint64_t`, which adds the optional `64-Bit
integer` feature to the shader, and quotient and remainder of one operand pair
stay separate:

```llvm
;       64-Bit integer
  %8 = mul nuw i64 %7, %6
  %9 = lshr i64 %8, 32
  %10 = trunc i64 %9 to i32
  %11 = trunc i64 %8 to i32
  %12 = udiv i32 %4, %5
  %13 = urem i32 %4, %5
```

**FXC emits the two-output DXBC operations from the same source.** For `a / b`
and `a % b`, `fxc /T cs_5_0` emits one `udiv r0.x, r1.x, r0.x, r0.y`, quotient
and remainder being its two outputs. For a plain `a * b` it emits
`imul null, r1.y, r0.y, r0.x` — DXBC's multiply has two destinations and the
high one is discarded into `null`. The divide/remainder pair side by side on
Compiler Explorer: https://godbolt.org/z/1nG4f73d3

**The opcodes are present — just not reachable from HLSL.** `IMul` = 41,
`UMul` = 42, `UDiv` = 43, op class `BinaryWithTwoOuts`, `dx.op` name
`binaryWithTwoOuts`, returning a two-`i32` struct
(`include/dxc/DXIL/DxilConstants.h`, `lib/DXIL/DxilOperations.cpp`,
`docs/DXIL.rst`). The only emitter in the tree is the DXBC-to-DXIL converter
(`projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp:2651-2657`), matching
tex3d's note that the shader5x HLK coverage arrives through translation.
`utils/hct/gen_intrin_main.txt` has no entry for any of them.

Worth knowing before implementing: `lib/HLSL/HLOperationLower.cpp:7860` reads
`{IntrinsicOp::IOP_umul, TranslateMul, DXIL::OpCode::UMul}`, but `IOP_umul` is
the unsigned overload of `mul()` and `TranslateMul` never reads its `opcode`
parameter, so that entry emits nothing.

The SPIR-V path has the same gap: `-spirv` on the same shader gives
`OpCapability Int64` with a 64-bit `OpIMul`, and separate `OpUDiv`/`OpUMod` —
no `OpUMulExtended`, the instruction behind GLSL's `umulExtended`.

**History.** All 20 stable release binaries from v1.4.1907 (2019-07) through
v1.9.2607 compile the shader and none emits the op, so this is not a
regression.

**Related work elsewhere.** LLVM's DirectX backend tracks lowering these ops in
[llvm/llvm-project#128638](https://github.com/llvm/llvm-project/issues/128638)
(open since 2025-02), proposing overflow-intrinsic lowering and explicitly
waiting on the HLSL-side decision here. Searching `microsoft/hlsl-specs` issues
and PRs for these operations returns no results.

**Label suggestion:** add `fxc-disagrees`. `enhancement` and `high-impact` still
fit.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
