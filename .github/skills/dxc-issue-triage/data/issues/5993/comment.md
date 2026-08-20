> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5993](https://github.com/microsoft/DirectXShaderCompiler/issues/5993).

Still present on `main` (commit `89e2f98e2`): `clang_createTranslationUnit` in
`tools/clang/tools/libclang/CIndex.cpp` is unchanged from what's quoted above (now at
lines 2947–2970, a small shift from unrelated edits elsewhere in the file, not from any change
to this code). `clang_createTranslationUnit2`'s active arm (`#if 1 // HLSL Change ... - no
support for serialization`) still returns `CXError_Failure` without ever assigning `*out_TU`,
so `clang_createTranslationUnit`'s `TU` local is still read (in the `assert`, and in
`return TU;`) without a path that guarantees it was initialized.

@llvm-beanz's suggested rewrite was implemented exactly in
[PR #6002](https://github.com/microsoft/DirectXShaderCompiler/pull/6002), opened by
@farzonl the day after this issue and approved — but it was never merged, and was closed
2026-01-22 by an inactivity sweep rather than by disagreement:

> This PR was closed as it has not been updated in the last two years. Please feel free to
> reopen if this PR should be merged and is in a reviewable state.

Reopening and rebasing #6002 is the cheapest path to closing this out.

For context: the flagged branch is dead code in every current DXC configuration (the `#if 1`
is unconditional), so this is a static-analysis/code-hygiene finding rather than an observed
runtime defect — consistent with `bug`/`tech-debt` already on the issue.

---
<sub>Triaged with AI assistance. This is a static-analysis/code-hygiene issue about source
outside the `dxc` build target, so no compiler was run; the evidence is the source text at the
cited commit and the linked PR/issue history. Please flag anything that looks wrong.</sub>
