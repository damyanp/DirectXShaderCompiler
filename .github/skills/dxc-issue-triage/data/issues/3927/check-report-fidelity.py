"""#3927: does the reconstructed repro reproduce the reporter's exact module?

The issue body quotes a full `spirv-dis` listing and says it was produced with
`dxc_2021_07_01`, which is release v1.6.2106. This script compares that quoted listing,
extracted straight out of issue.json, against out-v1.6.2106.txt -- the capture this triage
took by running repro.hlsl on that same release.

If they agree line for line, the reconstruction is not merely "a shader that shows the
symptom", it is the reporter's case.

Writes manual-case-report-fidelity.txt. Run from this directory:

    python check-report-fidelity.py > manual-case-report-fidelity.txt

Whitespace is normalised (the disassembler right-aligns result ids to a column that depends
on the longest id, and the issue body was pasted through a browser); nothing else is.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = "v1.6.2106"


def norm(lines):
    return [re.sub(r"\s+", " ", ln).strip() for ln in lines if ln.strip()]


def reporter_listing():
    with open(os.path.join(HERE, "issue.json"), encoding="utf-8") as f:
        body = json.load(f)["body"]
    blocks = re.findall(r"```[a-zA-Z]*\r?\n(.*?)```", body, re.S)
    for b in blocks:
        if b.lstrip().startswith("; SPIR-V"):
            return norm(b.splitlines())
    sys.exit("no SPIR-V listing found in the issue body")


def capture_listing():
    path = os.path.join(HERE, f"out-{RELEASE}.txt")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    out = text.split("--- stdout ---", 1)[1].split("--- stderr ---", 1)[0]
    return norm(out.splitlines())


def main():
    print(f"#3927 -- reporter's quoted disassembly vs this triage's {RELEASE} capture")
    print(f"# sources: issue.json (body) and out-{RELEASE}.txt")
    print(f"# the reporter states the listing came from dxc_2021_07_01, i.e. {RELEASE}")
    print()

    a, b = reporter_listing(), capture_listing()
    print(f"[reporter lines] {len(a)}")
    print(f"[capture  lines] {len(b)}")

    if a == b:
        print("[RESULT] identical line for line "
              "-- repro.hlsl reproduces the reporter's exact module")
        return 0

    print("[RESULT] DIFFERS -- first differences follow")
    import difflib
    shown = 0
    for line in difflib.unified_diff(a, b, "reporter", RELEASE, n=1, lineterm=""):
        print("  " + line)
        shown += 1
        if shown > 40:
            print("  ... (truncated)")
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
