> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5587](https://github.com/microsoft/DirectXShaderCompiler/issues/5587).

This no longer reproduces on `main` (commit `89e2f98e2`; local build
metadata points to a fork-local merge commit, but the compiler source
tree matches public `89e2f98e2`).

`SomeBitfield val = (SomeBitfield)0;` now compiles cleanly with
`-T cs_6_6 -HV 2021`, in both the field order reported as failing
(`SomeEnum field1 : 2; uint32_t rest : 30;`) and the reordered form the
issue said worked. The generated DXIL stores a concrete `0` into the
struct's storage word (not `undef`):

```
call void @dx.op.rawBufferStore.i32(i32 140, %2, i32 0, i32 0, i32 0, i32 undef, i32 undef, i32 undef, i8 1, i32 4)
```

Bisecting the public releases: it still failed with the exact reported
diagnostic through v1.8.2502 (2025-02-20) —

```
error: cannot convert from 'literal int' to 'SomeBitfield'
```

— and is clean at v1.8.2505 (2025-05-24). (v1.4.1907 through v1.6.2106
cannot probe this because `-HV 2021` is unsupported.)
[Compiler Explorer](https://godbolt.org/z/xG8Kj4v58) shows the same
contrast: CE's oldest DXC (1.6.2112) fails, `dxc_trunk` compiles.

The order-dependence appears resolved: both member orderings now behave
the same.

The broader design question raised in this thread (should HLSL adopt
C/C++ aggregate-initialization rules, e.g. `SomeBitfield val = {};`)
is untouched by this fix and remains open per the linked
`hlsl-specs` proposal/issue.

Suggested labels: no change (`bug`, `hlsl2021`).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
