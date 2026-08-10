# #4486 — expected symptom (written before running any compiler)

**Issue:** [SPIR-V] Nested static 'for' loops with unroll translate to 'while( true )' loops
with actual branches — <https://github.com/microsoft/DirectXShaderCompiler/issues/4486>
Filed 2022-05-28 by OrangeeZ against DXC **1.6.2104.52**. Label: `spirv`. Milestone: `Dormant`.

## What was reported

A pixel shader contains a doubly-nested `for` loop, both levels marked `[unroll]`, with
iteration bounds that are constant at compile time (`j < 3`, `k < 4 - j - 1`). The reporter
expects full unrolling. Instead the emitted SPIR-V still contains loops: their decompiled view
shows two `while(true)` constructs with `Phi` nodes and `break`s, i.e. real back-edges and
branches. Consequences reported on hardware (Mali/Adreno, warp divergence, malioc load/store
bottleneck, ~8x slower) are *not* compiler-verifiable and are not part of this predicate.

The reporter also states the **workaround** works: replacing the outer loop with three explicit
calls to a helper containing only the inner `[unroll]` loop produces "perfectly flat" code.
That contrast is the control this triage must reproduce.

`[unroll]` for **DXIL** is stated by pow2clk (2022-06-29) to work; the issue is SPIR-V only,
confirmed by the reporter ("Yes, we're only interested in SPIR-V output").

## Repro quality

**complete** — but supplied by a maintainer, not the reporter. The issue body's snippet is a
fragment (no entry point, undefined arrays, unused result, so the loops are dead). pow2clk's
2022-06-29 comment contains a self-contained shader with the entry point, resources,
`luminance()` and both loop levels reachable. That comment version is what `repro.hlsl` will
hold, verbatim apart from whitespace normalisation. Note it uses the *manually unrolled*
`boxMedianOneStep(0/1/2)` form in `boxMedian()`; the nested-loop form the issue is about is
quoted separately in the reporter's 2022-06-14 comment (item 2) and must be substituted back
in. That substitution is the one deliberate edit, and it restores exactly what the title
describes.

No profile is named anywhere in the thread. `ps_6_0` will be used: it is the oldest profile
that can express the shader, which is what keeps old releases probeable.

## "This reproduces" means

Compiling `repro.hlsl` with `-T ps_6_0 -E PS_bright_pass -spirv` produces a SPIR-V module for
the fragment entry point that **still contains a structured loop** — at least one
`OpLoopMerge`. Full unrolling would leave none: `OpLoopMerge` is emitted only for a loop
header, so a straight-line function cannot contain one.

Two clauses, both required, so that neither a failed compile nor a broken instrument can
manufacture either answer:

1. **anti-vacuity / instrument self-test:** the output must contain `OpEntryPoint Fragment`,
   which only a successful SPIR-V compile *whose disassembly actually reached stdout* can
   produce. If this clause fails, the run measured nothing — that release is unmeasurable,
   **not** clean.
2. **behaviour:** the output contains `OpLoopMerge`.

**does-not-repro** would therefore be: `OpEntryPoint Fragment` present, no `OpLoopMerge`
anywhere.

## Predicted hazards (recorded now so the outcome cannot be rationalised later)

- **SPIR-V bisection floor.** v1.4.1907 (and the v1.5.2003 prerelease, which is outside the
  search by policy) answer `SPIR-V CodeGen not available`. Any history statement must be "for
  as long as it is possible to check", never "since it was filed".
- **The predicate reads a disassembler.** `dxc -spirv` without `-Fo` prints SPIR-V assembly
  from its bundled SPIRV-Tools. If a release's disassembler changed what or where it prints,
  clause 1 fails and the probe would look like a fix. Every probed release therefore gets an
  instrument self-test, not just `main`.
- **`OpLoopMerge` in the wrong place.** A `while`/`do` loop anywhere else in the module would
  satisfy clause 2 for free. The repro has no other loop, and the controls below pin this down.

## Controls to run (declared before measuring)

| shader | expectation | what it proves |
| --- | --- | --- |
| `control-manual-unroll.hlsl` — the reporter's workaround: outer loop replaced by three `boxMedianOneStep` calls, only innermost `[unroll]` loops left | `no-match` | the predicate discriminates. A predicate that also fires on the shape the reporter calls "perfectly flat" measures nothing |
| `control-runtime-loop.hlsl` — same shader with a loop whose trip count is a uniform, so it cannot be unrolled | `match` | the `OpLoopMerge` detector is alive; a no-match everywhere would otherwise be indistinguishable from a dead regex |
| `control-trivial.hlsl` — `float4 main() : SV_Target { return 0; }` under `-spirv` | `no-match` | separates "this release has no SPIR-V backend / prints nothing" from a real clean result. Run on **every** probed release, not only ground truth |

## Possible outcomes and what each would mean

- **repros** — SPIR-V still has `OpLoopMerge`; matches s-perron's 2023-03-10 explanation that
  spirv-opt only unrolls innermost loops with known bounds.
- **does-not-repro** — SPIR-V fully unrolled. Would mean spirv-opt gained outer-loop unrolling
  since 2022; would need a bisected release boundary before being believed.
- **changed-behavior** — e.g. compiles but now warns that `[unroll]` could not be honoured, or
  unrolls one level but not the other. Worth distinguishing: a diagnostic where there was
  silence is a real, reportable improvement even if the codegen is unchanged.

## Out of scope for this triage

The GPU-side measurements (warp divergence, malioc cycle counts, the 8x figure) need hardware.
Nothing here attempts to confirm or deny them. The compiler-verifiable claim is only "the
`[unroll]`-marked nested loops are still loops in the SPIR-V".
