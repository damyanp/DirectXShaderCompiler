# #3693 — what "this reproduces" means

*Written before any compiler was run.*

## The report

Filed 2021-04-19 by @mstrgram, labelled `bug` + `diagnostic`. No comments on the thread.

A `uint3` is indexed with the **constant literal 3**:

```hlsl
const uint3 indices = g_indices.Load3(indexOffset);
float3 vertexNormals[3] = { g_vertices[indices[0]].normal,
                            g_vertices[indices[1]].normal,
                            g_vertices[indices[3]].normal };
//                                             ^ out of bounds: valid indices are 0..2
```

The attached `DefaultRT.hlsl` annotates the line with
`// THIS SHOULD LEAD TO A COMPILER WARNING AT LEAST`, so the ask is: **at minimum a
warning, ideally an error.** Reported command line:

```
dxc.exe /T lib_6_6 /Zpr /all_resources_bound /Zi /Od /Vn"..." /Fh"..." /nologo DefaultRT.hlsl
```

## This is a MISSING-DIAGNOSTIC issue: exit 0 is the bug

The reported symptom is **the absence of an error**. Therefore:

- **A clean compile (exit 0, no `error:`/`warning:` mentioning the index) IS the
  reproduction.** It is not evidence the issue is fixed.
- **The issue would be FIXED by a compile that fails**, or that emits a warning naming the
  out-of-range subscript. Any release that emits such a diagnostic is `does-not-repro`
  *for this issue* even though it "failed to compile".
- Because the predicate is absence-based, every release that fails to parse the repro for an
  unrelated reason (missing profile, unknown intrinsic, unrecognised root-signature flag)
  will also emit no such diagnostic and would score as a textbook reproduction. The predicate
  must therefore carry a **positive anchor** proving the compile actually got as far as
  emitting DXIL for the offending expression, and a control must prove the anchor
  discriminates.

## Reproduces if

Compiling the reporter's construct at `-T lib_6_6 /Zpr /all_resources_bound /Zi /Od`:

1. dxc exits **0**; and
2. DXIL is emitted for the shader containing `indices[3]`; and
3. **no diagnostic** (error or warning) is issued about the out-of-range vector element
   index.

## Does NOT reproduce if

dxc emits any diagnostic identifying the constant index 3 on a 3-element vector as out of
range — whether an error (FXC's `error X3504: array index out of bounds` shape) or a
warning. Any such diagnostic, at any severity, answers the report.

## What the correct behaviour is — and whether the language requires a diagnostic

This is the fork between `bug` and `enhancement-not-bug`, and it must be decided on what the
language says, not on what looks nicer:

- **A constant, statically-known out-of-range subscript on a fixed-size vector is not a
  case where the program can be correct.** Unlike a dynamic index, no runtime value can make
  `indices[3]` on a `uint3` in range, so this is diagnosable at compile time with no false
  positives.
- **The same access spelled as a swizzle is already an error** in DXC (`uint3.w` is not a
  valid component). If `v.w` is rejected and `v[3]` is not, DXC is inconsistent with itself,
  which strengthens the case that a diagnostic is intended rather than merely desirable.
  *To be measured, not assumed.*
- **FXC's behaviour is the relevant prior art** for a compiler DXC is meant to replace. If
  FXC issues `error X3504`, DXC accepting the same source silently is a regression in
  diagnostic quality against the compiler it replaced. *To be measured.*
- If instead the language leaves constant out-of-range vector indexing undefined **and** no
  other compiler diagnoses it, then the correct label is `enhancement-not-bug`: a request for
  a new diagnostic rather than a defect.

I will decide this from measurement (DXC's own swizzle behaviour, FXC, and the Clang HLSL
front end), plus what DXC does with the value at `-Od`, and record which way it went.

## Repro quality

`complete` — the issue attaches a self-contained `DefaultRT.hlsl` + `ShaderShared.h`, and
gives the exact command line. The attachment is downloaded to `attach/`. Caveat to check:
the attachment's root signature uses `RootFlags(XBOX_RAYTRACING)`, which stock DXC may
reject; if so, the committed repro must depart from the attachment there, and the departure
must be recorded — a compile that dies in the root-signature parser has measured nothing
about vector indexing.

## What would make this inconclusive

- If the only reachable configuration is one the reporter did not use.
- If DXC turns out to emit a diagnostic for the minimal case but not the reporter's case (or
  vice versa) — then the finding is about *which* contexts are checked, and the write-up has
  to say so rather than collapsing to a single yes/no.
