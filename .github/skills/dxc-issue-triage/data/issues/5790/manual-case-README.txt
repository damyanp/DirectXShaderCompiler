# How the captures in this directory were produced

These are read-only `gh api` GET calls, run 2026-08-19, checking the current, public
GitHub repository configuration -- there is no compiler input for this issue.

```
gh api repos/microsoft/DirectXShaderCompiler/branches/main/protection
gh api repos/microsoft/DirectXShaderCompiler/rulesets
gh api repos/microsoft/DirectXShaderCompiler/rulesets/5351760
```

Each was piped through `python -m json.tool` for readability and saved verbatim as
`manual-case-branch-protection.json`, `manual-case-rulesets-list.json` and
`manual-case-ruleset-5351760.json` respectively. No fields were edited.

Cross-reference timeline check (also read-only, confirms this triage created no event):

```
gh api repos/microsoft/DirectXShaderCompiler/issues/5790/timeline?per_page=100 --jq \
  '.[] | select(.event=="cross-referenced") | "\(.created_at)  \(.source.issue.repository.full_name)#\(.source.issue.number)"'
```
produced no output -- no cross-references exist on this issue.
