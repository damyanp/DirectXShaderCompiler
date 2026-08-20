# Expected symptom — #5040 "Undefined value allowed for buffer load index"

Filed 2023-02-17 by @dmpots. Repro quality: **complete** (exact HLSL + exact `dxc` command
line + expected DXIL snippet + FXC's contrasting diagnostic, all in the issue body).

## What the issue body reports

```
// dxc /Tps_6_0 t.hlsl
ByteAddressBuffer b;

[RootSignature("UAV(u0), SRV(t0)")]
float main(uint a : A) : SV_Target
{
    uint X;
    return b.Load(X);
}
```

`X` is read uninitialized as the byte-address-buffer load index. The reporter says dxc
compiles this **without warning or error**, and the generated DXIL keeps the index as
`undef`:

```
call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 undef, i32 undef)
```

FXC, for the same construct, both warns and errors:

```
t.hlsl(7,12-20): warning X4000: use of potentially uninitialized variable (X)
t.hlsl(7,12-20): error X4575: reading uninitialized value
```

## Multiple asks — decomposed (per SKILL.md "decompose multi-ask issues")

The thread narrows the ask over four comments and 14 months, and the final maintainer
comment redirects the actionable request. Score each piece separately.

1. **Ask A (as filed): does a default `dxc` invocation diagnose the uninitialized index at
   all** (front end, no extra flags)? Reporter says no.
2. **Ask B (established in comment #1, @llvm-beanz, 2023-06-30): does `-Wuninitialized` (a
   non-default flag) diagnose it?** Already answered **yes** in the thread with a linked
   Godbolt example, and explicitly *not* proposed for default-on: comment #3 explains the
   team decided **not** to enable `-Wuninitialized` by default, citing false positives
   tracked in #2494 (closed) that were supposed to be addressed by #5377 (also closed, but
   as "not planned" — its title is `out`/`inout` should always be references, not clearly the
   same fix). This is a policy/design position, not a compiler defect to re-measure.
3. **Ask C (comment #4, @damyanp, MEMBER, 2024-08-27 — the most recent and the one that
   re-scoped the issue): "the validator should have caught it"**, i.e. DXIL validation
   should flag a resource-load index that is `undef`, independent of whether the front end
   ever warns. damyanp's comment explicitly says the team is "unlikely to fix this in the
   frontend" and repurposes the issue to track the **validator** gap instead. This is the
   ask that determines the current headline verdict, since it is the maintainer's own most
   recent framing of what "fixed" would mean.

## What "reproduces" means here

Because the issue was explicitly repurposed by a MEMBER onto the validator, the primary
predicate is:

- **Primary symptom (validator gap, Ask C):** compiling the repro with default flags (which
  runs the bundled DXIL validator, no `-Vd`) succeeds (exit 0) and does **not** print any
  validation error/warning naming the buffer-load index or its `undef` operand. If the
  validator now rejects an `undef` resource-load index/offset, this is `does-not-repro` for
  Ask C even though Ask A may be unchanged.
- **Secondary symptom (front-end silence, Ask A):** compiling with default flags (no
  `-Wuninitialized`) produces no warning/error at all about the uninitialized `X`.
- **Control (Ask B, already established true in the thread):** compiling with
  `-Wuninitialized` added *does* produce a warning about `X`. This is not being re-litigated
  as a defect — it is a fact from the thread being spot-checked, and its expected outcome is
  "still warns", not "should not warn".

`agent-constructed` shaders are not needed — the issue's own repro is used verbatim.

## Not compiler-verifiable

Ask B's "should we enable this by default" is a design/policy question, not something a
probe can answer — no flag combination proves what the *default* should be. It is recorded
as `not-compiler-verifiable` background rather than folded into the main verdict.
