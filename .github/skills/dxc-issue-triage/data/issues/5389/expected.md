# Expected symptom

Issue: `as` casts (`asuint`/`asint`/`asfloat`) applied to an integer-literal constant
swizzle (e.g. `(123).xx`, `0.xxx`, `(-1).xxx`) produce invalid DXIL.

The reporter's narrative, across the thread:

- The literal `(123)` (no suffix) is a 64-bit integer constant in DXC's non-HLSL-2021
  constant folding. Swizzling it (`.xx`, `.xxx`, `.x`) keeps it 64-bit. Passing that
  64-bit value/vector to `asuint`/`asint`/`asfloat` (`TranslateBuiltinIntrinsic` ->
  `TranslateAsUint` -> `TranslateBitcast`) bitcasts a 64-bit value into a call expecting
  a 32-bit-element type, producing a type-mismatched `call` argument.
  - In a **Debug (assert-enabled)** build this trips the LLVM assert in
    `CallInst::init` (`lib/IR/Instructions.cpp`):
    `assert((i >= FTy->getNumParams() || FTy->getParamType(i) == Args[i]->getType()) &&
    "Calling a function with a bad signature!")`.
  - In a **Release (NDEBUG)** build the assert is compiled out and the mismatched call
    is emitted, later failing DXIL validation with `Invalid record` /
    `Validation failed.` (this is exactly the original report's symptom).
- An explicit integer-typed constructor (`int2(123, 123)`, `int64_t3(0,0,0)`, `(0u).xx`,
  or an explicit `int(...)` cast) avoids the bug — only the *bare, unsuffixed, swizzled
  literal* triggers it.
- A maintainer (damyanp) states the underlying literal-typing issue is fixed by the
  HLSL 2021 (`-HV 2021`/`-HV 202x`) language mode, but that the **default (pre-2021)
  language mode remains affected by design** — the issue was moved to "dormant" as a
  known limitation of the legacy literal-typing rules, not something the team plans to
  backport a targeted fix for, though a contributed fix would be considered.
- damyanp separately notes that *one specific* case from the thread (the `f(b)/f(c)/f(d)`
  helper-function repro, comment
  https://github.com/microsoft/DirectXShaderCompiler/issues/5389#issuecomment-2332484091)
  "doesn't repro on the latest DXC" via a Compiler Explorer link — this is a narrower,
  possibly stale, claim about one variant and needs to be checked against the other
  repros in the thread, not assumed to cover the whole issue.

**"Reproduces" for this triage means:** compiling any of the thread's bare-swizzled-
literal-into-`as*`-cast repros with default (non-2021) language mode either (a) trips
the `CallInst::init` "bad signature" assert on a Debug/assert-enabled `dxc`, or (b)
produces a DXIL validation failure (`Invalid record` and `Validation failed.`) on a
Release/NDEBUG `dxc`, where the equivalent explicitly-typed-literal form compiles clean.
"Does not reproduce" means the bare-swizzled-literal form compiles cleanly and produces
valid DXIL with default language mode, or matches the explicitly-typed control.

Repro quality: **complete** — the issue body and comments (in particular the 2024-09-05
`sb.Store(0, asuint((123).xx))` comment and the 2024-09-05 `f(b)/f(c)/f(d)` comment)
give exact, minimal, ready-to-compile HLSL and the exact assert text/line. Using the
reporter's own text verbatim rather than reconstructing.
