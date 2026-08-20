# Notes — #5682 "Install error"

## Summary

The reported failure is not a `dxc` compiler bug at all — it is CMake's own generated
`cmake_install.cmake` failing to find `llvm-as.exe` while installing the default `install`
target. This is a build-system issue; no HLSL/DXIL compiler probe applies. Per the skill's
guidance for build-system issues (step 5, "not-compiler-verifiable"), `cmd.txt`/`match.json` are
deliberately absent and the evidence below is a static read of the CMake rule graph at the
ground-truth commit, not a captured compiler run.

## Constraint on this pass

This triage explicitly forbids rebuilding any shared build target, changing source, editing
shared triage state (`SKILL.md`/`triage.py`/`reindex`), or writing GitHub. Reproducing the
reporter's exact failure would require running `cmake --build --target install` against a
Release configuration that has not been fully built in this workspace, which risks driving a
rebuild of the shared repository/build tree — out of scope here. Instead the root cause is
established from the CMake source itself, which is deterministic and needs no build.

## Root cause, confirmed by reading the CMake rule graph

`tools/llvm-as/CMakeLists.txt` (ground-truth commit `89e2f98e2`, unchanged since at least
`18328d510`, the commit immediately preceding this issue's 2023-09-10 filing date):

```
add_llvm_tool(llvm-as
  llvm-as.cpp
  )

# HLSL Change Starts
if (NOT HLSL_OPTIONAL_PROJS_IN_DEFAULT)
  set_target_properties(llvm-as PROPERTIES EXCLUDE_FROM_ALL ON EXCLUDE_FROM_DEFAULT_BUILD ON)
endif ()
# HLSL Change Ends
```

`HLSL_OPTIONAL_PROJS_IN_DEFAULT` defaults `OFF` (`CMakeLists.txt:84`, identical at
`18328d510` and at the ground-truth commit: `option(HLSL_OPTIONAL_PROJS_IN_DEFAULT "Include
optional projects in default build target." OFF) # HLSL Change`). Neither reporter (#5682 or
its duplicate #5867) passed `-DHLSL_OPTIONAL_PROJS_IN_DEFAULT=ON`, so with the default
configuration `llvm-as` is excluded from the default (`ALL`) build target and is never compiled
by a plain `cmake --build .`.

But `cmake/modules/AddLLVM.cmake`'s `add_llvm_tool` macro (unchanged between `18328d510` and
`89e2f98e2`) unconditionally registers an `install(TARGETS llvm-as ...)` rule the moment
`LLVM_BUILD_TOOLS` is `ON` (its default, and DXC's `cmake/caches/PredefinedParams.cmake` does
not touch it):

```
macro(add_llvm_tool name)
   if( NOT LLVM_BUILD_TOOLS )
     set(EXCLUDE_FROM_ALL ON)
   endif()
   add_llvm_executable(${name} ${ARGN})
   ...
   if (LLVM_IS_${name}_TOOLCHAIN_TOOL GREATER -1 OR NOT LLVM_INSTALL_TOOLCHAIN_ONLY)
     if( LLVM_BUILD_TOOLS )
       install(TARGETS ${name}
               EXPORT LLVMExports
               RUNTIME DESTINATION bin
               COMPONENT ${name})
       ...
```

`tools/llvm-as/CMakeLists.txt`'s `EXCLUDE_FROM_ALL` override runs **after** `add_llvm_tool` has
already generated that unconditional `install(TARGETS)` rule, so nothing in the DXC-specific
override retracts it. The result: `cmake_install.cmake` unconditionally tries to copy
`<build>/<config>/bin/llvm-as.exe` for the plain `install` target, and that file was never
produced, because the executable that would have produced it was excluded from the default
build. This matches the file/line the reporter quoted
(`tools/llvm-as/cmake_install.cmake:39 (file)`) and is exactly what the maintainer-confirmed
duplicate #5867 reporter also concluded independently ("`llvm-as` (which was never built)").

CMake's own wording ("File exists") for a source file that is simply absent is unusual, but is
not disputed by either reporter and is not something a source read can adjudicate — it is
CMake's own `file(INSTALL)` error text, external to this repository, and not necessary to
explain further to establish the root cause above (the file genuinely was never produced at
that path in both independent reports).

## Duplicate and maintainer position (already public, gh timeline)

- `gh api .../5682/timeline` lists a cross-reference to #5867 ("Windows CMake install target
  fails"), filed 2023-10-17, closed the same day by `@llvm-beanz`: *"This is a duplicate of
  microsoft/DirectXShaderCompiler#5682. We've never used the install action so it doesn't
  work."*
- On #5682 itself: `@pow2clk` (2023-09-13, collaborator) — "we don't use the cmake install
  rules ourselves and so they have some problems... if it's something you've resolved and would
  like to submit a pull request, we'd welcome the contribution." `@damyanp` (2024-10-17,
  member) — "We don't expect the install target to work, but if someone wants to take the time
  to try and make it work we'd consider a PR for that." Both are maintainer statements that the
  default `install` target is a known-broken, unsupported, up-for-grabs area — not a "fixed" or
  "will fix" commitment.
- The reporter (2024-10-17) says they "found a solution, using powershell" but never shared it
  in the thread, so it is not evidence of an upstream fix.
- `@bjconlan` (2025-01-19) points at the `install-distribution` target as a working
  alternative. This matches a separate, earlier triage of #3276 in this same dataset
  (`data/issues/3276/`), which independently confirmed `install-distribution` (added in
  `4f5e4d1b7`, 2023-04-18, PR #5154 — *before* #5682 was even filed) installs a working, trimmed
  set of DXC deliverables, and is what DXC's own Linux CI actually uses
  (`gcp-pipelines/x86_64-linux-clang.yml:40`). Reading why it avoids this exact bug: `CMakeLists.txt`
  wires `install-distribution` to per-component `install-<component>` custom targets
  (`CMakeLists.txt:817-825`, `add_llvm_tool`'s `install-${name}` custom target at
  `cmake/modules/AddLLVM.cmake:690-695`), each of which runs `cmake_install.cmake` with
  `-DCMAKE_INSTALL_COMPONENT=<component>` set to only `dxc`, `dxcompiler` or `dxc-headers` — so
  it never reaches the `llvm-as` component's install rule at all. The plain `install` target
  processes every component unconditionally, including `llvm-as`, which is where it fails.
- `@namandixit` (2025-02-02) asks what the supported install path is; no maintainer reply is
  recorded as of this triage. This is itself a documentation gap, consistent with #3276's
  finding that `install-distribution` is undocumented outside `CMakeLists.txt` and CI YAML.

## Verdict

`status: repros` (the underlying CMake rule defect, confirmed unchanged in source from
2023-09 through the ground-truth commit) but **`not-compiler-verifiable`** as the classification
for how this issue is actually probed, since no `dxc` invocation exercises CMake's install
machinery. `history: always-repro'd` is a source-level claim, not a captured-output bisection —
there is no compiler binary whose behavior changes here, only a CMake rule that has been present,
unmodified, across the entire window this triage can measure.

Suggested action: `still-valid-keep-open` — a real, still-present, unfixed defect in the CMake
install rules, already triaged twice by the same maintainer conclusion ("we don't expect the
install target to work" / "duplicate, never worked") and left open as up-for-grabs rather than
closed. Not `close-fixed` (nothing fixed it) and not `enhancement-not-bug` (it is a plain rule
bug: an install rule references a target deliberately excluded from the default build, in the
same file, with no guard).
