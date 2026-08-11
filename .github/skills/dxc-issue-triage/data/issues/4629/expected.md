# Issue 4629 — expected symptom

Written **before** running anything, from the issue text and its three comments only.

## What the issue says

**Title:** "Internal llvm::cast<X> due to particular combination of class fields and methods"
**Filed:** 2022-08-31 by `siliconvoodoo`. Labels: `bug`, `crash`.

The body gives a complete, self-contained, already-minimised shader: an empty `struct PSInput`,
a `class SurfaceData_BasePBR` with one `float3` field, an `interface ISpecRough` declaring one
method, and a `class SurfaceData_NewPBR` that **inherits from both** the base class and the
interface, adds its own `float3` field, and implements the interface method. `PSMain` declares
a local of the derived class, writes `obj.albedo.x`, and returns `float4(obj.albedo, 1)`.

Command line as filed:

```
-T ps_6_5 -E PSMain -HV 2021
```

Reported effect, quoted verbatim from the body:

> Internal Compiler error: llvm::cast<X>() argument of incompatible type!

## What the comments add

1. **`damyanp`, 2024-07-31:** "Stil reproduces: https://godbolt.org/z/zv4WKPjdn" — a
   maintainer datapoint that this was still live 23 months after filing.
2. **`llvm-beanz`, 2024-07-31:** a full lldb backtrace of an **assertions-enabled Linux build**.
   The top frame is *not* a cast at all — it is
   `assert(false && "expected struct bitcast to only be used by lifetime intrinsics")` at
   `lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:2578`, in
   `SROA_Helper::RewriteBitCast`, reached from `RewriteForScalarRepl` →
   `DoScalarReplacement` → `SROAGlobalAndAllocas` → `SROA_Parameter_HLSL::runOnModule`.
   Note his stack was taken with `-T ps_6_6 -E main`, i.e. a slightly different profile and
   entry point from the filed repro — so profile 6.5 vs 6.6 is *not* load-bearing for him.
3. **`llvm-beanz`, 2024-07-31:** filed `microsoft/hlsl-specs#291` to track **removing
   `interface` from a future HLSL version**, calling interfaces "broken and can't be used in
   many of the contexts that would make them interesting". This is a language-direction
   statement, not a fix.

Pre-existing cross-references (checked before any measurement, read-only):
`o3de/o3de-azslc#58` (2022-08-31) and `microsoft/DirectXShaderCompiler#6228` (2024-01-31).

## Therefore: "this reproduces" means

**DXC fails internally while compiling the filed repro** — it does not finish codegen and it
does not emit an ordinary diagnosed error. Concretely, at least one of:

- an assert trap in the Debug ground-truth build (exit `0x80000003`, or `0xE0000001` if the
  assert arrives as a C++ exception), most likely the `RewriteBitCast` assert above;
- an access violation (`0xC0000005`);
- the bad-cast HRESULT/text path: `hlsl::Exception(DXC_E_LLVM_CAST_ERROR)`, which the driver
  surfaces as **E_FAIL `0x80004005`** together with `llvm::cast<X>() argument of incompatible
  type!` in the output — the reporter's exact wording;
- on a Linux/CE build, a signal exit (SIGILL/SIGSEGV/SIGABRT → 132/139/134).

**"This does not reproduce"** means the shader compiles to DXIL and exits `0`.

### What must NOT be counted as a reproduction

- Any **ordinary diagnosed error**. On Windows those also exit `0x80004005`, so exit status
  alone cannot separate them from the bad-cast path — a plain syntax error, an unknown
  profile, and a DXIL validation failure all look identical at the exit-code level. A run
  that prints `error:` and no internal-failure marker is a *clean diagnosed failure*, not a
  crash.
- Any `invalid-probe` shape: a release rejecting `ps_6_5`, rejecting `-HV 2021`
  (`Unknown HLSL version: 2021`), or rejecting `interface`/`class` inheritance as unimplemented.
  Those releases never reached `SROA_Parameter_HLSL` and measured nothing.

## Predicate plan

`internal_failure`, **not** a text match on `llvm::cast<X>`. Three reasons, all of which the
issue itself demonstrates:

- The Debug build's signature (per llvm-beanz's stack) is an **assert about bitcasts**, whose
  message contains no `cast<X>` string at all. A `contains` predicate on the reported message
  would score the ground-truth Debug build as clean.
- The Windows build prints `llvm::cast<X>()` where CE's Linux build prints plain `cast<X>()`.
- An internal failure may print nothing at all on older releases.

## Repro quality (recorded before measuring)

**`complete`** — the body carries the entire shader and the exact command line; nothing has to
be reconstructed or guessed.

## Predictions I am committing to, so they can be wrong

- Ground truth (`main-debug`, 1.9.0.5433, `13730886e`) fails internally, most likely as a
  trapped assert at `ScalarReplAggregatesHLSL.cpp` near line 2578.
- History: unknown. `-HV 2021` will likely make the oldest releases `invalid-probe`
  (HLSL 2021 shipped around v1.6.2104), and `ps_6_5` limits how far back the profile exists.
- I do **not** know whether older releases crash, diagnose, or compile cleanly. That is what
  the scan is for.
