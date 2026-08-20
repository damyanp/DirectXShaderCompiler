# Expected symptom — #5993

**Claim:** `tools/clang/tools/libclang/CIndex.cpp` still contains the pattern that trips
ClangTidy's `clang-analyzer-core.uninitialized.Branch` check, in `clang_createTranslationUnit`
(quoted by the issue as lines 2944-2961 of a specific historical revision; the function starts
at line ~2944 on `main` too):

```cpp
CXTranslationUnit clang_createTranslationUnit(CXIndex CIdx,
                                              const char *ast_filename) {
  CXTranslationUnit TU;                                   // declared, NOT initialized
  enum CXErrorCode Result =
      clang_createTranslationUnit2(CIdx, ast_filename, &TU);
  (void)Result;
  assert((TU && Result == CXError_Success) ||
         (!TU && Result != CXError_Success));              // compiled out under NDEBUG
  return TU;                                                // can return uninitialized TU
}
```

and in `clang_createTranslationUnit2` immediately below it:

```cpp
enum CXErrorCode clang_createTranslationUnit2(CXIndex CIdx,
                                              const char *ast_filename,
                                              CXTranslationUnit *out_TU) {
#if 1 // HLSL Change Starts - no support for serialization
  return CXError_Failure;                 // out_TU is never touched on this path
#else
  ...
```

Because the HLSL-disabled branch (`#if 1`) returns without ever writing through `out_TU`,
`TU` in `clang_createTranslationUnit` is read (`return TU;`, and the `assert` when it is not
compiled out) while still uninitialized. That is exactly the analyzer-branch shape
`clang-analyzer-core.uninitialized.Branch` flags, and the issue itself agrees it is a false
positive **in the sense that nothing currently calls this path with serialization enabled** —
the finding is about the source shape, not an observed crash.

"This reproduces" means: the source at the ground-truth commit still has this exact shape
(uninitialized `TU`, unconditional early return in `clang_createTranslationUnit2`'s active
`#if` arm that never assigns `*out_TU`), i.e. neither this fix nor an equivalent one has landed.
"Does not reproduce" means the function was rewritten (e.g. as `llvm-beanz` suggested and
`farzonl` implemented in PR #6002) so that no branch returns a use of an uninitialized local.

**Repro quality:** `complete` — the issue quotes the exact function, exact line range, and a
concrete alternative implementation.

**Instrument note (recorded before probing):** This is a ClangTidy static-analysis finding
about `tools/clang/tools/libclang/CIndex.cpp`. That file belongs to the `libclang` CMake target,
which is a separate, optional target from `dxc`/`dxcompiler` — the ground-truth Debug build
(`main-debug`, built `--target dxc` only) never compiles this translation unit at all, and the
`#if 1` branch is unconditional in every DXC configuration (it does not depend on
Debug/Release/NDEBUG). There is therefore no `dxc` invocation, shader, or `match.json` predicate
that can exercise this code — the compiler is not the right instrument. The right instrument is
the source text itself (byte-for-byte comparison against the quoted excerpt) and the repository's
own PR/issue history, not a `run`/`bisect` probe. `cmd.txt`/`match.json` are deliberately absent
per the skill's guidance for non-compiler-verifiable issues.
