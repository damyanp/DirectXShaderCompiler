# #2792 — expected behaviour

> Written **before** any compiler was run, from the issue text alone.
> Title: *"Need to report error when use constant which has offset bigger than root
> constant size."* Filed 2020-03-25, label `bug`, **0 comments**.

## What the issue says

The body is 250 characters and carries a full shader, unfenced (no ``` markers), followed by
one sentence of explanation:

```hlsl
cbuffer cb : register(b0)
{
  float a;
  float b;
}

[RootSignature("RootFlags(0), RootConstants(b0, num32BitConstants = 1)")]
float main() : SV_Target {
  return b;
}
```

> Root constant size is 1, but `b` has offset 1 which is out of bound.

No command line, no compiler version, no expected/actual output, no comments. The profile is
implied by `float main() : SV_Target` → a pixel shader; `ps_6_0` is the oldest profile that
can express everything here.

## The claim, restated

`RootConstants(b0, num32BitConstants = 1)` reserves **one** 32-bit word at `b0`. The cbuffer
bound at `b0` declares two floats, so `b` sits at 32-bit offset 1 (byte offset 4) — one word
past the end of what the root signature reserves. Reading `b` therefore reads outside the
root constant block.

The reported defect is a **missing diagnostic**: the compiler is expected to *report an
error* for this and does not. That is the inverse of the usual shape — the symptom is the
**absence** of output, not its presence.

## What "this reproduces" means

**Reproduces** = compiling the shader above with an attached root signature whose root
constant block is too small **succeeds** (or at least emits no diagnostic naming the
overrun), so the out-of-bounds constant access is accepted silently.

Concretely, the symptom is present when **all** of the following hold:

1. dxc does **not** emit any error or warning that identifies the out-of-range constant
   access — no message mentioning the root constant size, the offset, `num32BitConstants`,
   an out-of-bounds/overrun cbuffer read, or `b` being outside the root signature; and
2. the compile otherwise **completes**, i.e. it reached the point where such a check would
   have to run. A compile that fails for an unrelated reason (bad profile, unparsed root
   signature, syntax error, crash) has not measured anything — see below.

**Does not reproduce** = dxc rejects the shader with a diagnostic that names this problem,
i.e. the feature the issue asks for now exists.

**Changed behavior** = dxc fails, but for a different reason — e.g. it diagnoses the root
signature/shader pairing on unrelated grounds, or it errors without naming the size overrun.

## Traps this issue walks straight into

- **An absence predicate is satisfied for free by a compile that never started.** "No error
  mentioning the root constant size" is trivially true of a shader that failed to parse, of
  a release that cannot express `RootConstants(...)` in a `[RootSignature("...")]`
  attribute, and of a release that crashed. Clause 2 above exists for that reason, and the
  predicate must carry it. A control is mandatory: the predicate has to *not* fire on an
  input where the diagnostic really is produced.
- **Nonzero exit ≠ crash.** On Windows dxc returns E_FAIL (0x80004005) for ordinary
  diagnosed errors, including DXIL validation failures. A nonzero exit here most likely
  means "diagnosed", not "crashed".
- **Two different mechanisms could own this check, and they are not the same thing.**
  DXIL *validation* (`dxv`/the validator, run over the container) and *root signature*
  validation (the root signature vs. the shader's resource bindings) are separate. Which one
  would be responsible has to be established from the source before either is asserted.
- **Bug vs. feature request.** The title is phrased as a request — "Need to report error
  when …". If no version of DXC has ever performed this check, then "it still does not" is a
  statement about a feature that was never implemented, and `enhancement-not-bug` is on the
  table. That judgement should follow the evidence, including whether D3D12 defines this as
  an error at all or merely as undefined behaviour at draw time.

## Repro quality

**`complete`.** The issue supplies a whole shader that compiles as-is once a profile is
supplied; nothing had to be invented. (The body has no ``` fence, so a tool looking for a
code block sees "prose" — the text is nevertheless a complete repro, and it is transcribed
verbatim.)

## What would make this inconclusive

If no release can express the repro at all, or if the only observable difference between
"the check is missing" and "the compile failed early" cannot be separated by a predicate
plus a control, then the honest answer is `inconclusive` rather than a forced `repros`.
