# #5824 -- [Test] Move clang diagnostic tests to verifiertest.cpp

## What the issue asks

Filed 2023-10-03 by `bob80905` (Joshua Batista) -- confirmed independently via
`gh api repos/microsoft/DirectXShaderCompiler/issues/5824`, matching the fetched
`issue.json`. Labels `enhancement`, `test`; no comments; milestone **`Dormant`** (added
2024-10-23, per the live timeline); no assignee; no linked PR anywhere in the issue's
timeline (`gh api .../issues/5824/timeline` returns only label/project/milestone events,
zero `cross-referenced` entries).

It names two specific unit tests, `GSMainMissingAttributeFail` and
`GSOtherMissingAttributeFail`, both in `tools/clang/unittests/HLSL/ValidationTest.cpp`, and
claims they only test a **clang diagnostic**, not DXIL validation, so they belong in
`tools/clang/unittests/HLSL/VerifierTest.cpp` instead (using `-verify` "if the new lit
framework is being used"). It also asks, more broadly and without naming further examples,
that "any other tests inside validationTest that only test clang diagnostics" get the same
treatment.

This is a request about which C++ test fixture registers a unit test, not a report of wrong
compiler behavior. No `dxc` invocation's output changes depending on which `.cpp` file
contains the `TEST_F`/`TEST_METHOD` line, so the history/bisection machinery this skill
otherwise relies on does not apply here (per `expected.md`, written before this
investigation).

## What was measured, and how

**Confirming the premise: is the diagnostic actually a clang (Sema) diagnostic, not a DXIL
validation failure?** Ran ground truth (`main-debug`, `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`)
directly on the two backing `.hlsl` files:

```
> dxc.exe -E main -T gs_6_0 tools\clang\test\CodeGenHLSL\attributes-gs-no-inout-main.hlsl
...attributes-gs-no-inout-main.hlsl:18:11: error: stream-output object must be an inout parameter
exit 0x80004005 (E_FAIL -- an ordinary diagnosed error, not internal_failure)

> dxc.exe -E main -T gs_6_0 tools\clang\test\CodeGenHLSL\attributes-gs-no-inout-other.hlsl
...attributes-gs-no-inout-other.hlsl:10:10: error: stream-output object must be an inout parameter
exit 0x80004005 (E_FAIL)
```

Both diagnostics fire and exit E_FAIL, before any DXIL container exists to validate --
consistent with a front-end (Sema) check, not the DXIL validator. The diagnostic's home is
also confirmed statically: `err_hlsl_stream*`-shaped text lives in
`tools/clang/include/clang/Basic/DiagnosticSemaKinds.td` (Sema's diagnostic table), and
`ValidationTest.cpp`'s two `TEST_F` bodies call `TestCheck()` (line 337), which runs the
file's `// RUN: %dxc ... | FileCheck %s` line and diffs `FileCheck`'s output -- **not**
`CheckValidationMsgs()`, the fixture's other helper that actually invokes
`IDxcValidator::Validate` on a compiled container. So even though the fixture is named
`ValidationTest`, these two specific tests exercise the front end only, exactly as the issue
claims.

**Are the two named tests still in `ValidationTest.cpp` at ground truth?** Yes, unchanged:

```cpp
// ValidationTest.cpp:157-158 (TEST_METHOD declarations)
  TEST_METHOD(GSMainMissingAttributeFail)
  TEST_METHOD(GSOtherMissingAttributeFail)

// ValidationTest.cpp:3360-3366 (bodies)
TEST_F(ValidationTest, GSMainMissingAttributeFail) {
  TestCheck(L"..\\CodeGenHLSL\\attributes-gs-no-inout-main.hlsl");
}

TEST_F(ValidationTest, GSOtherMissingAttributeFail) {
  TestCheck(L"..\\CodeGenHLSL\\attributes-gs-no-inout-other.hlsl");
}
```

`grep`/`Select-String` for both method names against
`tools/clang/unittests/HLSL/VerifierTest.cpp` returns **zero matches** -- they have not been
added there.

## Source history, scoped correctly (and the same disconnected-branch trap as elsewhere in this batch)

Ancestor-scoped history (`git log 89e2f98e2... -- ValidationTest.cpp`, **not** `--all`) shows
both `TEST_METHOD` lines and both `TEST_F` bodies appear **only as additions** (`+`) across
every commit touching the file in this lineage; a full `git log -p` scoped the same way was
grepped for a `-` line containing either method name and found none, so the tests have never
been removed or relocated within this repository's own ground-truth ancestry.

`git log -S "GSMainMissingAttributeFail"` scoped to ground truth finds exactly one ancestor
commit, `9009fb8ec1` ("Fix Test Breakage on WSL (#8263)", this clone's clock: 2026-03-12;
confirmed an ancestor via `git merge-base --is-ancestor 9009fb8ec1... 89e2f98e2...`, exit 0).
An unscoped `git log --all -S` for the same string additionally surfaces
`8a8b29f967` ("[spirv] AMD work graphs extension (#7353)", 2025-06-03) and, most temptingly,
`406fe38220` ("Add validation checks for HS/GS attributes after parsing (#768)",
**2017-11-16** -- a plausible real-world origin, predating this issue by six years).
**Neither of those two is an ancestor of ground truth**
(`git merge-base --is-ancestor <sha> 89e2f98e2...` exits 1 for both), so -- as elsewhere in
this batch -- this local clone's history for this file is a disconnected/synthetic
reconstruction, and `9009fb8ec1` is the only commit this triage can honestly cite as
touching these lines within ground truth's own lineage. This does not change the verdict,
which rests on reading current source, not on dating its introduction.

## The broader ask ("any other tests...") is not fully quantified here

The issue's second sentence generalizes to any `ValidationTest.cpp` entry that only tests a
clang diagnostic. This triage did not enumerate every `TEST_F` in the file (multiple
thousand lines, hundreds of methods) to classify each one by which helper it calls; that is
a materially larger audit than confirming the two named methods, and the issue itself does
not name further examples. The verdict below is scoped to the two named tests, which is the
part of the request this triage can fully substantiate.

## Verdict

The requested move has not happened. Both named tests are still registered under
`ValidationTest.cpp`'s `TEST_F`/`TEST_METHOD` pair, still call the `TestCheck()`/FileCheck
path rather than `CheckValidationMsgs()`, and are absent from `VerifierTest.cpp`. The premise
-- that these two tests exercise a clang (Sema) diagnostic rather than DXIL validation -- is
confirmed both by direct compilation (E_FAIL before any DXIL container exists) and by source
reading (`TestCheck()`, not the validator helper). The issue is `Dormant`-milestoned, has no
linked PR and no comments, but nothing found here contradicts its premise or shows the work
done under a different name.

- **status**: `not-compiler-verifiable` -- no `dxc` invocation's output depends on which
  `.cpp` file registers a unit test; the applicable instrument is source reading (which file
  currently contains the `TEST_F`), backed by a compiler run that confirms the diagnostic's
  layer.
- **repro quality**: `complete` -- the issue names exact, still-locatable test methods and
  source files; nothing needed to be reconstructed.
- **history**: n/a in the compile-history/bisection sense (test-fixture placement has no
  compiler-version axis); by source reading, both tests have existed in `ValidationTest.cpp`
  unmoved throughout this repository's own ground-truth ancestry, and remain there today.
- **suggested action**: `still-valid-keep-open` -- a live, unaddressed, narrowly-scoped
  test-organization request; the `Dormant` milestone reflects priority, not resolution.
- **labels**: current (`enhancement`, `test`) already describe this accurately; no change
  proposed.
- **text_stale**: not applied -- the issue's description of where the two tests live and
  what they test is still accurate.

## Caveats

- Scoped to the two named tests. The issue's broader "any other such tests" clause was not
  independently audited across all of `ValidationTest.cpp`'s several hundred methods; see
  above.
- Local git history for this file does not reproduce the real-world chronology for these two
  tests (the plausible 2017 origin commit is not an ancestor of ground truth here); dates
  attributed to source changes above come only from commits confirmed as ground-truth
  ancestors. GitHub-sourced facts (creation date, milestone, timeline) come independently
  from the live API.
- No GPU/runtime step applies; this is entirely a source-tree and single-invocation
  compiler check.
