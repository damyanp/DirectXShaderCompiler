# Expected symptom

This is a repository-configuration request, not a compiler defect: enable GitHub's
"Require conversation resolution before merging" (API: `required_conversation_resolution`
on classic branch protection, or `required_review_thread_resolution` under the newer
repository-ruleset `pull_request` rule) on the `main` branch, so that a reviewer's unresolved
comment blocks auto-merge even when the review itself is an approval.

Reporter's account, in order:
- 2023-09-27 (body): asks whether the setting should be enabled, because auto-merge currently
  submits a PR that has an approval-with-a-nit-comment.
- 2023-10-25 (pow2clk, maintainer): "This has been done for all branches."
- 2025-04-23 (Keenuts): reports that approving PR #7369 with a comment still let auto-merge
  merge it, and asks "Was the setting changed?" -- i.e. the symptom the issue originally
  described (a comment does not block auto-merge) is observed again, after being told it had
  been fixed.

There is no compiler input, shader, or command line to run; the only checkable fact is the
repository's *current* branch-protection/ruleset configuration for `main`, which is public
GitHub metadata readable through `gh api` (read-only GET). "Reproduces" here means: the
conversation-resolution requirement is currently OFF for `main`, matching Keenuts' 2025-04-23
observation and contradicting pow2clk's 2023-10-25 claim. "Does not reproduce" means it is
currently ON.

Repro quality: prose-only / not-compiler-verifiable -- this is entirely a GitHub repository
settings question, not something `dxc` can be run against.
