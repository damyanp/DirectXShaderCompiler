# Notes — #5804 "Fix UBSAN alignment failures"

## What the issue says

Filed 2023-09-29 by amaiorano. PR #5803 ("Disable UBSAN sanitizing alignment errors", merged
2023-10-06) disabled the *alignment* sub-check of `-fsanitize=undefined` for the whole build
because the unaligned reads/writes performed by
`DxilPipelineStateValidation::CheckedReaderWriter`
(`include/dxc/DxilContainer/DxilPipelineStateValidation.h`) trip it. The reporter tried a
short-term fix in a personal fork
(`amaiorano:DirectXShaderCompiler:fix-ubsan-unaligned-access`, out of scope — not this repo)
but judged the result too hard to read, and left the ask open: eventually re-enable the
alignment sanitizer, ideally by adopting a cleaner reimplementation `@llvm-beanz` is said to
have done in upstream Clang.

No shader repro is provided or implied — this is a build-configuration / tech-debt request.
Per the skill's guidance for such issues ("find the producing instrument" — the #3276 CMake
pattern), the right artifact to inspect is the sanitizer flag configuration itself, not `dxc`
output.

## What was measured

`cmake/modules/HandleLLVMOptions.cmake` sets the sanitizer flags. At the ground-truth commit
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), both `LLVM_USE_SANITIZER` configurations that
enable UBSAN still exclude `alignment`:

```
      append("-fsanitize=undefined -fno-sanitize=vptr,function,alignment -fno-sanitize-recover=all"
              CMAKE_C_FLAGS CMAKE_CXX_FLAGS)
...
      append("-fsanitize=address,undefined -fno-sanitize=vptr,function,alignment -fno-sanitize-recover=all"
              CMAKE_C_FLAGS CMAKE_CXX_FLAGS)
```

(`data/issues/5804/variant-sanitizer-flags-main-debug.txt`, obtained via
`git show <ground-truth-sha>:cmake/modules/HandleLLVMOptions.cmake`, confirmed with
`git merge-base --is-ancestor <ground-truth-sha> HEAD` = ancestor.) This is exactly the
suppression PR #5803 added (for the `Undefined` config) and PR #6431 "Disable ubsan alignment
errors properly" (merged 2024-03-20) added for the second, `Address;Undefined`, config that
#5803 had missed — both public, merged PRs
(`data/issues/5804/manual-case-pr-context.txt`).

`include/dxc/DxilContainer/DxilPipelineStateValidation.h`'s `CheckedReaderWriter` also carries
no `no_sanitize`/alignment-suppression attribute of its own (checked directly) — the fix
really is the blanket CMake exclusion described in the issue, not a narrower in-code
workaround that superseded it.

**Caveat on git history in this workspace:** a broader, unscoped `git log --all -S
"fno-sanitize=vptr,function,alignment"` over the whole local repository also surfaces a commit
titled "Turn on function & alignment UBSAN" (which removes the `alignment` exclusion) and a
later one that reintroduces it. Neither of those two commits is an ancestor of the
ground-truth commit (`git merge-base --is-ancestor` is false for both), and the ground-truth
commit's own ancestry contains only one commit touching this file at all, whose diff (due to
this workspace's rewritten/synthetic history) shows the entire file as newly added rather than
a real incremental change. That history is therefore not trustworthy for dating or explaining
*why* the exclusion persists — only the direct content check against the ground-truth tree
(above) is used for the verdict.

## Verdict

The tech debt the issue describes — the alignment sanitizer disabled because
`CheckedReaderWriter`'s unaligned access was too hard to fix cleanly — is still present,
unchanged, at ground truth. No shader-level bisection applies; this is confirmed by direct
source inspection of the build configuration, which is the only instrument that can answer
this question. `status: repros`, `history: always-repro'd` (from filing through ground truth,
the only two points checkable), `confidence: high` for the narrow claim "the exclusion is
still there"; the broader ask (a real fix, or a Clang-side backport) has not been attempted in
this tree as far as observable, so no `does-not-repro`/`fixed` claim is supported either.

Not `not-compiler-verifiable`: it *is* verifiable, just not by compiling a shader — the CMake
file is the artifact under test, consistent with the #3276 precedent for build/config issues.

## Labels

Current: `bug`, `tech-debt`. The taxonomy includes a `sanitizer` label
("fault detected by sanitizer run") that is not applied and squarely fits — this is
DXC's own build/CI sanitizer configuration, not a user-facing shader bug. `build` ("Issues
related to build and setup") also fits, since the change is entirely in CMake sanitizer flags.
`check-in-clang` does not apply: this is not a shader construct to compare against Clang, it's
a suppression of DXC's own sanitizer build.
