# #3726 — "Sema should not allow assignment to resource"

Written **before running any compiler**, from the issue text alone (issue.json, fetched
2026-08-07). Filed 2021-04-29 by jaebaek; one maintainer comment from damyanp 2024-07-16.

## Repro quality

`complete`. The body carries a self-contained shader: three global resources `r0`/`r1`/`r2`,
three more globals `x0`/`x1`/`x2`, a `getResource()` taking `out` parameters of resource type
that assigns the `r*` globals into them, and a `float4 main() : SV_Target` that calls it and
samples through the results. It names no target profile; `SV_Target` plus `Sample` makes it a
pixel shader, so `ps_6_0` — the oldest profile that can express it, per SKILL.md step 6.

Nothing has to be invented. One thing has to be *decided*: damyanp's 2024 comment says
"(For reference, x0, x1 and x2 in the repro should be static)". The body's `x0`/`x1`/`x2` are
global resource **declarations** (i.e. bound resources), not local/static variables, so passing
them as `out` arguments is not quite the local-alias case PR #3721 was about. The as-filed body
is the primary repro; the `static` restatement is a **variant**, and if the two behave
differently that difference is itself a finding.

## What is being claimed

Read carefully, the issue is **not** "DXC accepts this". It is a claim about *where* and *how
well* the rejection happens. Three separate assertions, and they need separate answers:

1. **"DXIL backend reports error if the code has assignments to resources."** The DXIL path
   already fails — but the diagnostic comes out of the **backend**, not the front end.
2. **The title: Sema should have rejected it.** So the defect is that the front end
   (`tools/clang/lib/Sema/`) is silent, and the error only appears once DXIL lowering runs.
   Confirming this needs more than an output observation: it needs the emitting site.
3. **The SPIR-V backend does not report the error at all.** The body says spirv-opt
   legalization "handles the code and somehow generates the legal code", and asks for a
   SPIR-V analysis (detect `OpStore` to a resource) or work in spirv-val — because the
   assignment is not locally detectable at `a0 = r0`.

## What "this reproduces" means

**All three of the following, on the ground-truth build:**

- **(a)** `-T ps_6_0 -E main repro.hlsl` fails, and the failure is a **DXIL-lowering /
  backend** error — one with no `<file>:<line>:<col>:` source location, or one whose emitting
  site is under `lib/HLSL/` or `lib/DXIL*` rather than `lib/Sema/`.
- **(b)** **No Sema diagnostic is emitted.** A positive match on (a) is itself evidence of
  this: a fatal front-end diagnostic stops compilation, so the backend error could not be
  reached if Sema had rejected the shader. To corroborate independently I will check
  `-Zs` (syntax-check only, front end only) and read `lib/Sema/` for any such check.
- **(c)** `-T ps_6_0 -E main -spirv repro.hlsl` **succeeds** (exit 0, a SPIR-V module on
  stdout), i.e. the two backends disagree on the same source.

**"Does not reproduce"** would be: the front end now emits a Sema diagnostic pointing at the
assignment (or at the call), on *both* targets. That is the fix the issue asks for.

**"Changed behavior"** would be: it is still not diagnosed in Sema, but the DXIL error has
moved or disappeared, or the SPIR-V path now errors from *its* backend (which would resolve
assertion 3 while leaving the title's request open), or the SPIR-V output changes shape
materially. **Collation correction:** this originally called the last case a visible
miscompile; because the issue expects this source to be rejected, emitted output can establish
acceptance and lowering shape, not a miscompile.

Note the sign of assertion 3: the issue reports SPIR-V **succeeding** as the bad outcome. So a
clean `-spirv` exit is a *reproduction*, not a pass. That inversion is the easiest thing to get
backwards here, and it is why (c) is written down before anything is run.

## Predicates I intend to write

Because the reported symptom *is* a diagnostic, SKILL.md step 6 warns that feature-absence
markers and the symptom become the same observation, and step 4 says to write the diagnostic
in verbatim rather than approximate it. I will pin the exact text after the first run, but the
*shape* is fixed now:

- **`match.json`** — a **positive-only** regex on the DXIL backend error. Positive-only is
  deliberate and load-bearing: the capture contains two dxc invocations, so any absence clause
  over the combined text would be answered by the other invocation. It also makes the
  predicate immune to the failed-parse trap. And it needs no separate "Sema was silent" clause,
  because *reaching* a DXIL-lowering error already proves the front end accepted the shader.
- **`match-sema.json`** — **inverted polarity: a match means the issue is FIXED.** A front-end
  diagnostic attributed to a source line of `repro.hlsl`. I expect this to match nowhere,
  including on `main`. Bisected separately so that "Sema learned to reject this" and "the DXIL
  backend error changed shape" cannot collapse into one verdict.

Controls, per SKILL.md step 4's missing-diagnostic rule (both halves are required):
- a shader DXC **does** diagnose in Sema, proving the front-end diagnostic pipeline is reached
  and that `match-sema.json` can fire at all (`--expect match` for `match-sema.json`);
- a shader that is simply **correct** resource-passing code, proving neither predicate fires on
  everything (`--expect no-match`).

## History

The bisection floor is v1.4.1907, which predates the 2021-04-29 report by 21 months, so a full
history is expected to be available for the DXIL half. **The SPIR-V half has a higher floor**:
v1.4.1907 answers `SPIR-V CodeGen not available`, which is a feature-absence marker and an
`invalid-probe`, not a clean run. Assertion (c) must therefore be read only from v1.5.2010
onward. v1.5.2003 is not in the bisectable set; it predates the report and is not needed here.

## Prediction

I expect this still reproduces: assignment-to-resource is a long-standing DXC shape and I know
of no Sema check for it. I expect the DXIL error to be one of the "local resource not
guaranteed to map to unique global resource" family from `lib/HLSL/`. I expect `-spirv` to
compile clean. **If any of that is wrong the observation wins, and this file is the record
that the prediction came first.**
