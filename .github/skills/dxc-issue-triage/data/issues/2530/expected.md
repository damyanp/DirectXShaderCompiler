# #2530 — Array bound with static const variable

*Written before any compiler was run.*

## What the issue reports

Filed 2019-10-17. DXC rejects an array bound that is derived, via a **type
conversion**, from a `static const` variable. FXC accepts the same code.

Two cases are given in the body. Both use a pixel entry point
(`float4 main() : SV_Target`); no profile, no flags and no compiler version are
stated.

**Case 1** — cast applied at the array bound:

```hlsl
static const float ARRAY_SIZE = 1;

float4 main() : SV_Target
{
    float array[uint(ARRAY_SIZE)] = { 1.0f };
    return (float4)0;
}
```

**Case 2** — cast applied one step earlier, into a `static const uint`:

```hlsl
static const float ARRAY_SIZE = 1;
static const uint ARRAY_SIZE_UINT = (uint)ARRAY_SIZE;

float4 main() : SV_Target
{
    float array[ARRAY_SIZE_UINT] = { 1.0f };
    return (float4)0;
}
```

Reported DXC behaviour, quoted in the issue:

> `error: variable length arrays are not supported in HLSL`

Reported FXC behaviour: *"This same code compiles successfully with FXC."*

The one comment on the thread (pow2clk, 2020-08-14) says only
`Related to #2188`. It adds no repro, no diagnosis and no "still repros" data
point.

## What "this reproduces" means

**The symptom is present when DXC fails to compile either case with
`error: variable length arrays are not supported in HLSL`.**

That is a positive predicate — a specific diagnostic string that must be
*emitted* — so it is not satisfied for free by a compile that never started
(the absence-predicate trap in SKILL.md step 6 does not apply). A release that
rejects the repro for an unrelated reason (bad profile, unknown identifier)
scores `invalid-probe` rather than a spurious clean run.

The symptom is **absent** when the shader compiles successfully (exit 0, DXIL
emitted). Anything else — a different diagnostic, a crash — is
`changed-behavior`, not a fix.

## What would falsify it

- The shader compiles to DXIL: the issue is fixed.
- DXC still rejects it but with a *different*, well-targeted diagnostic (e.g.
  "array size must be an integer constant expression"): the defect is largely
  unchanged but the issue text is stale about the wording.
- FXC turns out to reject it too: the `fxc-disagrees` label is wrong, and the
  premise of the report is wrong. **This must be measured, not assumed** — the
  claim "compiles successfully with FXC" is the reporter's, from 2019.

## Things to be careful about

- **Profile.** The reporter names none. `SV_Target` implies a pixel shader, so
  `-T ps_6_0 -E main` — the oldest SM6 pixel profile, so v1.4.1907 can run it
  (SKILL.md step 6: target the oldest profile that still shows the symptom).
- **Language version.** Filed in 2019, when DXC's default `-HV` was not 2021.
  SKILL.md warns that a default moving forward can make an old repro fail for a
  new reason and fake a fix. Must be checked with an explicit `-HV 2016`
  variant rather than assumed irrelevant.
- **Is DXC even wrong?** In C++03 ICE rules a `const float` is not usable in an
  integral constant expression, so clang's diagnostic is defensible as a
  language-rules question rather than a plain bug. Whether HLSL *should* follow
  FXC here is a language decision, not something triage can settle. Report what
  each compiler does; do not pre-empt the decision.
- **Bisection floor.** This is a 2019 issue and the oldest usable release is
  v1.4.1907 (2019-07), which postdates nothing here but predates the report by
  three months. "Always reproduced" can only ever mean "for as long as it is
  possible to check".

## Repro quality

**`complete`** — the issue body contains two self-contained shaders that
compile as-is once a profile and entry point are supplied. Only the profile
(which `SV_Target` determines) had to be added.
