> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6001](https://github.com/microsoft/DirectXShaderCompiler/issues/6001).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

Compiling the repro from this issue (`HSPerPatchData` filled in with the
conventional tri-domain fields, since it isn't defined in the snippet above)
with `-T hs_6_0 -E MyHSMainPassthrough` still emits four
`dx.op.loadInput.f32` calls in `MyHSMainPassthrough`'s body and a non-null
`!dx.entryPoints` entry — exactly "Actual Behavior" as described: the
compiler does not recognize the pass-through case and still manually copies
every value.

```
%2 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 0, i32 %1)
%3 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 1, i32 %1)
%4 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 2, i32 %1)
%5 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 3, i32 %1)
...
!5 = !{void ()* @MyHSMainPassthrough, !"MyHSMainPassthrough", !6, null, !16}
```

Bisected across every stable release from v1.4.1907 (2019-07) through
v1.9.2607 (2026-07): the behavior has never differed. This is a missing
optimization, not a regression. Compiler Explorer confirms the same output
on both `dxc_1_6_2112` and `dxc_trunk`:
https://godbolt.org/z/nM3en9K5b

The other two problems in the report (a validator crash on a hand-crafted
null-entry pass-through representation, and a validator false-positive on a
declaration-only entry) both require authoring a DXIL module by hand — no
`dxc.exe`-driven compile from HLSL reaches either code path, matching the
report's own note that no such module could be made to validate. Those
weren't independently re-verified here.

An external issue, `HansKristian-Work/dxil-spirv#263` (2025-11-05, closed),
independently describes this as still "a planned feature" in DXC, over a
year after this was filed.

No change from the label suggestion here — `bug`/`crash`/`validation` are
all supported by the report; the crash/validation content just isn't
reachable from a plain HLSL compile the way the missing-optimization part
is.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
