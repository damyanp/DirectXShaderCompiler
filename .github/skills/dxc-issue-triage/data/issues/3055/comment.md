> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3055](https://github.com/microsoft/DirectXShaderCompiler/issues/3055).

Still reproduces on `main` (1.9.0.5433, `ab5400907`, Debug), and on **all 20 release binaries
from v1.4.1907 (2019-07) through v1.9.2607** — a full linear scan, not just the endpoints. The
v1.4.1907 output is byte-identical to today's, caret art included.

The "compiles successfully now" comment from 2023-07-14 refers to the *original* example,
which was replaced on 2023-09-27. The example currently in the body produces exactly the
output quoted beneath it.

**Repro:** <https://godbolt.org/z/M7e5Yrr36> (FXC · DXC 1.6.2112 · DXC trunk · `hlsl_clang_trunk`)

### The intended overload is the one candidate that is suppressed

Passing the *correct* `SamplerState` but one argument lists **four** candidates — requires 2,
3, 4, 5 arguments. The issue's shader lists **three** — 3, 4, 5. The 2-argument overload is the
only one dropped, so the notes describe only overloads that were never being called.

Not specific to `Sample`: `tex.GatherRed(samp, coord)` with the same mistake gives the same
shape — notes requiring 3, 4, 6 and 7 arguments, nothing about the sampler type.

### Where the note is dropped

`DeduceTemplateArgumentsForHLSL` selects candidates by argument count, then calls
`MatchArguments`, which computes `badArgIdx` — "The first argument to mismatch if any"
(`SemaHLSL.cpp:5396`). On mismatch the caller does `++cursor; continue;`
(`SemaHLSL.cpp:11364-11369`) and the value is discarded, so the loop falls out to a bare
`TDK_NonDeducedMismatch` (`SemaHLSL.cpp:11456`) with no `FirstArg`/`SecondArg`. `SemaOverload.cpp:9355-9360`
then elides the note explicitly:

```cpp
// HLSL Change Starts
// The implementation for template argument deducation does not yet provide
// FirstArg and SecondArg information for failure cases; ellide the note in
// this case.
if (FirstTA.isNull() || SecondTA.isNull()) return;
// HLSL Change Ends
```

The remaining notes come from candidates rejected on arity before deduction, which is why the
arity complaints are all that survives.

### Both comparison compilers name the type

FXC prints the candidate signatures, each showing `SamplerState` first:

```
error X3013: 'Sample': no matching 2 parameter intrinsic method
error X3013: Possible intrinsic methods are:
error X3013:     Texture2D<float4>.Sample(SamplerState, float2|half2|min10float2|min16float2)
```

`hlsl_clang_trunk` already emits the wanted note:

```
note: candidate function not viable: no known conversion from 'SamplerComparisonState' to 'hlsl::SamplerState' for 1st argument
```

Controlled: with `SamplerState samp` the Clang pane produces no overload error at all and
fails later in DXIL lowering, which the repro never reaches. Clang's HLSL front end already
emits the note this issue asks for.

**Labels** — suggest adding `fxc-disagrees` (measured above) and `usability` (plausible slip,
misdirecting message). `tech-debt` and `diagnostic` still fit; nothing to remove.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
