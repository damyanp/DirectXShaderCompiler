> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5184](https://github.com/microsoft/DirectXShaderCompiler/issues/5184).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), with the same
validator diagnostic:

```
error: validation errors
repro.hlsl:3:12: error: Instructions must be of an allowed type.
note: at '%10 = insertvalue %dx.types.fouri32 %5, i32 %9, 0' in block '#0' of function 'main'.
Validation failed.
```

A few corrections/additions to the report:

- **The trigger is `-Od` alone, not "debug mode."** `-Zi` is incidental — `-Od` with or
  without `-Zi` fails; an optimized build with `-Zi` still compiles clean. The optimizer
  isn't required, just disabled.
- **Not `uint4`-specific.** @pow2clk's linked repro uses `float4` and hits the identical
  diagnostic, because `WaveMatch` always *returns* `uint4` regardless of the argument's
  element type — a scalar (non-vector) argument compiles fine under the same flags.
- **The mechanism isn't "not scalarized."** Both the optimized and `-Od` builds already lower
  the call into four separate per-lane `waveMatch.i32` calls. What differs is how the four
  per-lane masks are recombined: the optimized build `extractvalue`s and `and`s them directly,
  while `-Od` codegen rebuilds a single aggregate via repeated `insertvalue` on the
  `%dx.types.fouri32` result type — which the validator's aggregate-type rule forbids. So this
  is the generic unoptimized-codegen path for aggregate-typed intrinsic results, not a missing
  scalarization pass specific to `WaveMatch`.
- **Always reproduced, never worked.** Across every stable release that can express the
  target profile (v1.6.2104 through the current v1.9.2607, 18 releases), none compile it
  clean; the two oldest catalogued releases predate the SM6.6 profile itself and can't run
  the repro at all. This is not a regression.
- **On the Clang expectation:** `hlsl_clang_trunk` doesn't confirm or refute it — Clang hasn't
  implemented `WaveMatch` yet (`use of undeclared identifier`), and separately rejects
  `uint4`-typed `SV_Target` outright, so today's front end can't even parse this repro's
  signature. It's a plan for the new front end, not a measured result yet.

Compiler Explorer, `dxc_1_6_2112` and `dxc_trunk` (both reproduce identically):
https://godbolt.org/z/GjKe8bn5b

Suggest adding `validation` (the failure is specifically a DXIL validation rejection) and
`up-for-grabs`, matching the intent already stated above.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
