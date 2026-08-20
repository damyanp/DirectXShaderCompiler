## Repro quality: complete

The issue body includes a full, minimal HLSL repro (hull shader with an oversized
`ControlPoint` input struct: `float4 position[100] : POSITION`) and an exact command line:

```
dxc -T hs_6_0 -E Hull repro.hlsl
```

## Expected symptom (per the issue)

DXC aborts with an `UNREACHABLE executed at .../HLSignatureLower.cpp:523!` /
`llvm_unreachable` hit, reached through:

```
Failed to allocate all input signature elements in available space.
UNREACHABLE executed at DirectXShaderCompiler/lib/HLSL/HLSignatureLower.cpp:523!
Aborted
```

on the reporter's Linux build ("DXC version HEAD (bdd7d9b0b9e8bfd28d6f25e8287f4a5fcd0d864c)").
"Reproduces" here means: dxc terminates via an internal failure (assert/unreachable trap,
not a normal diagnosed E_FAIL) when compiling this hull shader — the crash is what the issue
is about, not the underlying "too much IO" limitation itself, which all three commenters
agree is a legitimate error case (not something that should ever compile).

## Maintainer commentary already on the thread

- llvm-beanz (2023-11-15): agrees a better diagnostic is needed; believes the shape itself
  ("this much IO") is not fixable without a shader-model change.
- s-perron (2023-11-15): the original SPIR-V reporter (#3735) was fine with an error message;
  the ask here is specifically "avoid the crash", not "support this shader".
- tex3d (2023-11-15): identifies the root cause precisely — a legitimate, detectable error
  case ("packed elements must fit in 32 rows of 4-component vectors") was converted into
  `llvm_unreachable` by commit `21e56159eadc740c7ee6d01dbb6ec3251a769226`
  (diff line `HLSignatureLower.cpp` L502-L503 at the time), removing what used to be a normal
  diagnostic path.

So the actionable ask, per the thread's own consensus, is narrow: turn the
`llvm_unreachable` back into a diagnosed compiler error. It is not a request to support
arbitrarily large IO signatures.

## Predicate

`internal_failure` (any_of: exit-code-based classification per the skill's
`is_internal_failure()` table, backed by a text anchor on `HLSignatureLower.cpp` /
`Failed to allocate all input signature elements`, since the crash message is stable across
platforms in this case — Windows raises this as a Debug assert/abort, not a differently-worded
diagnostic).
