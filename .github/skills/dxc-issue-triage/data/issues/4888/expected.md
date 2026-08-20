# Expected symptom — issue #4888

Title: "Dynamic resources validation errors: All metadata must be used by dxil.!55 = !{i32 1}"

## What was reported

Reporter compiles the attached HLSL with `-T ps_6_6 -E PSMain` (no other flags mentioned; the
linked Compiler Explorer URL in the body is Windows/DXC on godbolt, dynamic-resources/SM6.6
style). The shader declares a `static const Texture2D<float4> textures[2]` array whose two
elements are each initialized from a `ResourceDescriptorHeap[...]` lookup (a per-element dynamic
resource, SM6.6 "HLSL for dynamic resources"), then indexes that array with
`NonUniformResourceIndex(int(input.color.x))` and calls `.Sample`.

Reported compiler output:

```
error: All metadata must be used by dxil.!55 = !{i32 1}
```

This reads as a DXIL-validator-shaped error (a generic "some metadata operand went unused"
complaint), not an ordinary semantic diagnostic naming what the author actually did wrong.

## What "reproduces" means here

The primary claim to test is: **compiling the reporter's exact shader (`ps_6_6`/`PSMain`) still
produces this same class of confusing/generic metadata-validation error** (the literal `!\d+ =
!{i32 1}`-shaped "All metadata must be used by dxil" failure), rather than either (a) a clean
compile, or (b) a clear, actionable diagnostic that names the actual unsupported pattern.

## What the thread already established (read before probing)

- **mathforlife83** (comment 1): reports the same error, and separately notes that dropping
  `NonUniformResourceIndex` lets it compile but then crashes the AMD driver at pipeline-creation
  time — that half of the report is **not compiler-verifiable** (it is a downstream
  driver/runtime symptom, not something `dxc` alone can measure).
- **Keenuts** (COLLABORATOR, comment 2): reproduces the validation error on the reporter's
  pattern, and separately shows (a) a *compute-shader* variant using the same "static array of
  heap-indexed textures + `NonUniformResourceIndex`" pattern that **also fails**, and (b) a
  differently-written compute shader that manually selects the index with a ternary
  (`ResourceDescriptorHeap[(int)NonUniformResourceIndex(id == 0 ? id1 : id2)]`, no static
  array) that **does compile and emit DXIL**. Keenuts also reports that adding `-spirv` to the
  *first* (still-failing) compute-shader repro produces a **crash** — an assertion in
  `include/llvm/Support/Casting.h`: `Assertion 'Val && "isa<> used on a null pointer"' failed`,
  aborting the process. This is a **second, distinct signature** (an internal failure) from the
  reported metadata-validation error, and needs its own predicate — it is not established
  whether it fires on the *pixel-shader* repro from the issue body or only on Keenuts' compute
  restatement, so both need checking.
- **tex3d** (CONTRIBUTOR, comment 5 — the closest thing to an authoritative maintainer answer):
  states the HLSL is not something today's compiler can legalize, for two named reasons: (1)
  `NonUniformResourceIndex` is only handled when it wraps the *immediate* index of a bound
  resource array or a `*DescriptorHeap` built-in array — used anywhere else (e.g. indexing an
  intermediate array of resource *objects*, as here) the intrinsic's effect is **silently
  lost**; (2) turning a temporary array of resource objects into an array of indices into a
  `*DescriptorHeap` array (what would be needed to legalize this pattern) "isn't done yet". His
  conclusion: this issue should track **adding diagnostics** for these unsupported patterns, not
  a promise to make the code legal. So the "fixed" outcome this predicate should watch for is
  narrower than "compiles cleanly" — it is "produces a clear diagnostic *or* the pattern is now
  legalized", either of which would replace the current opaque validator error.

## Repro quality

`complete` — the issue body contains a full, standalone HLSL source and the exact command-line
target/entry point needed to reproduce (`-T ps_6_6 -E PSMain`). Comment 2 (Keenuts) supplies an
independently-confirmed compute-shader restatement of the same defect plus a working control,
which is useful as a variant/control but the primary repro is the reporter's own pixel shader.

## Predicates

1. **Primary — validation-error predicate** (`match.json`): present when the "All metadata must
   be used by dxil" diagnostic (or, more narrowly, the reporter's exact
   `!<N> = !{i32 1}`-shaped variant of it) appears in the combined output of the reporter's exact
   command. This is an ordinary DXIL-validation failure (E_FAIL), not an internal failure — no
   crash is claimed for the pixel-shader repro itself.
2. **Secondary — SPIR-V crash predicate** (`match-crash.json`, `internal_failure`): present when
   compiling the (compute-shader) repro with `-spirv` added trips the `isa<>` assertion Keenuts
   reported. Kept separate because it is a different observable signature (crash vs. diagnosed
   validation error) and may have a different history.

## Not-compiler-verifiable pieces

- mathforlife83's downstream AMD driver crash when `NonUniformResourceIndex` is *removed* is a
  runtime/driver claim, not something `dxc` can measure, and is out of scope for the probes
  below.
