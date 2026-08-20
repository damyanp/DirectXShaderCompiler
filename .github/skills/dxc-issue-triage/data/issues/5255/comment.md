> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5255](https://github.com/microsoft/DirectXShaderCompiler/issues/5255).

Still reproduces on current `main` (89e2f98e2, 2026-08-19). Running `dxr -remove-unused-functions -remove-unused-globals -E vs_main` on the shader in the issue produces output byte-identical to what's quoted above: both `cbuffer` blocks are kept (unused cbuffers are intentionally kept by this rewriter), but the `struct InstanceDataStructType { ... };` declaration they both reference is deleted — the emitted HLSL references an undeclared type and will not recompile.

Root cause: `InstanceDataStructType` is only referenced as the **element type of an array-typed** cbuffer member (`InstanceDataStructType mData[2];`). `VisitHLSLBufferDecl` in `tools/clang/tools/libclang/dxcrewriteunused.cpp` marks a cbuffer member's type as "used" via `memberDecl->getType()->getAsTagDecl()`, and `getAsTagDecl()` does not unwrap array types — so it returns null for an array member and the struct is never marked used. A same-shaped control with a **scalar** member (`InstanceDataStructType mData;`, no array) correctly keeps the struct declaration; only the array form loses it. This has reproduced on every stable release able to express these rewriter options, `v1.5.2010` (2020-10-22) through `v1.9.2607`, and on `main`; `v1.4.1907` predates the rewriter's `-remove-unused-*` option support entirely.

This was already root-caused and fixed once: [#5265](https://github.com/microsoft/DirectXShaderCompiler/pull/5265), opened two days after this issue, adds a `MarkUsedType` helper that also unwraps array element types, with a test using this exact repro. It built cleanly but was never merged, and was auto-closed in January for two years of inactivity, not for a technical objection.

Labels: this repo has a `rewriter` label ("Bugs in the rewriter") that isn't on this issue; suggest adding it along with `bug` and `correctness`, since the output is not just suboptimal but fails to recompile.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
