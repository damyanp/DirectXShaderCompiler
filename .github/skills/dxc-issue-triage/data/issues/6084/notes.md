# #6084 — [CI] Add clang-cl on windows build to test pipeline

## Summary of the request

Filed 2023-11-30 by python3kgae, contingent on #5480 ("Compile with clang-cl on
windows", closed 2024-01-29). Once that prerequisite landed, #6084 asks that a
`clang-cl` Windows build be added to the *regular* CI pipeline — the issue body
explicitly says "Currently we only compile with clang-cl for release builds ...
we should enable this on all of our builds", i.e. release-only coverage is called
out as insufficient.

This is a CI/process request, not a compiler-behaviour claim. There is no HLSL
input or `dxc` invocation that could show it "reproducing" or "fixed"; the only
evidence is the CI pipeline definition itself and its edit history/timeline.
Per the skill's guidance for non-compiler claims, the check is to find the
producing artifact (`azure-pipelines.yml` / GitHub Actions workflows) rather than
invent a hollow predicate.

## What actually happened afterwards

The issue's own cross-reference timeline (`gh api .../issues/6084/timeline`)
shows exactly two cross-references, both pre-dating this triage:

- 2023-12-14 — PR #6107 "[CI] add clang-cl to azure pipeline" ("Fixes: #6084")
- 2024-01-29 — issue #5480 (the prerequisite) closing

PR #6107 has two commits: "Only enabled clang-cl for release build since the
pipeline is already slow. Might need to remove one of Nix build if the pipeline
is too slow." and a follow-up "define clang-cl for normal build." — i.e. the PR
author was actively working toward the "all builds" ask #6084 makes, not just
the release-only case the first commit shipped.

**The PR was never merged.** `gh pr view 6107` reports `mergedAt: null,
mergeCommit: null`, and it was closed on 2026-01-22 by a maintainer
(damyanp) with the comment: *"This PR was closed as it has not been updated in
the last two years. Please feel free to reopen if this PR should be merged and
is in a reviewable state."* This is the same "agreed fix lapsed via an
inactivity sweep" pattern documented for #2427 in this skill — the design
question was settled, a PR existed, and it was closed unmerged for staleness
rather than being rejected on its merits or superseded by other work.

## Ground-truth check of the actual CI definition

At the registered ground-truth commit (`main-debug`, git commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, self-reported version
`1.9.0.5465 (triage, 7665270b9)`; provenance note in
`.cache/compilers/main-debug.json` records the binary's self-reported fork-local
SHA `ab5400907` is source-identical to this public commit):

```
git grep -n "clang-cl" 89e2f98e29c289ae8ad9e00dd310104fea9fd7df -- azure-pipelines.yml .github
```

returns **no matches**. `git ls-tree` confirms `.github/workflows/` only
contains `clang-format-checker.yml`, `coverage-gh-pages.yml` and
`pr-description-checker.yml` — none of which build DXC. `azure-pipelines.yml` is
the only build/test pipeline definition and its job list (`Windows`, `Nix`,
`Offload`) has no `clang-cl` job or step at all — not even the release-only
variant the issue says already existed in 2023. (`CMakeSettings.json` still
carries local `x64-clang-cl-Release`/`x64-clang-cl-Debug` presets for Visual
Studio, but those are not exercised by CI.)

So, as of ground truth: the CI pipeline has **no** clang-cl Windows build at all
(the ask is fully unaddressed), and the one PR that would have closed it was
closed unmerged for inactivity, not because the ask was withdrawn or completed
elsewhere.

## Verdict

- **status:** `not-compiler-verifiable` — nothing about this can be measured by
  compiling a shader; it is a claim about the CI pipeline definition.
- **repro-quality:** `prose-only`.
- **history:** n/a (no dxc bisection applies).
- **Text staleness:** none. The issue's title and body still accurately describe
  a gap that is still present on `main` (indeed the "release only" complaint in
  the body is now an *understatement* — there is currently no clang-cl Windows
  build in CI at all, release or otherwise).
- **Suggested action:** `still-valid-keep-open`. The request is unmet, the
  prerequisite (#5480) is long done, and the one prior attempt to close it
  (#6107) lapsed procedurally rather than being resolved. Labels `enhancement`
  and `ci` both still fit; no label change proposed.

## Confidence

High confidence in the two file-level facts (no clang-cl in current CI; PR #6107
unmerged/closed-stale) since both were checked directly against the ground-truth
tree and the live GitHub API. Whether a maintainer still *wants* this done is a
human judgement call this triage cannot settle — it is presented as evidence,
not as a recommendation to act.
