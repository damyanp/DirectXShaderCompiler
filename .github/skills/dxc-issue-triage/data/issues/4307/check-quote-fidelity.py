"""Mechanically compare #4307's quoted compiler output with a release capture.

Run from anywhere:  python check-quote-fidelity.py

The issue body quotes one line of dxc output. "The reconstructed shader looks
similar" is not evidence that we are measuring the reporter's instance; comparing
the quote token-by-token against a real capture is. The reporter did not name a
build, so this checks the release contemporary with the filing date
(2022-03-03 -> v1.6.2112, published 2021-12-08) and reports every difference it
finds rather than a bare pass/fail.

Normalisation is limited to two documented things: the source filename
(main.hlsl -> repro.hlsl) and runs of whitespace, because GitHub's blockquote
rendering joined dxc's two output lines into one in the issue body.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "out-v1.6.2112.txt"
QUOTED = (
    "main.hlsl:11: error: Function main with parameter is not permitted, "
    "it should be inlined. Validation failed."
)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("main.hlsl", "repro.hlsl")).strip()


def main() -> int:
    body = json.loads((HERE / "issue.json").read_text(encoding="utf-8"))["body"]
    if QUOTED not in body.replace("\r\n", "\n"):
        sys.exit("the quoted line is not in issue.json verbatim -- update QUOTED")

    text = CAPTURE.read_text(encoding="utf-8")
    stderr = text.split("--- stderr ---", 1)[1]
    got = norm(stderr)
    want = norm(QUOTED)

    print(f"capture:  {CAPTURE.name}")
    print(f"quoted:   {want}")
    print(f"captured: {got}")
    # The capture carries dxc's leading "error: validation errors" summary line,
    # which the reporter did not quote; the claim under test is containment.
    ok = want in got
    print(f"\nRESULT: the issue's quoted line is {'PRESENT' if ok else 'ABSENT'} "
          f"verbatim in the v1.6.2112 capture (after filename + whitespace "
          f"normalisation only)")
    if not ok:
        for a, b in zip(want.split(), got.split()):
            if a != b:
                print(f"  first difference: quoted {a!r} vs captured {b!r}")
                break
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
