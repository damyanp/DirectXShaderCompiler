# #4036 — expected symptom

Written **before** running any compiler, from the issue text alone.

## The report

Filed 2021-10-25 by `Jasper-Bekkers`. Original title carried the prefix `[hlsl 2021]`
(renamed twice; the prefix was dropped by `pow2clk` on 2021-11-08). Body is a complete,
self-contained pixel shader plus the exact diagnostic and a shader-playground link.

```hlsl
struct PSInput
{
	float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
	return ((StructuredBuffer<float>)ResourceDescriptorHeap[int(input.color.x)]).Load(0);
}
```

Reported output:

```
...hlsl:8:79: error: no member named 'Load' in 'StructuredBuffer<float>'
        return ((StructuredBuffer<float>)ResourceDescriptorHeap[int(input.color.x)]).Load(0);
               ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ^
```

Reporter's question: "Somehow the right type is deduced, but we can't call it's functions?"

Maintainer reply (`pow2clk`, 2021-11-08): the expected usage is to assign to a local
variable; the maintainer agrees the reported usage *should* be supported, but a workaround
exists so it is not a priority. The issue was milestoned `Dormant` (2024-04-22) and is
currently unlabelled (`needs-triage` was added 2023-06-29 and removed 2024-04-22).

## What "this reproduces" means

**Primary symptom** — compiling the body above emits, at the `.Load(0)` call site, the
diagnostic:

```
error: no member named 'Load' in 'StructuredBuffer<float>'
```

i.e. member lookup fails on the *result of a C-style cast* of a `ResourceDescriptorHeap`
subscript, even though the cast names a type that does have `Load`. Compilation fails.

**Does not reproduce** would mean the shader compiles (exit 0, DXIL produced), or the
diagnostic is gone.

**Changed behaviour** would mean it still fails but with a different message (for example a
diagnostic about descriptor-heap indexing, an ICE, or a validation error) — that is a
distinct outcome and must not be collapsed into either of the above.

## Secondary asks recorded separately

1. **The workaround must work.** `pow2clk` states the supported spelling is a local
   variable. If assigning to a local *also* fails today, the issue is materially worse than
   filed. Scored by a labelled control, not by the primary predicate.
2. **The maintainer position** — "we agree that this usage should be supported" — makes this
   an accepted-but-unimplemented enhancement rather than a plain bug. The verdict should say
   whether the enhancement has since landed.

## Configuration

The issue body gives no command line. Derived:

- `-T ps_6_6` — `ResourceDescriptorHeap` is a Shader Model 6.6 feature and the entry point
  returns `SV_TARGET`, so a pixel shader at SM 6.6 is the lowest profile that can express the
  repro. Anything older cannot see `ResourceDescriptorHeap` at all.
- `-E PSMain`.
- `-HV 2021` — the original title said `[hlsl 2021]`, so that is the reporter's
  configuration. It is also today's default, so pinning it protects the old repro from a
  moved default. Whether it is load-bearing is a question to *measure* (labelled variant
  without it), not to assume.

## Expected hazards (stated in advance so the evidence can contradict them)

- **The symptom IS a diagnostic.** `no member named` is one of the runner's feature-absence
  markers, so a genuine reproduction is at risk of being demoted to `invalid-probe`. The
  documented mitigation is to quote the diagnostic verbatim as a *positive* clause of
  `match.json`; the capture headers must be checked to confirm the demotion did not fire.
- **`ResourceDescriptorHeap` is SM 6.6**, released after this issue was filed. Releases
  predating it will reject the input in a completely different part of the compiler, score
  `no-repro`, and fake a fix boundary. Every such release must be shown to be an
  `invalid-probe`, and the count of skipped releases reported. The bisection floor of
  v1.4.1907 is therefore not the effective floor; history can only be reported "for as long
  as it is possible to check".
- **A per-release feature-presence control is required** to separate "this release predates
  SM 6.6" from "this release rejected something else in my repro".

## Repro quality

`complete` — the issue body contains a compilable shader and the verbatim diagnostic. Only
the command line is reconstructed.
