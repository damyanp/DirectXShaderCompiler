"""Enumerate the commits inside #2923's measured regression window.

The window v1.6.2104 -> v1.6.2106 comes from `history-2923.py`; the cross-probe in
`crossprobe-2923.py` narrows the change to the pass DLL (`lib/DxilPIXPasses`). This
script only *counts* what is in that window, so the draft can bound the search
without naming a commit -- release-to-release probing cannot distinguish them.

It echoes every command before running it, so a reader can re-derive the output
below each `$` line rather than trusting a transcription.

    cd <repo>/.github/skills/dxc-issue-triage/data/issues/2923
    python window-commits.py > manual-case-window-commits.txt   # NOT the same filename
"""
import subprocess
import sys

REPO = ["git", "-C", "../../../../../.."]

CASES = [
    ("every commit touching the PIX pass directory in the window",
     ["log", "--oneline", "v1.6.2104..v1.6.2106", "--", "lib/DxilPIXPasses/"]),
    ("...of those, the ones touching the value-to-declare pass",
     ["log", "--oneline", "v1.6.2104..v1.6.2106", "--",
      "lib/DxilPIXPasses/DxilDbgValueToDbgDeclare.cpp"]),
    ("...and the ones touching the numbering pass named in the issue title",
     ["log", "--oneline", "v1.6.2104..v1.6.2106", "--",
      "lib/DxilPIXPasses/DxilAnnotateWithVirtualRegister.cpp"]),
]


def main():
    print("# Commits inside #2923's measured regression window "
          "(v1.6.2104 -> v1.6.2106).")
    print("# Written by window-commits.py -- rerun it to re-derive this file.")
    print("# This is a COUNT, not an attribution: nine candidates cannot be told "
          "apart by\n# release-to-release probing, and no commit was built in "
          "isolation.")
    for title, args in CASES:
        print(f"\n{'=' * 78}\n# {title}")
        print("$ git " + " ".join(args))
        p = subprocess.run(REPO + args, capture_output=True, text=True,
                           errors="replace")
        if p.returncode:
            print(p.stderr.strip())
            return 1
        out = p.stdout.rstrip("\n")
        print(out)
        print(f"# count: {len(out.splitlines()) if out else 0}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
