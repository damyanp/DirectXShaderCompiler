# #5790 -- [Github] Enable "Require conversation resolution before merging" ?

## What was asked

A repository-process request, not a compiler bug: enable GitHub's "Require conversation
resolution before merging" for `main`, so an approving review that still carries an
unresolved comment ("a nit") does not let auto-merge submit the PR immediately.

## Timeline (from `issue.json`)

- 2023-09-27 -- Keenuts files the request.
- 2023-10-25 -- pow2clk (maintainer): "This has been done for all branches."
- 2025-04-23 -- Keenuts reports the symptom recurred: approved PR #7369 with a comment, and
  auto-merge merged it anyway. Asks "Was the setting changed?"

No cross-reference events exist on the issue (`gh api .../issues/5790/timeline`, empty
result for `event=="cross-referenced"`), so nothing else on GitHub links back to it.

## What is actually checkable

There is no shader, command line, or compiler behaviour here -- the only fact `dxc`/this repo's
source can never answer is a GitHub repository setting. That setting is public metadata and
is read directly, read-only, via `gh api`:

- Classic branch protection for `main`
  (`manual-case-branch-protection.json`, captured 2026-08-19):
  ```
  "required_conversation_resolution": { "enabled": false }
  ```
- The repository also carries an **organization-sourced** ruleset targeting the default
  branch, `microsoft-production-ruleset` (`manual-case-rulesets-list.json`,
  `manual-case-ruleset-5351760.json`). Its `pull_request` rule is the ruleset-system
  equivalent of the same setting, and it too is off:
  ```
  "required_review_thread_resolution": false
  ```
  This ruleset's `created_at`/`updated_at` is **2025-05-07**, about two weeks *after*
  Keenuts' 2025-04-23 comment. So the org ruleset that currently governs `main` post-dates
  the reported regression, and it still does not carry conversation/thread resolution.
  There is no earlier ruleset revision to inspect (the API only exposes the current ruleset,
  not a change history), so this cannot establish whether the classic branch-protection
  toggle was flipped off at some point between 2023-10-25 and 2025-04-23, or whether it was
  superseded/overridden when the org ruleset was introduced on 2025-05-07 with this rule left
  unset. Either way, the setting the issue asks for is not in effect on `main` today, on both
  mechanisms GitHub exposes for it.

  A second ruleset, `Copilot review for default branch` (id 20001303), is unrelated (Copilot
  code-review automation only).

## Assessment

- The maintainer's 2023-10-25 statement that this "has been done for all branches" no longer
  describes current configuration: as of this triage, `main` requires neither conversation
  resolution (classic branch protection) nor thread resolution (org ruleset). This directly
  corroborates Keenuts' 2025-04-23 report rather than leaving it as an unconfirmed anecdote.
- This is `not-compiler-verifiable`: there is no compiler input to run, and the finding rests
  entirely on reading GitHub's own configuration API, which is exactly the kind of process
  evidence the "not-compiler-verifiable" outcome is meant to capture (cf. #3150, #3276).
- Suggested action: `needs-human-judgement` / re-confirm with a maintainer. The issue's own
  text is stale in the sense that the thread's most recent maintainer-facing claim ("has been
  done for all branches") is contradicted by the live setting, but this is a repo-admin
  decision, not something this triage can or should resolve further -- only a maintainer with
  admin access can say whether the setting was intentionally left off, was dropped when the
  ruleset replaced/supplemented classic branch protection, or should be turned back on.

## Caveats / what could not be determined

- No history of *when* the classic protection setting changed is available through the API
  (GitHub does not expose branch-protection change history); only the current value.
- Cannot determine whether other branches (release branches) have conversation/thread
  resolution enabled -- the issue and evidence here are scoped to `main` only, matching the
  issue title.
- This is a live, mutable, third-party (GitHub) setting: the captured values are true as of
  2026-08-19T (this triage) and could change independently of any DXC source commit, so
  `triaged_with_commit` records the ground-truth DXC compiler build for consistency with other
  issues in this batch, even though the compiler played no role in this verdict.
