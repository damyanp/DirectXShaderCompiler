# Expected symptom — #5116 "Weird behavior when returning texture"

Repro quality: **complete** (issue body contains the full compute-shader source, unmodified).

## What the issue actually reports

The reporter's shader passes an uninitialized `Texture2D tex2d;` into `getTextureFromId(inout
Texture2D tex, uint textureId)`. That function only writes `tex` on the success path; on every
`return false;` path it leaves the caller's `tex2d` untouched. Because HLSL `inout` parameters
are copy-in/copy-out, the caller's variable is written back *unconditionally* at function exit,
so on the failure path the caller writes back whatever undefined value `tex2d` held. The
reporter's title/body call this "won't compile" — the shown repro is the version that fails.

Maintainer `llvm-beanz` (2023-11-01) reframes it with two distinct, separately-actionable
findings, and this is the operative description of the bug for triage purposes:

1. The code is arguably invalid HLSL (the `inout` write-back reads a possibly-uninitialized
   local), so a shader-model-dependent rejection is not inherently wrong.
2. **The real defect:** the shader "compiles successfully under SM 6.6" (accepted, no error)
   while presumably still failing/erroring at SM 6.5. The maintainer attributes the SM 6.6
   acceptance to `DXILCondenseResources` not looking through the SM 6.6 resource-handle
   annotations, so it fails to see that the resource value is unknown at that point. The
   quoted offending IR is `%2 = phi i32 [ %IMax, %if.end.9.i.i ], [ undef, %entry ]` feeding a
   resource index that reaches a `SampleGrad`/`SampleLevel` call — i.e. **SM 6.6 silently
   emits DXIL that samples an undefined resource handle**, which the maintainer states is a
   correctness bug ("SM 6.6 should also be failing... but isn't... causes correctness bugs").
   A second, separate ask (control-flow flattening removing the `phi` entirely so the code
   becomes valid either way) is explicitly labelled by the maintainer as a *second*, harder
   problem, not settled by this issue.

## Symptom predicate, decided before probing

"Reproduces" (`repros`) means finding #2 above still holds on `main`:

- Compiling the exact repro at `-T cs_6_6 -E main` **succeeds** (exit 0, no diagnostic), *and*
- Compiling the identical source at `-T cs_6_5 -E main` (same code, only the profile changed)
  behaves **differently** — i.e. the SM 6.5/SM 6.6 asymmetry the maintainer flagged is still
  present. (`NonUniformResourceIndex` requires SM 6.5+, so 6.5 is the floor for this repro.)

Both arms are needed: a fix could make 6.6 start diagnosing the shader (finding #2 resolved by
adding the check), or make 6.5 stop diagnosing it (also resolves the asymmetry, from the other
direction), or the control-flow flattening in finding #3 could make the `phi`/`undef` disappear
from the IR entirely regardless of what either profile's front end decides. Any of those counts
as `does-not-repro` for the specific asymmetry finding; only "6.6 clean, 6.5 not, and the same
`undef`-reaching-a-resource-consumer shape is still emitted" counts as `repros`.

If SM 6.6 already diagnoses the shader on `main`, or the generated DXIL for the 6.6 arm no
longer carries an `undef` feeding the resource path, that is `does-not-repro` for finding #2
even if the SM 6.5 diagnostic and the underlying "no control-flow flattening" complaint (finding
#3) are unchanged — those are explicitly a separate, still-open ask per the maintainer's own
"two separate issues" framing, and will be recorded as a separate line in the verdict rather than
folded into a single pass/fail.

`not-compiler-verifiable` is not expected to apply — this is entirely measurable via `dxc`
output on the two profiles plus disassembly of the SM 6.6 arm.
