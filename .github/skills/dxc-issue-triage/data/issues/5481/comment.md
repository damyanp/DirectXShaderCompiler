> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5481](https://github.com/microsoft/DirectXShaderCompiler/issues/5481).

This is a build/CI request rather than a compiler bug, so there's no shader or `dxc.exe`
command line to test — the checks below come from reading the CMake and CI scripts at
`main` (89e2f98e2).

**Still open, and a matching fix was proposed and closed unmerged.** #5510, opened by the
same reporter a week after this issue, tried to fix exactly this:

```
1. Use PYTHON_EXECUTABLE instead of Python3_EXECUTABLE which not enabled for DXC.
2. Use "" instead of '' for -fprofile-instr-generate=${LLVM_PROFILE_FILE_PATTERN
```

It closed without merging, and its target lines are unchanged on `main` today:

- `cmake/modules/HandleLLVMOptions.cmake` still appends
  `-fprofile-instr-generate='${LLVM_PROFILE_FILE_PATTERN}' -fcoverage-mapping` with single
  quotes, which a Windows/clang-cl command line does not strip the way a Unix shell does.
- `cmake/modules/CoverageReport.cmake`'s `generate-coverage-report` target still invokes
  `${Python3_EXECUTABLE}`, not `${PYTHON_EXECUTABLE}`.
- `.github/workflows/coverage-gh-pages.yml` (the only coverage-generating CI job) still runs
  only on `ubuntu-latest`, and `cmake/caches/PredefinedParams.cmake` — the cache script that
  wires up `-DDXC_COVERAGE=On` — still documents itself as being "for building DXC using
  CMake on *nix platforms."

Nothing in `HandleLLVMOptions.cmake` blocks setting `LLVM_BUILD_INSTRUMENTED_COVERAGE=ON` on a
Windows configure directly, but nothing here confirms that path has ever been exercised
end-to-end either; the CI job and the maintained cache script both remain Linux-only, and #5510
is the one attempt on record to make it work.

Labels: `enhancement` and `build` both still fit. Consider adding `ci`, since the concrete gap
is a CI workflow and its cache script rather than general build plumbing.

---
<sub>Triaged with AI assistance. This assessment is based on reading the build/CI scripts and
the linked PR, not on running a compiler; please flag anything that looks wrong.</sub>
