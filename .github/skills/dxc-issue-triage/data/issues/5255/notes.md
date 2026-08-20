# #5255 -- Rewriter removed struct declaration which used in constant buffer

## Ground truth

`main-debug` = `build/Debug/bin/dxc.exe`, registered at commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (this batch's assigned ground
truth). Verified:

- `git merge-base --is-ancestor 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  upstream/main` succeeds (exit 0) against `microsoft/DirectXShaderCompiler`
  fetched fresh.
- Tree check: `git diff --name-only 7665270b9 89e2f98e29...` (7665270b9 is
  what the locally built binary self-reports) touches **only** files under
  `.github/skills/dxc-issue-triage/` -- 5315 changed paths, all inside that
  tree. A control diff against an older commit
  (`git diff --name-only 7665270b9~2000 89e2f98e29...`) touches **4775**
  files outside it, confirming the check has power to detect a real source
  difference. No compiler source differs from the cited commit.
- `.cache/compilers/main-debug.json`'s `git_commit` field already recorded
  `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` from a prior batch; this batch
  only re-verified it (no re-registration, no rebuild).

## The tool under test is `dxr`, not `dxc`

The issue's repro command is `dxr.exe -remove-unused-functions
-remove-unused-globals -E vs_main`. `dxr` is the standalone HLSL rewriter
driver (`tools/clang/tools/dxr`), a thin wrapper over
`IDxcRewriter2`/`RewriteUnused`. `dxc.exe` does not expose this surface at
all:

```
$ dxc -remove-unused-functions -remove-unused-globals -E vs_main -T vs_6_0 repro.hlsl
dxc failed : Unknown argument: '-remove-unused-functions'
```

(captured in `variant-dxc-rejects-rewrite-flags-main-debug.txt`, run against
the real registered `main-debug` ground truth, `--expect invalid-probe`,
confirmed).

**No rebuild was done for this issue.** `build/Debug/bin/` in this checkout
does not currently contain `dxr.exe` (a prior batch built it at an older
commit under the id `main-debug-rw`, then the Debug tree was rebuilt for
`dxc` only and `dxr.exe` was not regenerated -- its registered commit,
`13730886e6a9019e4e0823746470f3ab75341d6b`, is stale and was left alone).
Rebuilding `dxr` would touch the shared Debug build tree other batch-019
workers may be measuring, which this triage explicitly must not do.

Instead, `build/Release/bin/dxr.exe` (already present, untouched, built
2026-07-20) was used read-only. Both it and `build/Release/bin/dxc.exe`
self-report `dxcompiler.dll: 1.10(5440-677a02a1)(1.9.0.15438) - 1.9.0.15438
(main, 89e2f98e2)` -- the `89e2f98e2` prefix matches this batch's ground-truth
commit exactly (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and `dxr`/`dxc`
share the same `dxcompiler.dll` on disk, so the version string is not an
independent confirmation of `dxr.cpp` itself, only of the shared DLL that
contains the rewriter logic under test -- which is what actually matters
here, since the bug is inside `dxcrewriteunused.cpp`, compiled into
`dxcompiler.dll`. Registered as a new, non-colliding compiler id
`dxr-5255-release` (`triage.py compiler --id dxr-5255-release ...`); the
existing `main-debug-rw` row was left untouched.

This is not a Debug-vs-Release concern the way crash issues are: the defect
is an AST-traversal/text-emission logic bug with no assert or crash involved,
observable identically regardless of `NDEBUG`.

## Repro

`repro.hlsl` is the issue's shader verbatim. `cmd.txt`:
`-remove-unused-functions -remove-unused-globals -E vs_main repro.hlsl`.

```
$ dxr -remove-unused-functions -remove-unused-globals -E vs_main repro.hlsl
[exit] 0
cbuffer InstanceData {
  const InstanceDataStructType mData[2];
}
;
cbuffer InstanceDataNotUsed {
  const InstanceDataStructType mDataNotUsed[2];
}
;
struct VS_OUTPUT { ... };
VS_OUTPUT vs_main(VS_INPUT input, uint instanceID : SV_InstanceID) { ... }
```

(`out-dxr-5255-release.txt`.) This is **byte-identical** to the output quoted
in the issue body: both cbuffers are kept (matches the documented rewriter
contract that unused cbuffers are not removed --
`tools/clang/test/HLSLFileCheck/rewriter/remove-unused-globals.hlsl`), but
`struct InstanceDataStructType { ... };` is gone even though both retained
cbuffers still declare a field of that type. `InstanceDataStructTypeNotUsed`
(genuinely referenced by nothing) is correctly removed, so the removal logic
itself is doing something, just not the right thing here.

## Root cause, corroborated two ways

**Code reading**, before running anything: `CollectRewriteHelper` in
`tools/clang/tools/libclang/dxcrewriteunused.cpp` walks every top-level
`HLSLBufferDecl` (used or not; "Traverse cbuffers to save types for cbuffer
constant", introduced by #2939 in 2020-06-02, itself before the oldest
release checked below) via `VisitHLSLBufferDecl`, which for each cbuffer
member does:

```cpp
if (TagDecl *tagDecl = constDecl->getType()->getAsTagDecl()) {
  AddRecordType(tagDecl);   // -> SaveTypeDecl -> marks it visited/kept
}
```

`clang::Type::getAsTagDecl()` (`lib/AST/Type.cpp:1526`) only resolves through
`getAs<TagType>()` and `InjectedClassNameType` -- it does **not** unwrap an
array type. For `InstanceDataStructType mData[2]`, `constDecl->getType()` is
a `ConstantArrayType` of `InstanceDataStructType`, not a `TagType`, so
`getAsTagDecl()` returns null, `AddRecordType` is never called for the
element type, and `InstanceDataStructType` is left in `unusedTypes` and
removed by `DoRewriteUnused`. For a scalar member (no array), the same type
is a plain `TagType` and is correctly kept.

**Empirical control** (`control-scalar.hlsl`, `--expect no-match`,
`variant-scalar-dxr-5255-release.txt`): identical shader, `InstanceDataStructType
mData;` (no array) instead of `mData[2]`. The struct declaration is correctly
retained:

```
struct InstanceDataStructType {
  float4 data;
};
cbuffer InstanceData {
  const InstanceDataStructType mData;
}
;
...
```

This isolates the trigger to the array form specifically, matching the code
reading exactly.

**Anti-vacuity control** (`variant-entry-not-found-dxr-5255-release.txt`,
`--expect no-match`): `-E no_such_entry` makes `dxr` fail before emitting any
rewritten source (`//entry point not found`), and correctly scores no-match
-- the predicate's positive anchor clause (`InstanceDataStructType\s+
mData\[2\]` must be present) prevents a failed/empty run from vacuously
satisfying the absence clause.

## An unrelated second gap, not scored by `match.json`

The issue's own quoted output is also missing `struct VS_INPUT { ... };`,
even though `vs_main`'s signature (`VS_OUTPUT vs_main(VS_INPUT input, ...)`)
still uses it as a parameter type -- and this is confirmed both in the
primary repro capture and in `control-scalar.hlsl`'s output (present
regardless of the array/scalar difference), so it is a **separate** defect:
the entry function's own parameters are never marked as "used types" unless
a field of the parameter is dereferenced in the body (`vs_main` never reads
`input.*`). Nothing in `CollectRewriteHelper` walks
`entryFnDecl->parameters()` to mark their types used. PR #5265 (below) does
not touch this path (confirmed: its diff has no `ParmVarDecl`/`params()`
reference), so this second gap is unfixed by that PR too. Not scored here
because it is a different code path from the reported (and titled) symptom;
recorded so a future triage of a parameter-type-specific report is not
surprised to find it already known.

## History: release matrix (`dxr` is a harness, `bisect` refuses)

`triage.py bisect` hard-errors for this issue
(`refuse_harness_bisect`/`is_dxc_binary`): the registered ground-truth
executable's filename is `dxr.exe`, not `dxc`/`dxc.exe`, and `bisect` would
otherwise substitute each release's `dxc.exe` -- which never calls the
rewriter -- and could report a confident, wrong verdict (same shape as
#4273, #3237, #2923).

Followed the #4273 pattern: `measure.py --history` stages the ground-truth
`dxr.exe` next to each cached stable release's own `dxcompiler.dll` under
`.cache/rw5255/<tag>/` (Windows' DLL search order then loads that release's
rewriter, driven by a fixed, known-good `dxr` binary), and scores `repro`
against this issue's own `match.json` via `triage.classify` -- the same code
used for `out-*.txt`. Full output: `manual-case-release-history.txt`;
`measure.json` has the machine-readable rows.

| release | repro | control (scalar) | reading |
| --- | --- | --- | --- |
| v1.4.1907 | no-repro | no-repro | **invalid-probe** -- `-unchanged` exits 1 (`0x80070057`) while no-option run exits 0, i.e. this release's rewriter runs but has none of these options yet |
| v1.5.2010 .. v1.9.2607 (all 20 stable releases) | repro | no-repro | repro |
| `dxr-5255-release` (main, 89e2f98e2) | repro | no-repro | repro |

The `control` column (scalar-member variant) scores `no-repro` on **every**
release including `v1.4.1907`'s successors, so the array/scalar distinction
that isolates the root cause holds across the whole history, not just on
ground truth. `v1.5.2010`'s own `repro` output is byte-identical to the
issue's quoted output (see `manual-case-release-history.txt`, `=== v1.5.2010
probe: repro ===`).

**Always reproduced, for as long as this is checkable.** `git log --all -S
"getAsTagDecl()" -- tools/clang/tools/libclang/dxcrewriteunused.cpp` dates
the offending pattern (as used for cbuffer members) to
`7e780aef6fc71936d8f3a6fa11a63e66fb349236` ("Fix crash when remove unused
globals in rewriter and support remove types. (#2933)", 2020-05-30) -- the
commit that *introduced* type-removal in the rewriter at all. That predates
`v1.4.1907`'s successor `v1.5.2010` (2020-10-22), so the defect has existed
since the feature it is part of was introduced, and every probeable stable
release inherits it. `v1.4.1907` (2019-07) itself predates the rewriter
option surface entirely and is `invalid-probe`, not evidence either way.

## The bug was already found and fixed once, and the fix lapsed

Cross-reference timeline (`gh api .../issues/5255/timeline`) shows exactly
one pre-existing event, dated 2023-06-02 (two days after filing, predating
this triage): [PR #5265](https://github.com/microsoft/DirectXShaderCompiler/pull/5265),
"[Rewriter] Support struct type used by array.", by `python3kgae` (a
Microsoft engineer, not the reporter). Its description: *"the SaveTypeDecl
function was used to add a type to the visited set... this function was
only called on TagDecl, causing array types to be ignored. The fix
introduces a new function, MarkUsedType, which checks not only TagDecl but
also the element type of arrays."* -- independently reaching the identical
root cause via `Ty->getArrayElementTypeNoTypeQual()`. Its test
(`tools/clang/test/HLSLFileCheck/rewriter/struct_array.hlsl`, added by the
PR) uses this exact repro (byte-for-byte the same shader) and asserts
`InstanceDataStructType` is kept.

The PR built cleanly (two green AppVeyor CI comments, 2023-06-02 and
2023-07-10) but was **never merged** (`merged: false`,
`gh pr view 5265 --json mergedAt` -> `null`). It sat with no further activity
until `2026-01-22`, when it was auto-closed by an inactivity sweep
(`damyanp`: *"This PR was closed as it has not been updated in the last two
years. Please feel free to reopen if this PR should be merged and is in a
reviewable state."`) -- the same shape as #2427's lapsed fix noted elsewhere
in this batch's method notes: a correct, tested fix that never landed for
reasons unrelated to its correctness.

## Text staleness

None. The issue body and its output quote are still exactly what the
compiler does; nothing in the thread claims this was fixed. (The reporter's
own third comment is a distinct feature request -- "remove cbuffer
definitions which all members are not used" -- not a claim that this bug was
resolved; no PR from the reporter's account exists on GitHub, so that offered
patch appears to have never been posted.)

## Verdict

- status: `repros`
- repro-quality: `complete` (issue body has exact input and exact, byte-
  reproducible malformed output)
- history: `always-repro'd` across every checkable release
  (`v1.5.2010`..`v1.9.2607`, 20 stable releases) and `main`
  (89e2f98e29c289ae8ad9e00dd310104fea9fd7df); `v1.4.1907` is an invalid probe
  (predates the rewriter's `-remove-unused-*` options)
- confidence: high
- suggested action: `still-valid-keep-open` -- an unrelated Microsoft
  engineer already produced and tested a correct fix (#5265); the actionable
  next step is reviving/merging that PR rather than re-diagnosing the bug.
  Not `close-fixed` (does not reproduce would be false); not
  `needs-repro-from-reporter` (repro is complete and verified).
