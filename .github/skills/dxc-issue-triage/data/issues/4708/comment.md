> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4708](https://github.com/microsoft/DirectXShaderCompiler/issues/4708).

**This is an enhancement, not a DXC defect.** Non-member operator overloading
was never an HLSL 2021 capability. The feature has since been accepted in
[hlsl-specs proposal 0008](https://github.com/microsoft/hlsl-specs/blob/main/proposals/0008-non-member-operator-overloading.md),
targeting **HLSL 202y**. The standing 2023 comment's **202x** target is now
stale.

Current DXC rejects the declaration deliberately:

```text
repro.hlsl:15:12: error: overloading non-member 'operator+' is not allowed
```

All 16 stable releases that can express HLSL 2021 templates reject the free
operator while the member-operator control compiles; the four older releases
are unmeasurable, not clean. v1.8.2403 added the declaration-site diagnostic
above; that was a diagnostic improvement, not a regression.

Clang trunk compiles the issue shader. An observable variant proves the
operator is resolved and evaluated:

```llvm
  call void @dx.op.bufferStore.f32(i32 69, %dx.types.Handle %1, i32 %2, i32 0, float 4.000000e+00, float undef, float undef, float undef, i8 1), !dbg !134
```

Side-by-side evidence: <https://godbolt.org/z/9esTrW5ox>. This establishes
Clang's current behaviour, but not whether it is an intentional implementation
of proposal 0008 rather than inherited C++ overload resolution.

Suggested disposition: keep open as an accepted language feature (`hlsl-next`
plus `enhancement`), or consolidate with the spec proposal if it is not planned
for DXC itself.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
