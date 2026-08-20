# Expected symptom (written before running anything)

Issue: groupshared memory used through a hull shader's patch-constant function
(PCF) passes DXIL validation when the shader is compiled as a **library**
target (`lib_6_x`), even though the same shader compiled directly as a
standalone hull shader (`hs_6_x`) is correctly rejected.

Reporter's claim, precisely:

- `groupshared` is not a legal storage class for a hull-shader stage (it is
  meaningful only for compute-like thread-group stages). DXIL validation is
  supposed to catch a hull shader (or its patch-constant function) using it.
- When compiling the *same* source directly to `hs_6_x` (non-library target),
  validation correctly fails.
- When compiling the same source to a **library** target (`lib_6_x`) with the
  entry point exported via `[shader("hull")]`, validation only walks the
  function marked `[shader("hull")]` (`main`) and never checks the separate
  patch-constant function (`HSPatch`) that `main` references via
  `[patchconstantfunc("HSPatch")]`. Because `HSPatch` (not `main`) is the one
  touching `groupshared gs`, the check is skipped and the library compiles
  and validates cleanly.

**"Reproduces" means:** compiling the repro as `-T lib_6_3` (or another
library profile) succeeds validation (no diagnostic mentioning `gs` /
`groupshared` / the patch-constant function), while compiling the same source
directly as `-T hs_6_0 -E main` produces a validation error about the illegal
`groupshared` use. If the library-target compile also produces an error, the
symptom is fixed/does-not-repro.

Repro quality: **complete** — the issue links a Compiler Explorer repro
(https://godbolt.org/z/es4EY9hrY) with a self-contained HLSL hull shader
using `[shader("hull")]` / `[patchconstantfunc(...)]`, no external files
needed.
