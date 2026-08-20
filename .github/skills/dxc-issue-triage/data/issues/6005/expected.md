# Expected symptom (written before running anything)

Issue title: `[Assert Triggered] MaybeODRUseExprs.empty() && "Leftover expressions for odr-use
checking"`.

Reporter (devshgraphicsprogramming) hits a Debug-build assert with message
`MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking"` after adding, in
their own namespace, typedefs named `vector`/`matrix`-shaped aliases (actually: typedefs whose
names collide with HLSL's own scalar/vector "type sugar" spellings such as `float32_t`,
`uint32_t3`, etc., built from the builtin `vector<T,N>`/`matrix<T,R,C>` templates) alongside
HLSL's own builtins. They say the shader still compiles (Release builds swallow the assert
because `assert()` compiles out under `NDEBUG`), so the only user-visible effect on a Release
compiler is none — this is purely a Debug-assert / internal-consistency issue, not a
compile-time failure or wrong-codegen bug as reported.

A collaborator (s-perron, 2024-08-23) confirmed it fails in Sema and confirmed it **still
reproduces without `-spirv`** (i.e. it is not SPIR-V-specific), then later (2024-09-16) posted
a concrete repro command and the exact assert location:

```
dxc -HV 202x -T cs_6_7 -Zpr -enable-16bit-types -fvk-use-scalar-layout -Wno-c++11-extensions \
    -Wno-c++1z-extensions -Wno-gnu-static-float-init -fspv-target-env=vulkan1.3 \
    -fspv-debug=source -fspv-debug=tool s.hlsl
Error: assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")
File:
.../tools/clang/lib/Sema/SemaDecl.cpp(11119)
Func:   ActOnFinishFunctionBody
```

using the source at https://godbolt.org/z/zGaGPaKK3 (a public Compiler Explorer link posted by
pow2clk on this same issue thread — safe to reuse per this repo's public-repro policy).

## What "reproduces" means here

The compiler process aborts/traps due to an assertion failure (Debug-build internal failure)
while compiling `repro.hlsl` with the command above, rather than completing the compile
normally (with or without diagnostics). Concretely: `internal_failure` per the triage
predicate table (Debug assert typically exits `0x80000003` when trapped, or `0xE0000001` if it
throws as a C++ exception before an installed handler — measure which one this build uses).

"Does not reproduce" means the same command completes (exit 0, or an ordinary diagnosed
error/warning) with no internal-failure signature.

## Repro quality

`complete` — a maintainer (s-perron) posted the exact working command line and confirmed the
crash and assert message/location on their own Debug build; the source is recovered verbatim
from pow2clk's public Compiler Explorer short link referenced in the same comment thread.
