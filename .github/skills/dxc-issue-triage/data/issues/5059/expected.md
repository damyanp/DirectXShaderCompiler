# Expected symptom for #5059

Title: "HLSL loop optimization results in an unsupported i33 type"

## What the reporter showed

Compiling the attached `i33.hlsl` (a `RWByteAddressBuffer`-based compute shader,
entry `CSMain`, `[numthreads(8,8,1)]`) with `-T lib_6_3 i33.hlsl -Fc i33.dxil.txt`
produced disassembly containing operations on an `i33` integer type, e.g.:

```
%8 = zext i32 %7 to i33
%11 = mul i33 %8, %10
%12 = lshr i33 %11, 1
%13 = trunc i33 %12 to i32
```

DXIL's spec (`docs/DXIL.rst`) documents only `i1, i8, i16, i32, i64` as supported
integer widths. The reporter attributes the `i33` to LLVM's Scalar Evolution
(SCEV) pass widening the loop trip-count expression
`((input - 1) * (input - 2)) / 2` by one bit to make room for the intermediate
multiply's possible overflow, then narrowing back to `i32` after the division.
The claim is that this `i33`-typed SSA value is not eliminated/legalized before
being written into (or, on later builds, checked against) the final DXIL
module, where widths outside the supported set are not allowed to appear.

Reported against December 2022 and October 2020 dxc releases. Two comments in
the thread are relevant:
 - 2023-11-02 (pow2clk, COLLABORATOR): a Compiler Explorer link claimed to show
   the behaviour.
 - 2024-09-25 (damyanp, MEMBER): closed the issue saying "this no longer repros
   on recent compilers", then reopened it **two minutes later** saying the
   previous godbolt link was bad and posting a second link that does show a
   repro, and added the `validation` label plus a `Backlog` milestone. So the
   thread is internally self-correcting -- there is no stale "no longer
   repros" claim left standing; the live, final position in the thread is
   "reproduces".

## What "reproduces" means here

The underlying defect is that the compiler's optimizer can leave a SCEV-derived
temporary of illegal DXIL integer width (`i33`) live in a shader that a user
wrote with only 32-bit arithmetic. This can manifest as either of two
observable shapes, and either one counts as "reproduces":

 1. **Silent/legacy shape**: the compile succeeds (exit 0) and the `i33`
    zext/mul/lshr/trunc sequence is visible in the disassembly text (what the
    reporter saw) -- i.e. an internally-illegal type escaped into a
    "successfully" compiled, validated DXIL module.
 2. **Caught/current shape**: the compile fails with a diagnosed DXIL
    validation error naming the illegal width, e.g.
    `error: Int type 'i33' has an invalid width.` -- i.e. the same illegal type
    is generated, but a validator check (added at some point) now catches it
    and refuses to emit the module.

Both shapes are evidence of the *same* root defect (the optimizer produces an
operation whose type DXIL does not support, and nothing narrows or eliminates
it before that fact matters). Which shape is observed is a statement about
whether the *validator* has learned to check integer width, not about whether
the *optimizer* still produces the type -- those are different questions and
are scored separately.

`does-not-repro` would mean: no `i33` (or any operation on an out-of-range
integer width) appears anywhere in the compiled output, disassembly, or
diagnostics, even with validation disabled (`-Vd`) so a caught case cannot hide
a persisting one.

## Repro-quality

`complete` -- the issue includes a full, self-contained attachment
(`i33.hlsl.txt`) and an exact command line. The command line as literally
filed (`-T lib_6_3 i33.hlsl -Fc ...`, no `-E`) is a `lib_6_3` compile with no
explicit entry point and no `[shader(...)]` attribute on `CSMain`; whether that
exact invocation still reaches the SCEV-widening code path at all (as opposed
to being probed via a direct `-T cs_6_3 -ECSMain` compile, which is what the
maintainer's working godbolt link used) is itself something to verify before
trusting a "no repro" result from the literal command line.
