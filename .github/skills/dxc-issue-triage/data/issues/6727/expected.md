# #6727 — Support IMul/UMul/UDiv with two outputs from HLSL

*Written before running the compiler.*

## What the issue asks for

Filed 2020-04-10 by `tex3d` (MEMBER), labelled `enhancement` + `high-impact`.

> IMul/UMul/UDiv ops with two outputs have been part of the shader models since 4.0, but HLSL
> has never explicitly exposed these to HLSL so they could be fully used.
>
> This is the suggestion that we should add new intrinsic functions to HLSL that map to these
> DXIL ops, which could open up scenarios without requiring the optional 64-bit support to be
> used.

Thread positions (all from `issue.json`):

| date | who | claim |
| --- | --- | --- |
| 2020-04-10 | `jstoecker` | UMul's `mulhi`/`mullo` pair is the core of the Philox-4x32 PRNG; GLSL exposes it as `umulExtended` |
| 2021-12-03 | `fdwr` | DirectML's int64 operator emulation is "very verbose" without it |
| 2023-07-13 | `llvm-beanz` | asks whether exposing it needs a shader-model revision |
| 2023-07-13 | `tex3d` | no — the shader5x HLK test already covers these ops in DXIL via DXBC translation, so they can be exposed safely |
| 2023-07-13 | `llvm-beanz` | "Tagging this as a feature request. We'll need to prioritize this request and spec it out." |
| 2024-06-26 | `damyanp` | "This does not require a SM change. We need to add new intrinsics ... but we already have other code paths that generate these DXIL operations." |

No maintainer has stated the feature is done, and none has rejected it.

## What "this still reproduces" means

This is a **feature request**, so "reproduces" means *the capability is still absent*. It is
absent iff **all** of these hold on the ground-truth build:

1. **No HLSL-callable intrinsic maps to the two-output ops.** There is no spelling in HLSL
   (`umul`, `imul`, `udiv`, `mulhi`, `umulExtended`, …) that lowers to the DXIL two-output
   opcodes. Check `utils/hct/gen_intrin_main.txt` and `lib/HLSL/HLOperationLower.cpp`.
2. **The DXIL opcodes nevertheless exist**, are named in `docs/DXIL.rst` /
   `include/dxc/DXIL/DxilConstants.h`, and are accepted by the validator. If true, this is the
   sharper finding: *the opcode exists but is unreachable from HLSL*, exactly as the title says.
3. **Written the natural way, HLSL codegen does not reach them.** A shader that asks for the
   high and low halves of a 32x32 multiply, and for quotient + remainder of the same operand
   pair, must compile to something *other* than the two-output ops:
   * the mul-high case falls back to a 64-bit `mul i64`, which drags in the optional
     `Int64Ops` feature flag — the precise cost `tex3d` says the intrinsics would avoid;
   * `a / b` and `a % b` on identical operands stay as two separate operations rather than
     one two-output `UDiv`.

## Concrete predicted observation

Compiling the constructed repro as `cs_6_0`:

* exit 0, valid DXIL emitted;
* **no** `dx.op.binaryWithTwoOuts` (or any other `dx.op` call carrying two integer results)
  anywhere in the disassembly;
* a `mul` on `i64` operands, and the shader flagged as using 64-bit integers;
* separate `udiv` / `urem` LLVM instructions, not fused.

## Would falsify "still reproduces"

* An HLSL intrinsic that emits `dx.op.binaryWithTwoOuts` exists today (⇒ `does-not-repro`,
  `close-fixed`);
* DXC's optimiser already fuses the mul-hi or div/rem pair into the two-output op (⇒ partial
  support; `changed-behavior`);
* The DXIL opcodes turn out not to exist at all, making the request larger than described
  (⇒ the issue text would be stale).

## Repro quality

`agent-constructed`. The issue contains no shader, no command line and no compiler output —
it is a design request. Any repro here is a best-effort demonstration of the gap.

## Known hazards for this issue

* The predicate is necessarily **absence-based** ("no two-output op in the DXIL"), which is
  satisfied for free by a compile that never produced DXIL. It must carry a positive anchor,
  and a failed-compile control must be captured.
* It is also **vacuously true of any successful shader**, so the predicate alone cannot prove
  "no HLSL construct reaches these ops". That claim has to rest on source inspection
  (`gen_intrin_main.txt`, the op-code tables, and who emits the opcode), not on one probe.
* An old release may reject `uint64_t`; that would be an `invalid-probe`, not a fix.
