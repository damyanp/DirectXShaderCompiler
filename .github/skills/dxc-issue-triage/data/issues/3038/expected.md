# Expected symptom - #3038 DXR 1.1: TraceRayInline after TraceRay crashes compilation

**Repro quality: partial -> agent-constructed.** The shape is given but every argument is
elided (`TraceRay(...)`), there is no complete shader, no profile and no entry point. A full
raygeneration shader must be constructed. Flagged `agent-constructed` accordingly.

## What was reported (2020-07-14)

Calling `TraceRay(...)` and then `RayQuery::TraceRayInline(...)` **in the same shader** crashes
compilation with:

```
Val->VTy->ContainedTys was 0xFFFFFFFFFFFFFFFF.
```

Note this crashes the **compiler**, not the GPU - despite the DXR subject matter this is
compiler-verifiable.

## The critical detail is in the comments, not the body

@tex3d (2020-07-17): the trigger is **reusing the same `RayDesc` instance** for both calls.
Passing a copy avoids it:

```hlsl
RayDesc ray2 = ray;
q.TraceRayInline(..., ray2);
```

The body alone does not say this, so a repro built from the body alone might not reproduce at
all, and would produce a false `does-not-repro`.

## The symptom has already changed shape once

@donguklim (2022-12-24) reported it still failing but with a **different** message:
`llvm::cast<X>() argument of incompatible type!`. The original text is a Debug assert; the
later one is a Release-build failure. A predicate keyed to either message string would score
the other build as clean. Use `internal_failure`, which is signature-independent.

## The symptom reproduces if

dxc fails **internally** (assert / access violation / fatal error) on the shared-`RayDesc`
shader. Any well-formed diagnostic is NOT the symptom.

## Control (supplied by @tex3d)

The separate-`RayDesc` variant must compile **cleanly**. If both variants crash, the repro is
not isolating what the issue describes. If neither crashes, the bug is fixed.
