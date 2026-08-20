> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5790](https://github.com/microsoft/DirectXShaderCompiler/issues/5790).

This is a repository-settings question, so I checked the current GitHub configuration for
`main` rather than running the compiler.

As of today, "Require conversation resolution before merging" is **not** enabled for `main`:

- Classic branch protection: `"required_conversation_resolution": {"enabled": false}`
- The `microsoft-production-ruleset` (org-sourced, applies to `~DEFAULT_BRANCH`, created
  2025-05-07) also has its equivalent rule off: `"required_review_thread_resolution": false`

So the 2023-10-25 note that this "has been done for all branches" no longer matches the live
setting, which is consistent with @Keenuts' 2025-04-23 report that an approval-with-a-comment
still let auto-merge submit PR #7369. GitHub does not expose branch-protection change
history, so I can't tell whether the classic setting was later turned off, or whether it was
superseded when the `microsoft-production-ruleset` was introduced in May 2025 without this
rule enabled.

Since this is an org/repo-admin setting rather than a compiler behavior, only a maintainer
with admin access can say whether that was intentional or should be re-enabled.

---
<sub>Triaged with AI assistance. The GitHub API results above were fetched read-only just now;
please flag anything that looks wrong.</sub>
