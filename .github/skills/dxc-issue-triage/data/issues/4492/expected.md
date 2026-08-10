# #4492 — expected symptom

**Written before running any compiler.** Derived from the issue body and the attached
`dxc-float16_t4x4-example.zip` only.

Issue: [#4492](https://github.com/microsoft/DirectXShaderCompiler/issues/4492),
"[DXIL] Broken codegen for loading elements from FP16 matrix types in StructuredBuffer",
filed 2022-06-01 by `pclarberg`. No comments.

## What the reporter claims

Loading individual elements of a `float16_t4x4` (`matrix<half,4,4>`) held in a
`StructuredBuffer` produces the wrong elements. From the body:

> ```
> float16_t2 b = buf.a[0].xy;
> ```
> This loads elements a[0][0] and a[0][2], not a[0][1] as expected.
> Looking at the generated code it looks like it thinks there is 4B between each element
> not 2B.

So the claim is precise and mechanical: **byte offsets into the structured-buffer element
are computed with a 4-byte per-scalar stride instead of 2 bytes.**

## What the attachment shows

`attachment/1-mat.hlsl` is the reporter's shader (Slang-generated): a `[numthreads(1,1,1)]`
compute entry `testStructuredBufferMatrixLoad2` reading all 16 elements of
`row_major half4x4 m_0` out of `StructuredBuffer<Test2_0> data2_0 : register(t1)` through an
8-way `switch`, and writing them as floats to `RWStructuredBuffer<float> result_0`.

`attachment/3-mat.dxil.asm` is the reporter's captured disassembly. Two facts read directly
off it, and they are the definition of the bug:

1. The buffer element is **32 bytes**:
   `;   } $Element;   ; Offset: 0 Size: 32` and `!7 = !{i32 1, i32 32}` (stride 32).
   That is right: 16 halves x 2 bytes.
2. Every `@dx.op.rawBufferLoad.f16` uses a **4-byte** stride, so the sixteen loads sit at
   elementOffset `0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60`.

Correct codegen for a 32-byte element is `0, 2, 4, ..., 30`. The observed sequence runs to
offset 60, i.e. **the last eight loads read past the end of the 32-byte element entirely.**

The attachment names its own configuration: `!3 = !{!"cs", i32 6, i32 5}` (`cs_6_5`) and
`; Note: shader requires additional functionality: Use native low precision`
(`-enable-16bit-types`). `dx.version 1.5`, `dx.valver 1.6`.

## "This reproduces" means

Compiling `repro.hlsl` (the reporter's shader, verbatim) with native 16-bit types and
inspecting the emitted DXIL, **all** of:

- the compile **succeeds** (exit 0) and emits `@dx.op.rawBufferLoad.f16` — i.e. native f16
  raw-buffer loads were really produced. This is the anti-vacuity / instrument self-test:
  without it an absent-token or malformed-output run could be scored either way for free;
- at least one of those `rawBufferLoad.f16` calls has an **elementOffset >= 32**, which for a
  32-byte `$Element` is out of bounds and is only producible by the doubled stride;
- concretely, the `case 0` pair — source `m_0[0][0]` and `m_0[0][1]` — loads at offsets
  `0` and `4` rather than `0` and `2`.

"This does not reproduce" means the compile succeeds, `rawBufferLoad.f16` is still emitted,
and every elementOffset lies in `[0, 30]` with a 2-byte stride.

The symptom is **wrong code at exit 0**. There is no exit status, no diagnostic and no crash
to lean on, so the predicate has to read the emitted DXIL. That makes it an instrument as
well as a measurement, hence the two guards above: a positive anchor on every probe, plus a
known-good control that must *not* match.

## Control (predicate discrimination)

`control-half-vec-array.hlsl`: the same shader shape, same profile, same flags, same 32-byte
element and the same `rawBufferLoad.f16` instrument, but with the matrix replaced by
`float16_t4 v[4]` — a type whose scalar stride there is no reason to believe is broken.
Expected `no-match`. If the predicate fires on it, the predicate is matching structurally
normal f16 buffer IR rather than the defect, and is worthless.

## Prediction (recorded so it can be wrong)

I expect this still reproduces: nothing in the thread claims a fix, the issue is still open
and milestoned, and it carries `matrix-bug` + `correctness` applied by a maintainer in
2024-04, ~2 years after filing. But the evidence decides.

## Repro quality

`complete` — the reporter attached a self-contained `.hlsl` plus the `.dxil` and `.dxil.asm`
it produced, and the asm names the target profile and the 16-bit-types requirement, so the
command line is recoverable from the attachment rather than guessed.

## Known hazards for this issue

- **FP16 needs `-enable-16bit-types` and SM 6.2+.** Any release predating either rejects the
  input outright. That is an `invalid-probe`, not a clean run, and must not be read as a fix.
- **`rawBufferLoad` (opcode 139) is itself SM 6.2+.** Same trap one layer down.
- **Disassembler formatting drifts across releases** (named vs numbered SSA values, comment
  layout). A predicate anchored on a modern build's spelling can invent a boundary. Anchors
  use `%[\w.]+` rather than `%\d+`, and the self-test clause above must be checked on every
  probed release, not only on `main`.
- **HLSL language default moved to 2021** after this was filed. If a modern build rejects the
  2022-era source for that reason, the probe measured the language mode, not the bug.
