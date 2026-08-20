# Notes — #5481 "[Build] enable clang Source Based Code Coverage on windows"

## Issue text

Filed 2023-07-31 by python3kgae (Xiang Li). Body, in full:

> clang Source Based Code Coverage tool works for DXC on linux now.
> But not on windows build.
>
> Goal:
> Generate code coverage report on windows.

No repro shader, no command line, no attachment. Zero comments. Labels at fetch time:
`enhancement`, `build`.

## This is a build/CI feature request, not a compiler defect

There is no `dxc` invocation this issue is about — the "goal" is a working `cmake`
configuration and CI job, not a shader compile. Per the skill's guidance for such issues,
`match.json`/`cmd.txt`/`bisect`/`godbolt` are deliberately not produced; the question is
answered by inspecting the build scripts and CI workflow, and by checking whether it was
addressed since filing.

## What exists today (ground truth 89e2f98e29c289ae8ad9e00dd310104fea9fd7df)

* `.github/workflows/coverage-gh-pages.yml` is the only coverage-generating CI job in the
  repo. Its `build` job is pinned to `runs-on: ubuntu-latest` (confirmed at the ground-truth
  commit via `git show 89e2f98e2:.github/workflows/coverage-gh-pages.yml`) and configures with
  `-DDXC_COVERAGE=On -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++`. There is no
  Windows leg.
* `cmake/caches/PredefinedParams.cmake`, the cache script that turns `-DDXC_COVERAGE=On` into
  `LLVM_BUILD_INSTRUMENTED_COVERAGE=ON` (plus the profile dir and target lists), opens with:
  `# This file contains the basic options required for building DXC using CMake on *nix
  platforms.` — coverage's only wired-up entry point is documented as Unix-only.
* `cmake/modules/HandleLLVMOptions.cmake` itself does not gate `LLVM_BUILD_INSTRUMENTED` /
  `LLVM_BUILD_INSTRUMENTED_COVERAGE` on `WIN32`, so nothing stops a user from setting
  `-DLLVM_BUILD_INSTRUMENTED_COVERAGE=ON` directly on a Windows/clang-cl configure. But the
  flag it appends is **single-quoted**:
  `-fprofile-instr-generate='${LLVM_PROFILE_FILE_PATTERN}' -fcoverage-mapping` (confirmed
  present, unchanged, at the ground-truth commit). Single quotes are shell/Make-only grouping;
  MSVC-style and clang-cl command-line parsing on Windows does not strip them, so the pattern
  argument clang receives literally contains the quote characters.
* `cmake/modules/CoverageReport.cmake`'s `generate-coverage-report` target invokes
  `${Python3_EXECUTABLE}` (confirmed present, unchanged, at the ground-truth commit).

## A concrete, matching fix attempt exists and was closed unmerged

The issue's own cross-reference timeline (`gh api .../issues/5481/timeline`) shows one directly
relevant PR, opened by the same reporter one week after filing:

```
2023-08-07T23:25:49Z  microsoft/DirectXShaderCompiler#5510  [CodeCoverage] Fix issues when run code coverage on windows
```

`gh pr view 5510` shows **state: CLOSED, mergedAt: null**. Its description:

