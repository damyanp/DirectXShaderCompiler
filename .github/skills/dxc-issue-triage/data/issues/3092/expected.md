# #3092 — what "this reproduces" means

**Written before running any compiler.**

## The request

[#3092](https://github.com/microsoft/DirectXShaderCompiler/issues/3092) (filed 2020-08-19 by
@SaschaWillems, label `spirv`) is a **feature request**, not a bug report. GLSL lets a compute
shader's local workgroup size be driven by specialization constants:

```glsl
layout(local_size_x_id = 18, local_size_z_id = 19) in;
```

so one SPIR-V module can be specialised to different group sizes at pipeline-creation time.
The request is for an HLSL→SPIR-V equivalent. The body says "There doesn't seem to be an
equivalent of this for HLSL to SPIR-V right now."

There is **no repro in the issue body** — it is prose plus a GLSL snippet. Repro quality will
therefore be `agent-constructed`.

## What the thread adds

* 2022-07-27 @shangjiaxuan posts the `glslc` output for the GLSL form, which is the reference
  for "what correct output looks like": `OpDecorate %7 SpecId 1`, `OpDecorate %8 SpecId 2`,
  `OpDecorate %gl_WorkGroupSize BuiltIn WorkgroupSize`, and
  `%gl_WorkGroupSize = OpSpecConstantComposite %v3uint %7 %8 %uint_3`.
* 2023-11-03 @s-perron states the syntax he would want, and it is the syntax to test:

  ```hlsl
  [[vk::constant_id(13)]]
  const int X = 10;

  [numthreads(X,1,1)]
  void CSMain() { }
  ```

  "We can already define spec constants, so I would want to reuse the same syntax, just allow
  them in the `numthreads` attribute."
* 2023-11-03 @llvm-beanz: "I think this is just a bug. We should allow any compile-time
  constant in that attribute, but I think the way it is implemented we don't correctly support
  that."
* 2025-01-24 @s-perron: draft PR #7084 (`Add vk::LocalSizeId Attribute`) exists but "cannot go
  into DXC yet. We would need an HLSL spec update." He lists three prerequisites: a new
  attribute or a `numthreads` spec change; a compute-derivatives spec update (SM 6.6
  derivatives derive quad layout from `numthreads`, which assumes compile-time values); and a
  refactor of `OpExecutionModeId`. "I do not have any timeline on when we can get to this."
* 2025-07-08 @s-perron points at PR #7439 (`Allows Vulkan spec constants as attribute
  arguments`, by @danbrown-amd, `Fixes #3092`).

## The claim under test

**"There is no way to make the SPIR-V workgroup size depend on a specialization constant."**

## Does-not-reproduce criteria (falsifiable, decided in advance)

The capability is **present** — the issue would be fixed — if compiling the HLSL in
@s-perron's preferred syntax with `-T cs_6_0 -E main -spirv` produces a module where the
workgroup size is *linked to the SpecId-decorated constant*, in either of the two forms
Vulkan accepts:

1. `OpExecutionModeId %main LocalSizeId %specconst ...` — the `LocalSizeId` execution mode
   naming the spec constant; or
2. `OpDecorate %x BuiltIn WorkgroupSize` on an `OpSpecConstantComposite` whose components
   include the SpecId-decorated constant — the form `glslc` emits, quoted in the thread.

## Reproduces criteria

The capability is **still absent** if neither form appears. Two shapes are plausible and both
count as "still absent"; I will record which one actually occurs:

* **Silent fold** — dxc accepts `[numthreads(X,1,1)]`, evaluates `X` to its *initialiser* and
  emits a literal `OpExecutionMode %main LocalSize 4 1 1`. The spec constant is still declared
  (`OpDecorate %x SpecId 1`) but has no connection to the workgroup size, so specialising it at
  pipeline creation changes nothing. This is what `SemaHLSL.cpp`'s `ValidateAttributeIntArg`
  (line 13858: looks up the `VarDecl` and constant-folds `decl->getInit()`) plus
  `SpirvEmitter::processComputeShaderAttributes` (line 14600: `uint32_t x =
  numThreadsAttr->getX()`, then `addExecutionMode(..., LocalSize, {x,y,z})`) predict.
* **Hard error** — dxc rejects the attribute argument.

The **silent fold** is the more serious outcome, because the shader compiles and the
application gets a group size that silently ignores its specialisation data. If that is what
happens, the strongest available proof is an **identity control**: the same shader with the
literal `[numthreads(4,1,1)]` must produce *identical* SPIR-V, showing the reference to the
spec constant is discarded entirely.

## Also to be checked (the "has anything changed?" half)

A capability request's useful triage output is "is it still absent, and is there now a way to
do it anyway?". Three things to check against ground truth:

* Is there a `vk::LocalSizeId` attribute on `main`? (PR #7084 is still open, so expected: no.)
* PR #7378 `[SPIRV] Refactor OpExecutionModeId` **did** merge (e866b4bac, 2025-04-29) — one of
  the three listed prerequisites. Does the inline-SPIR-V escape hatch
  `vk::ext_execution_mode_id(38 /*LocalSizeId*/, X, 1, 1)` now let a user express this
  themselves, and does it accept a spec constant operand? If it works, that is a workaround
  worth naming in the comment; if it does not, that is worth recording too.
* Is `WorkgroupSize` reachable as a `vk::builtin`?

## Expected verdict shape

If the capability is absent: `status=repros`, `repro_quality=agent-constructed`,
`suggested-action=enhancement-not-bug` (the label is already `spirv`; the thread's own
blocker is an HLSL **spec** decision, which is a product/language decision this triage must
not pre-empt). History is expected to be `always-repro'd` from the SPIR-V floor. **The
bisection floor for SPIR-V issues is above v1.4.1907**, which answers "SPIR-V CodeGen not
available" — that is an `invalid-probe`, not a clean run.
