# #3055 — Improve error reporting for intrinsic methods with type mismatched arguments

Written **before** running any compiler.

Filed 2020-07-23 by `pow2clk`. Labels: `tech-debt`, `diagnostic`.
<https://github.com/microsoft/DirectXShaderCompiler/issues/3055>

## What the issue claims

Intrinsic *methods* (members of `Texture2D`, `Buffer`, …) have their own overload-resolution
error-reporting path, separate from the one fixed for #2693 / #818. When a call fails because
an **argument type** does not match, that candidate's failure reason "is elided due to
incomplete error reporting from the HLSL code", so the only notes the user gets are about the
*other* overloads, which failed for an unrelated reason (wrong **argument count**).

The result is a diagnostic that never mentions the mistake actually made.

## The repro in the issue body

The body was **edited on 2023-09-27** (`pow2clk`: "Exampled updated to a quite plausible
mistake to make") after `llvm-beanz` reported on 2023-07-14 that the *original* example
compiled clean. The example below is the current one, and it is the one under test. The
2020-era example is gone from the issue and is not recoverable from the issue text.

```hlsl
Texture2D<float4> tex;
SamplerComparisonState samp;

float4 main(float2 coord : C) : SV_Target {
  return tex.Sample(samp, coord);
}
```

`Texture2D::Sample` takes a `SamplerState`. The user passed a `SamplerComparisonState` — a
plausible copy/paste slip. The overload that the user *meant* is the 2-argument
`Sample(SamplerState, float2)`; it fails on argument 1's type.

## What "this reproduces" means

Compiling the above (pixel shader, `main`) must produce **all** of:

1. `error: no matching member function for call to 'Sample'`;
2. candidate notes complaining only about **arity** — `requires 3 arguments, but 2 were
   provided`, and likewise for 4 and 5;
3. **no** note anywhere explaining the real problem, i.e. nothing saying the argument could
   not be converted from `SamplerComparisonState` to `SamplerState`. The 2-argument
   candidate — the one the user meant — is not listed at all.

Point 3 is the defect. Points 1 and 2 are what the compiler prints instead, and they must be
required too: without them, an "absent conversion note" is satisfied for free by any compile
that never reached overload resolution.

Quoted verbatim from the issue body:

```
<source>:5:14: error: no matching member function for call to 'Sample'
  return tex.Sample(samp, coord);
         ~~~~^~~~~~
<source>:5:14: note: candidate function template not viable: requires 3 arguments, but 2 were provided
<source>:5:14: note: candidate function template not viable: requires 4 arguments, but 2 were provided
<source>:5:14: note: candidate function template not viable: requires 5 arguments, but 2 were provided
```

## What would count as **not** reproducing

- A note naming the conversion that failed (`no known conversion from 'SamplerComparisonState'
  to 'SamplerState' for 1st argument`, or equivalent wording); or
- a direct, specific error about the sampler type instead of the generic overload failure.

Compiling **successfully** would not be a fix — it would be a different bug. The call is
genuinely invalid and must be rejected.

## What is explicitly *not* the symptom

- A **non-zero exit code**. This issue's expected behaviour is a diagnosed error, and on
  Windows dxc returns `E_FAIL` (0x80004005) for every ordinary diagnosed error. Exit status
  carries no information here and must not be part of the predicate.
- An **internal failure / crash**. Nothing in the issue reports one.

## Repro quality

`complete` — the issue body supplies a self-contained shader with an entry point and a
semantic. Only the profile (`ps_6_0`, implied by `SV_Target` + `float4 main`) and the entry
name had to be supplied, both unambiguous.

## Known hazards to watch (recorded in advance)

- The reported symptom **is** a diagnostic, so the runner's `invalid-probe` classifier and the
  symptom are the same kind of observation. The classifier's marker list contains
  `no matching function for call to`; the expected error is `no matching **member** function
  for call to`, which does not contain it — but only by one word. Check every probe's
  classification against its captured text rather than trusting the header.
- Point 3 makes this a mixed (partly absence-based) predicate, so `_is_absence_predicate`
  will be true and a matching probe can be demoted to `invalid-probe`. Verify by hand.
- The issue predates the `-HV 2021` default switch (v1.7.2308). If old and new releases
  disagree, re-check with the language version pinned before calling it a transition.
