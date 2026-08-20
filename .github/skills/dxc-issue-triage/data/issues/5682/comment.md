> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5682](https://github.com/microsoft/DirectXShaderCompiler/issues/5682).

Still reproduces on `main` (commit `89e2f98e2`) — confirmed by reading the CMake rule graph
rather than by re-running the failing install, since this is a CMake configuration defect, not
a `dxc` compiler behavior.

**Root cause:** `tools/llvm-as/CMakeLists.txt` excludes `llvm-as` from the default build
(`EXCLUDE_FROM_ALL`) whenever `HLSL_OPTIONAL_PROJS_IN_DEFAULT` is `OFF` — its default. But
`add_llvm_tool` (`cmake/modules/AddLLVM.cmake`) already registered an unconditional
`install(TARGETS llvm-as ...)` rule before that exclusion is applied, so `cmake_install.cmake`
still tries to copy `llvm-as.exe` for the plain `install` target even though it was never built.
This is unchanged in the tree from before this issue was filed through the current commit.

This is exactly what the duplicate report, #5867, found independently ("`llvm-as` ... which was
never built"), and `@llvm-beanz` closed it as a duplicate of this issue with the same
conclusion.

**Workaround that already works today:** the `install-distribution` target
(`CMakeLists.txt`, added in #5154, predates this issue) installs only the `dxc`, `dxcompiler`
and `dxc-headers` components via per-component `install-<component>` custom targets, so it never
reaches `llvm-as`'s install rule at all. It's what DXC's own Linux CI uses
(`gcp-pipelines/x86_64-linux-clang.yml`), and matches `@bjconlan`'s suggestion above. It isn't
documented anywhere outside `CMakeLists.txt` and that CI file, which is presumably why
`@namandixit`'s question above went unanswered.

Given `@pow2clk`'s and `@damyanp`'s comments that the plain `install` target isn't expected to
work and a PR would be welcome: `build`, `up-for-grabs` looks right for labels; recommend
keeping open rather than closing, and consider pointing users at `install-distribution` from
the docs in the meantime.

---
<sub>Triaged with AI assistance. This finding was verified by reading the CMake source (no
build was run); please flag anything that looks wrong.</sub>
