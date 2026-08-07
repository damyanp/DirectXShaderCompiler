# Expected symptom — #3009 "dxc silently passes uninitialized value as undef"

**Reported (2020-06-30):** a shader reads an uninitialized local (`b.y` is never written) and
DXC emits DXIL passing `undef` into `@dx.op.tertiary.i32` (`IMad`) with **no warning or
error**.

**Repro quality:** `complete` — a full shader is supplied, and a maintainer supplied a second,
better one.

**Two repros, and the second is the one that matters.** `pow2clk` noted that arbitrary output
semantics are allowed to be partially undefined, so the original `: OUT` shader is a weak
demonstration. He replaced it with a `SV_Position` version where partial undefinedness is not
excusable. Both are kept: `repro.hlsl` (as reported) and `repro-pow2clk.hlsl` (maintainer's).

**What we test:** compile each as reported and inspect the emitted DXIL.

**Symptom is present if:** compilation succeeds (or at least emits no diagnostic about the
uninitialized read) *and* the DXIL passes `undef` into a `dx.op` call.

**Symptom is absent if:** DXC errors or warns about the uninitialized value, or the validator
rejects the module.

**Note on the `validation` label:** @damyanp's 2024 comment — "this is unlikely to be
something we could catch before codegen, but the validator should be able to detect this" —
means `validation` (which denotes **DXIL validation**) is correctly applied here. Contrast
#1306, where the label was proposed for removal because the request was for a front-end
diagnostic. The test therefore has to distinguish "no diagnostic at all" from "the validator
catches it", which is the difference between the bug being open and being fixed.

**Watch for a false negative:** #1702 showed DXC's validator *does* reject `undef` stores to a
UAV. If this repro now fails validation, the symptom is gone even though compilation still
"fails". Judge on whether the uninitialized read is diagnosed, not on the exit code.

**Out of scope:** `jshopf`'s 2021 comment (an `out` parameter left unassigned) — @damyanp
stated in 2024 that it is a different issue and asked for a separate report. Not tested here.
