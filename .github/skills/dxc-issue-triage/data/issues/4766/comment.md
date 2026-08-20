> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4766](https://github.com/microsoft/DirectXShaderCompiler/issues/4766).

Still an open, unactioned ask as of `main` (`89e2f98e2`).

`tools/clang/tools/dxcompiler/CMakeLists.txt` still hardcodes
`add_clang_library(dxcompiler SHARED ${SOURCES})` — the exact line @MarijnS95 linked in 2023.
That line dates to the repository's first commit (`6ee4074a4`, 2016-12-28) and has never been
touched since; the file's most recent change (`6ea7cf1c1`, #8166) is an unrelated MacOS warning
fix. `llvm_add_library` (`cmake/modules/AddLLVM.cmake`) already supports a `STATIC` target, but
nobody has made the change. `dxildll` (`dxil.dll`) has the identical pattern: it only entered
this repo via #6866 (2024-09-05, after this issue was filed) and hardcodes `SHARED` too,
unchanged since.

#5985 cites this issue and discusses moving `DllMain`'s work (including its `LoadLibraryA` call
for `dxil.dll`) into `DxcCreateInstance`, which @amaiorano described there as non-trivial and
untaken. `include/dxc/Support/dxcapi.use.h` still calls `LoadLibraryA` from `DllMain` today.
Both issues remain open with no linked PR.

No shader or `dxc` invocation applies here; this is a CMake configuration question, so no CE
link or release history is included.

Suggest adding `enhancement` alongside the existing `build`/`api` labels, since the thread
converged on a specific, still-open feature ask rather than only an unanswered question.

---
<sub>Triaged with AI assistance from `git log`/`git show` evidence in this repository, not a
compiler run; please flag anything that looks wrong.</sub>
