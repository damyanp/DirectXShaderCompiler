#!/usr/bin/env python3
"""Unresolved PR review threads on #5600, showing why the implementation
stalled (a maintainer design objection about lit local-config handling).
Read-only `gh api graphql` (GET-equivalent query), per SKILL.md's hard rule.

Run from anywhere:
    python fetch-review-threads.py > manual-case-pr5600-unresolved-threads.txt
"""
import json
import subprocess
import sys

QUERY = (
    'query { repository(owner:"microsoft", name:"DirectXShaderCompiler") { '
    "pullRequest(number:5600) { reviewThreads(first:50) { totalCount nodes { "
    "isResolved comments(first:10) { nodes { author { login } createdAt body } "
    "} } } } } }"
)


def main():
    argv = ["gh", "api", "graphql", "-f", f"query={QUERY}"]
    print("$ " + subprocess.list2cmdline(argv))
    out = subprocess.run(argv, capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    unresolved = [t for t in threads if not t["isResolved"]]
    print(f"total review threads: {len(threads)}, unresolved: {len(unresolved)}")
    print()
    for t in unresolved:
        print("=== unresolved thread ===")
        for c in t["comments"]["nodes"]:
            print(f"{c['author']['login']} {c['createdAt']}")
            print(c["body"])
            print("--")
        print()


if __name__ == "__main__":
    sys.exit(main())
