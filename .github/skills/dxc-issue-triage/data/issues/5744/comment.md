> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5744](https://github.com/microsoft/DirectXShaderCompiler/issues/5744).

This is fixed on `main` as of commit `28d9915fa0` (PR
[#8707](https://github.com/microsoft/DirectXShaderCompiler/pull/8707),
merged 2026-07-31), but the fix was recorded against
[#8001](https://github.com/microsoft/DirectXShaderCompiler/issues/8001),
a later-filed issue describing the identical defect -- so this issue never
got closed. No shipped release contains the fix yet: the newest stable
release, v1.9.2607, was built 2026-07-29, two days before the fixing commit.

The derivative DXIL ops (`DerivCoarseX/Y`, `DerivFineX/Y`) were not marked
`convergent`, so LLVM's optimizer could legally sink a call to one of them
into a conditional block when its result was only used there -- exactly the
symptom this issue describes. #8707's own commit message says: "Previously,
the various derivative operations were not marked as convergent, which
allows their results to be sunk into conditional branches. This change
fixes that **and removes the workaround for this issue from the execution
tests**" -- that workaround-removal is the same `-opt-disable sink` change
this issue's own repro steps ask for.

Verified with a static repro (no GPU needed -- this is visible directly in
the disassembled DXIL): a compute shader computes `ddx(value)` unconditionally
and only stores it inside `if (WaveGetLaneIndex() == 3)`. Before the fix, the
derivative call itself moves into that conditional block:

```
%DerivCoarseX = call float @dx.op.unary.f32(i32 83, float %2)  ; -- inside the `if`
```

On `main` today, it stays where the source put it, unconditional:

```
%5 = call float @dx.op.unary.f32(i32 83, float %4)  ; DerivCoarseX(value) -- before the branch
```

Bisecting the stable release history (v1.4.1907 and v1.5.2010 can't run
this repro at all -- SM 6.6 postdates them, so they're excluded, not
"fixed"), every release from v1.6.2104 through v1.9.2607 reproduces the sink.
Compiler Explorer corroborates: [the linked
case](https://godbolt.org/z/vrMMYWr31) still shows the sink on CE's oldest
DXC (`dxc_1_6_2112`), and no longer shows it on CE's rolling `dxc_trunk`
build.

Current labels (`bug`, `correctness`) still fit. Suggest closing this as a
duplicate of #8001, which already carries the fix and its own closure.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
