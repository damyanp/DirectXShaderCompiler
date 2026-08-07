"""Record what happened to the PRs that reference #3377.

SKILL.md, step 5: "When a thread has already diagnosed the behaviour, re-confirming
it adds nothing; check what happened to the resolution instead." The issue timeline
is the cheap way to find those, and it is read-only.

Every command here is a `gh` GET. Nothing is posted, edited or labelled.

    cd <repo>/.github/skills/dxc-issue-triage/data/issues/3377
    python linked-prs.py > manual-case-linked-prs.txt
"""
import subprocess
import sys

REPO = "microsoft/DirectXShaderCompiler"
CASES = [
    ("cross-reference events on #3377 (who linked it, from where)",
     ["api", f"repos/{REPO}/issues/3377/timeline?per_page=100", "--jq",
      '.[] | select(.event=="cross-referenced") | '
      '"\\(.created_at)  \\(.actor.login)  #\\(.source.issue.number)  '
      '\\(.source.issue.title)"']),
    ("PR 4538 state",
     ["pr", "view", "4538", "--repo", REPO, "--json",
      "number,title,state,mergedAt,closedAt,createdAt,author", "--template",
      '{{.number}} {{.title}}\n  state={{.state}} created={{.createdAt}} '
      'mergedAt={{.mergedAt}} closedAt={{.closedAt}} author={{.author.login}}\n']),
    ("PR 4554 state",
     ["pr", "view", "4554", "--repo", REPO, "--json",
      "number,title,state,mergedAt,closedAt,createdAt,author", "--template",
      '{{.number}} {{.title}}\n  state={{.state}} created={{.createdAt}} '
      'mergedAt={{.mergedAt}} closedAt={{.closedAt}} author={{.author.login}}\n']),
    ("PR 4554 body -- names this issue as the defect it fixes",
     ["pr", "view", "4554", "--repo", REPO, "--json", "body", "--template",
      '{{.body}}']),
    ("PR 4554 human comments -- why it did not land",
     ["api", f"repos/{REPO}/issues/4554/comments", "--jq",
      '.[] | select(.user.login != "AppVeyorBot") | "\\(.user.login): \\(.body)"']),
]


def main():
    print("# What happened to the fixes proposed for #3377.")
    print("# Written by linked-prs.py -- rerun it to re-derive this file.")
    print("# All commands are read-only `gh` GETs.")
    for title, args in CASES:
        print(f"\n{'=' * 78}\n# {title}")
        print("$ gh " + subprocess.list2cmdline(args))
        p = subprocess.run(["gh"] + args, capture_output=True, text=True,
                           errors="replace", shell=False)
        if p.returncode:
            print(p.stderr.strip())
            return 1
        print(p.stdout.rstrip("\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
