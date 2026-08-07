"""Is the DXIL on today's `main` still the DXIL the reporter pasted in 2021?

Extracts `define void @main() ... }` from the issue body (issue.json) and from
the ground-truth capture (out-main-debug.txt) and compares them line for line.
Both inputs live in this directory; paths come from __file__, so there are no
machine-specific paths and a stranger can re-derive the result from the repo.

    python compare-dxil.py          # writes manual-case-dxil-identity.txt
"""
import difflib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "manual-case-dxil-identity.txt")
BLOCK = re.compile(r"define void @main\(\).*?\n\}", re.S)


def block(text, where):
    m = BLOCK.search(text.replace("\r", ""))
    if not m:
        # Distinguish "nothing matched" from "nothing was read": a reader must
        # never be shown an empty comparison that looks like agreement.
        print(f"PARSE-WARNING: no `define void @main()` block in {where}",
              file=sys.stderr)
        return None
    return [ln.rstrip() for ln in m.group(0).split("\n")]


def main():
    issue = json.load(open(os.path.join(HERE, "issue.json"), encoding="utf-8"))
    reported = block(issue["body"], "issue.json (the 2021 report)")
    capture = open(os.path.join(HERE, "out-main-debug.txt"),
                   encoding="utf-8").read()
    measured = block(capture, "out-main-debug.txt (ground truth)")

    lines = [
        "# Does today's main still emit the DXIL pasted in the 2021 report?",
        f"# Written by {os.path.basename(__file__)} -- rerun it to re-derive.",
        "# left : the `define void @main()` block quoted in issue.json",
        "# right: the same block from out-main-debug.txt",
        f"# $ {subprocess.list2cmdline([os.path.basename(sys.executable), os.path.basename(__file__)])}",
        "",
    ]
    if reported is None or measured is None:
        lines += ["PARSE-WARNING: one side could not be extracted; "
                  "no comparison was made."]
    else:
        lines += [
            f"# lines quoted in the issue : {len(reported)}",
            f"# lines emitted by main-debug: {len(measured)}",
            f"# identical                  : {reported == measured}",
            "",
        ]
        diff = list(difflib.unified_diff(reported, measured, "issue-body-2021",
                                         "main-debug", lineterm=""))
        lines += ["--- diff ---"] + (diff or ["(no differences)"])
        lines += ["", "--- block as emitted by main-debug ---"] + measured
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
