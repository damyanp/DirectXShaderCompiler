# Expected symptom (written before running anything)

Issue: SV_VertexID is documented/specified as `uint`. Declaring the parameter bound to
`SV_VertexID` as `float` instead should, per the reporter, produce a **compile-time error**
(a Sema/front-end diagnostic) because the declared type does not match the semantic's
required type. Instead, the reporter says dxc accepts the shader at compile time and only
fails later, during **DXIL validation**, with a validation error.

This is a diagnostic-quality / tech-debt issue (labels: bug, tech-debt, diagnostic): the
compiler already rejects the input, but at the wrong compilation stage. The interesting
history question is not "does it fail" (it should, one way or another) but **which stage
produces the failure**: a Sema-level `error:` before DXIL is emitted (matches reporter's ask)
vs. a validation-only diagnostic after a warning is printed (the reported bug).

"Reproduces" (the reported bug is still present) means: dxc compiles the repro shader to
DXIL (i.e. does not stop with a hard Sema error) and the failure, if any, is reported by the
DXIL validator, not by the front end.

"Fixed" (does-not-repro) would mean: dxc now rejects the mismatched type at compile time
(Sema diagnostic), before validation ever runs, i.e. the DXIL validator is never reached for
this input.

Repro quality: **complete** — the issue body's shader has a typo (`SV_VertextID`, extra
"t") but the reporter's own linked Compiler Explorer permalink
(https://godbolt.org/z/ahe1fjsEM) uses the correct spelling `SV_VertexID` in the actual
compiled source (confirmed via the permalink's `og:description` metadata), matching the
title. Using the correctly-spelled repro, compiled with `-T vs_6_0`.
