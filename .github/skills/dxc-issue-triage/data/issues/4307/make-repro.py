"""Extract the reporter's shader from the fetched issue and write it verbatim.

Run from anywhere:  python make-repro.py

Writing the repro by hand risks silently changing line numbers, and #4307's whole
subject is *which line* the diagnostic points at: the reported error names line 11
(the entry-point signature) and the reporter asks for line 22 (the offending
statement). Deriving repro.hlsl mechanically from issue.json makes that fidelity
checkable instead of asserted.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def extract(body: str, index: int) -> str:
    blocks = re.findall(r"```(?:hlsl|HLSL)\r?\n(.*?)```", body, re.DOTALL)
    if not blocks:
        sys.exit("no fenced hlsl block found")
    return blocks[index].replace("\r\n", "\n")


def main() -> int:
    issue = json.loads((HERE / "issue.json").read_text(encoding="utf-8"))

    body_src = extract(issue["body"], 0)
    (HERE / "repro.hlsl").write_text(body_src, encoding="utf-8", newline="\n")

    comment_src = extract(issue["comments"][0]["body"], 0)
    (HERE / "comment-repro.hlsl").write_text(
        comment_src, encoding="utf-8", newline="\n"
    )

    lines = body_src.split("\n")
    print(f"repro.hlsl: {len(lines)} lines")
    for n in (11, 22):
        print(f"  line {n}: {lines[n - 1].rstrip()}")
    print(f"comment-repro.hlsl: {len(comment_src.splitlines())} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