> 1. Use PYTHON_EXECUTABLE instead of Python3_EXECUTABLE which not enabled for DXC.
> 2. Use "" instead of '' for -fprofile-instr-generate=${LLVM_PROFILE_FILE_PATTERN

`gh pr diff 5510` (full diff, three files):

```diff
--- a/cmake/modules/AddLLVM.cmake
+++ b/cmake/modules/AddLLVM.cmake
@@ function(configure_lit_site_cfg input output)
+  # HLSL Change - replace " with \" in HOST_LDFLAGS for -fprofile-instr-generate
+  string(REPLACE "\"" "\\\"" HOST_LDFLAGS "${HOST_LDFLAGS}")

--- a/cmake/modules/CoverageReport.cmake
+++ b/cmake/modules/CoverageReport.cmake
-                  COMMAND ${Python3_EXECUTABLE} ${PREPARE_CODE_COV_ARTIFACT}
+                  COMMAND ${PYTHON_EXECUTABLE} ${PREPARE_CODE_COV_ARTIFACT}

--- a/cmake/modules/HandleLLVMOptions.cmake
+++ b/cmake/modules/HandleLLVMOptions.cmake
-append_if(LLVM_BUILD_INSTRUMENTED "-fprofile-instr-generate='${LLVM_PROFILE_FILE_PATTERN}'"
+append_if(LLVM_BUILD_INSTRUMENTED "-fprofile-instr-generate=\"${LLVM_PROFILE_FILE_PATTERN}\""
   ...
-append_if(LLVM_BUILD_INSTRUMENTED_COVERAGE "-fprofile-instr-generate='${LLVM_PROFILE_FILE_PATTERN}' -fcoverage-mapping"
+append_if(LLVM_BUILD_INSTRUMENTED_COVERAGE "-fprofile-instr-generate=\"${LLVM_PROFILE_FILE_PATTERN}\" -fcoverage-mapping"
```

This PR's commit (`78979e55d78e6520520cd08ae293808777d5b814` per `gh pr view --json commits`)
does not exist in this local clone (`git cat-file -e` fails, `git merge-base --is-ancestor`
reports "Not a valid commit name") — expected for a closed, unmerged PR whose branch was
deleted, and consistent with the diff above never having landed on `main`.

**All three of the PR's target lines are present, byte-for-byte unfixed, at the pinned
ground-truth commit** (`git show 89e2f98e2:<path> | Select-String ...`, quoted above under
"What exists today"). `git log --all --follow` on `HandleLLVMOptions.cmake` and
`CoverageReport.cmake` since 2019 shows only three commits touching the coverage block, none
after 2022-11-17 aside from one large unrelated synthetic merge (`8a8b29f96`, 2025-06-03,
"[spirv] AMD work graphs extension #7353" — a repo-wide history-rewrite artifact, not a
coverage change; confirmed `8a8b29f96` predates the ground-truth commit in the same log). A
repo-wide `git log --all --since=2023-07-31 -i --grep=coverage` finds no commit implementing a
Windows coverage fix; every hit is either this issue's own triage batches or unrelated test
"coverage" (e.g. LinAlg test-coverage PRs).

Also worth recording: the PR's *first* stated defect ("Python3_EXECUTABLE which not enabled
for DXC") does not hold at the top-level `CMakeLists.txt` as of ground truth — line 451,
`find_package(Python3 REQUIRED)`, runs unconditionally (no `WIN32`/`UNIX` guard) and precedes
`include(CoverageReport)` at line 805, so `Python3_EXECUTABLE` should in fact be populated on a
Windows configure too. Whatever originally motivated that half of the PR is not reproducible
from the CMake control flow alone; the single-quoting defect (the PR's second point) is the
one independently confirmed to still be live code today.

## Verdict

Not a compiler-behavior issue — `not-compiler-verifiable`. Repro quality `none` (prose-only
goal statement, no repro to grade). No release/bisect history applies: there is no `dxc.exe`
command line this request can be tested against, so `bisect`/`godbolt` are correctly absent,
not merely skipped.

The request is **still open and unimplemented** at the pinned ground truth. It is not simply
"nobody has looked at this yet" — a specific, matching fix (#5510) was proposed and then closed
without merging, and the exact lines it touched remain in their pre-fix state. That is stronger
evidence of "still needed" than silence would be, and worth surfacing to a maintainer as the
headline fact rather than "no one has looked at this."

Suggested action: `still-valid-keep-open`. This is a legitimate, unactioned infrastructure
request with a concrete, ready-to-revive starting point (PR #5510) rather than something to
close for staleness.

## Labels

Current: `enhancement`, `build` — both fit. Proposing to add `ci`: the blocking artifact
central to this issue's evidence is a CI workflow file (`coverage-gh-pages.yml`, Linux-only)
and a CI-oriented cache script (`PredefinedParams.cmake`, documented Unix-only), not general
build plumbing. No removals — nothing in the evidence contradicts the existing labels. No
`text_stale`: the issue's two-sentence body still accurately describes the state of the world
(Linux coverage works, Windows coverage does not); it was never claiming more than that.
