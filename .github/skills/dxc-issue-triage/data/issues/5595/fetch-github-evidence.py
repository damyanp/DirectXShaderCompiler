#!/usr/bin/env python3
"""GitHub-side evidence for issue #5595: duplicate issue #5552, the fix attempt
PR #5600 ("Fixes #5595"), and the cross-reference timeline. Read-only `gh`
calls only (issue view / pr view / api GET), per SKILL.md's hard rule.

Run from anywhere:
    python fetch-github-evidence.py > manual-case-github-evidence.txt
"""
import subprocess
import sys


def run(argv):
    print("$ " + subprocess.list2cmdline(argv))
    out = subprocess.run(argv, capture_output=True, text=True, check=False)
    text = (out.stdout or "") + (out.stderr or "")
    print(text.rstrip("\n"))
    print(f"(exit {out.returncode})")
    print()


def main():
    print("## Cross-reference timeline on #5595 (read-only; predates this triage)")
    run(["gh", "api",
         "repos/microsoft/DirectXShaderCompiler/issues/5595/timeline",
         "--paginate", "--jq",
         '.[] | select(.event=="cross-referenced") | '
         '"\\(.created_at)  \\(.source.issue.repository.full_name)#'
         '\\(.source.issue.number)  \\(.source.issue.title)"'])

    print("## Duplicate issue #5552 (closed 2023-08-30 as 'Duplicated by #5595')")
    run(["gh", "issue", "view", "5552",
         "--repo", "microsoft/DirectXShaderCompiler",
         "--json", "number,title,state,createdAt,closedAt,body"])
    run(["gh", "issue", "view", "5552",
         "--repo", "microsoft/DirectXShaderCompiler",
         "--json", "comments", "-q",
         ".comments[] | \"\\(.author.login) \\(.createdAt)\\n\\(.body)\""])

    print("## PR #5600 top-level state (never merged)")
    run(["gh", "pr", "view", "5600",
         "--repo", "microsoft/DirectXShaderCompiler",
         "--json",
         "number,title,state,createdAt,updatedAt,closedAt,mergedAt,mergeCommit,"
         "isDraft,headRefName,baseRefName,changedFiles,additions,deletions"])

    print("## PR #5600 review states (extensive review, then no further activity)")
    run(["gh", "pr", "view", "5600",
         "--repo", "microsoft/DirectXShaderCompiler",
         "--json", "reviews", "-q",
         '.reviews[] | "\\(.author.login) \\(.state) \\(.submittedAt)"'])

    print("## PR #5600 commit list (last commit 2023-09-22; no activity since)")
    run(["gh", "pr", "view", "5600",
         "--repo", "microsoft/DirectXShaderCompiler",
         "--json", "commits", "-q",
         '.commits[] | "\\(.committedDate)  \\(.messageHeadline)"'])


if __name__ == "__main__":
    sys.exit(main())
