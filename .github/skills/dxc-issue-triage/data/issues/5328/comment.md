> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5328](https://github.com/microsoft/DirectXShaderCompiler/issues/5328).

Still present, unchanged, on `main` at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
`HLMatrixBitcastLowerPass::lowerMatrix`, `lib/HLSL/HLMatrixBitcastLowerPass.cpp:244`:

```cpp
} else if (StoreInst *ST = dyn_cast<StoreInst>(U)) {
  Value *V = ST->getValueOperand();
  if (VectorType *Ty = dyn_cast<VectorType>(V->getType())) {
    IRBuilder<> Builder(LI);   // should be Builder(ST)
```

`LI` and `ST` are bound in sibling arms of the same `if`/`else if` chain,
so `LI` is guaranteed `nullptr` here: the earlier `dyn_cast<LoadInst>`
had to fail for control to reach the `StoreInst` arm. `IRBuilder<>`'s
single-`Instruction*` constructor dereferences its argument immediately
(`IP->getContext()`), so reaching this branch is an unconditional null
dereference, not a latent risk. `git blame` traces the line back past
this clone's shallow-history boundary (2025-06-03), so it's been there
at least that long.

This pass is only reachable via `dxc -T lib_6_x -link ...`
(`DxilLinker::RunPreparePass`), and I wasn't able to construct a
minimal HLSL library-link input that reaches this exact branch.
`AlwaysInlinerPass`, which runs immediately before this pass in the
same pipeline, fully inlines a cross-module call whenever the link
resolves to a single shader entry point, before a fake-matrix-typed
`Store` can ever reach this code. So the verdict here is based on the
source and the `IRBuilder` API contract, not an executed crash of this
exact branch.

Separately: the 2026-04-27 comment's attached repro does crash `main`
(confirmed, exit `0xE0000001`), but its stack trace is
`HLMatrixLowerPass::replaceAllVariableUses` → `checkGEPType`
(`lib/HLSL/HLMatrixLowerPass.cpp`) — a different file, function, and
fault from the one reported here. So it should be treated as a separate
bug, not as corroborating evidence for this typo.

Suggest adding `crash` (the code is an unconditional null dereference
once reached, not just a style issue) alongside the current
`matrix-bug`/`tech-debt`, and `shader-linking` (the bug lives entirely
in a pass that only exists for `-link`).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
