# Triage — #1306 Validation for sync in varying flow control

| | |
| --- | --- |
| Opened | 2018-05-24 |
| Labels | `enhancement`, `validation` |
| Repro quality | **complete** (full shader supplied in the issue) |
| Status vs `main` | **repros** — feature still absent |
| History | **always-repro'd** (v1.4.1907 → v1.9.2607) |
| Confidence | **high** |
| Suggested action | **enhancement-not-bug** — needs a product decision, not a fix |

## What was tested

The compute shader from the issue, verbatim: a `GroupMemoryBarrierWithGroupSync()` inside an
`if` predicated on `SV_DispatchThreadID`.

`dxc -T cs_6_0 -E main repro.hlsl`

## Result

Compiles cleanly (exit 0) with **no diagnostic whatsoever**. The generated DXIL confirms the
barrier really is inside divergent control flow:

```llvm
  %8 = icmp eq i32 %7, 0
  br i1 %8, label %9, label %16

; <label>:9
  call void @dx.op.barrier(i32 80, i32 9)  ; Barrier(barrierMode)
```

FXC rejects the same shader with `error X3663: thread sync operation found in varying flow
control`. Behaviour is unchanged across every release from v1.4.1907 to v1.9.2607.

## Assessment

The request is still entirely unimplemented, so "still reproduces" here means "still not
built" rather than "still broken".

Worth noting the issue already contains most of a decision:

- 2018 — SPIR-V maintainers (`antiagainst`, `dneto0`) argued this belongs in SPIRV-Tools
  validation, and that without precise value information the best achievable result is a
  *warning* with false positives, not an error.
- 2018 — `kayru` countered that it is equally wanted for the DXIL path.
- 2024 — `damyanp`: "If we had uniformity analysis we could look into solving this in clang",
  referencing `microsoft/hlsl-specs#246`.

So the real blocker is uniformity analysis, and the likely home is Clang rather than DXC.

**Suggested handling:** this is a candidate for redirecting to the HLSL specs / Clang work
rather than remaining an open DXC bug. It should not be closed as "cannot reproduce" — the
repro is good and the gap is real.

---

## Shareable repro

<https://godbolt.org/z/c3ojha8KW> — FXC 10.0.19041 alongside DXC 1.6.2112 and trunk.

This link demonstrates the request directly rather than by assertion. FXC fails the shader:

    error X3663: thread sync operation found in varying flow control, consider reformulating
    your algorithm so all threads will hit the sync simultaneously

while both DXC versions compile it cleanly and emit code. That contrast *is* the feature
request, in one screen.
