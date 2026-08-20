> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5573](https://github.com/microsoft/DirectXShaderCompiler/issues/5573).

Still reproduces on `main` (Debug build, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and on every stable release
that can even express this shader — `v1.6.2104` (2021-04-20, the first release with
`ResourceDescriptorHeap`/`cs_6_6`) through `v1.9.2607` (2026-07-29). `v1.4.1907` and
`v1.5.2010` reject the profile itself (`error: invalid profile cs_6_6`) and predate the
feature, so they're not evidence of a fix, just of the feature not existing yet.

Compiler Explorer, both CE's oldest DXC and current trunk, same result:
https://godbolt.org/z/r6TGKo7sv

```
error: validation errors
<source>:1: error: External declaration '\01?buffer@@3URWByteAddressBuffer@@A' is unused.
Validation failed.
```

The root cause: `DxilCondenseResources.cpp`'s `UpdateResourceSymbols` asserts
`GV->user_empty()` before replacing a resource's DXIL symbol with `undef`, on the assumption
that the resource's global variable has already been fully lowered away. When `buffer` is
used *before* being reassigned to a `ResourceDescriptorHeap` handle, that assumption is false
— the global still has a real user (the earlier `Store`) — and in a Debug build the assert
traps (confirmed by a local build: `Internal compiler error: Terminal Error 0x80000003`,
`!(GV->user_empty())`, `DxilCondenseResources.cpp:1984`). Release builds compile the assert
out, so execution falls through: the resource's DXIL symbol still gets replaced with
`undef`, the now-stale global is left behind, and the validator reports it as unused —
exactly this issue's symptom. Both are the same defect; only the build configuration decides
which face you see. The assert itself predates Shader Model 6.6 by about four years
(`dc3ad5efe`, 2018), so it was never written to guard this pattern specifically.

A control that uses `ResourceDescriptorHeap` alongside a static resource, without the
reassign-then-reuse pattern, compiles cleanly — this is specific to reassigning a resource
variable that was already used, not to mixing static and dynamic resources in general.

@llvm-beanz's root-cause read in the earlier comment still holds, and the open design
question raised there — whether reassigning a global resource declaration should be
diagnosed at compile time rather than silently mis-compiled — remains unresolved.

Suggested labels: no change (`bug`, `dxil`, `correctness` already fit).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
