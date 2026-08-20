# Expected behavior (written before running anything)

Issue #5481 is a build-infrastructure feature request, not a shader-compilation bug. There is
no HLSL source, no `dxc` command line, and no compiler output attached or implied. The body is
two sentences:

> clang Source Based Code Coverage tool works for DXC on linux now. But not on windows build.
> Goal: Generate code coverage report on windows.

"This reproduces" therefore means: **building DXC on Windows with clang Source-Based Code
Coverage instrumentation enabled (`-DDXC_COVERAGE=On` / `-DLLVM_BUILD_INSTRUMENTED_COVERAGE=ON`)
still does not work end-to-end** (configure, build, run tests, and generate a coverage report),
in the same way it already does on Linux via `.github/workflows/coverage-gh-pages.yml`.

"This is fixed" would mean: the repository ships a working, exercised path to produce a source
coverage report from a Windows build (a documented cmake invocation and/or a Windows leg of the
coverage workflow), not merely that the `LLVM_BUILD_INSTRUMENTED_COVERAGE` option is *syntactically*
platform-agnostic in `HandleLLVMOptions.cmake`.

Repro quality: **prose-only / none.** There is no shader or dxc invocation to write a `cmd.txt`
for, so `match.json`/`cmd.txt`/`bisect`/`godbolt` are deliberately not produced for this issue —
per the skill's guidance that these are legitimately absent when compiler output cannot answer
the question. The question here is answered by source/CI inspection instead.
