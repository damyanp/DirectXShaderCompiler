"""Generate the manual-case captures for issue 6727.

Two things this file exists to prove, neither of which `triage.py run` can
express:

1. the FXC/DXC comparison. FXC is not a registered triage compiler, and the
   comparison is the core evidence: the *same* HLSL that DXC lowers to two
   separate operations is lowered by FXC to one DXBC instruction with two
   destinations.
2. which single predicate clause each control isolates.

Everything is run through subprocess with the argv echoed by
`subprocess.list2cmdline`, so the command line printed into the capture is the
command line that ran, rather than a transcription of it. Paths are redacted to
placeholders: no machine-specific absolute path is written to disk.

Run from this directory:  python make-manual-cases.py
"""

import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/6727 -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))


def find_dxc():
    exe = os.environ.get("DXC")
    if exe and os.path.exists(exe):
        return exe
    for cfg in ("Debug", "Release", "RelWithDebInfo"):
        cand = os.path.join(REPO, "build", cfg, "bin", "dxc.exe")
        if os.path.exists(cand):
            return cand
    sys.exit("dxc not found; set DXC")


def find_fxc():
    exe = os.environ.get("FXC")
    if exe and os.path.exists(exe):
        return exe
    pf = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles")
    if not pf:
        sys.exit("fxc not found; set FXC")
    pat = os.path.join(pf, "Windows Kits", "10", "bin", "*", "x64", "fxc.exe")
    hits = sorted(glob.glob(pat))
    if not hits:
        sys.exit("fxc not found; set FXC")
    return hits[-1]


DXC = find_dxc()
FXC = find_fxc()

REDACT = [
    (DXC, "<repo>/build/Debug/bin/dxc.exe"),
    (REPO, "<repo>"),
    (FXC, "<sdk>/Windows Kits/10/bin/<ver>/x64/fxc.exe"),
]


def redact(text):
    for real, token in REDACT:
        text = text.replace(real, token).replace(real.replace("\\", "/"), token)
    return text


def run(argv, note):
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return (f"$ {redact(subprocess.list2cmdline(argv))}\n"
            f"[note] {note}\n"
            f"[exit] {p.returncode}\n"
            f"{redact(out).rstrip()}\n\n")


def tail(text, n):
    lines = text.rstrip().splitlines()
    return "\n".join(lines[-n:])


def fxc_body(argv, note, keep=12):
    """FXC's header block is 30 lines of resource tables; keep the code."""
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return (f"$ {redact(subprocess.list2cmdline(argv))}\n"
            f"[note] {note}\n"
            f"[exit] {p.returncode}\n"
            f"[trimmed] resource/signature header omitted; last {keep} lines of "
            f"the disassembly follow\n"
            f"{redact(tail(out, keep))}\n\n")


def dxc_grep(argv, note, needles):
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
    out = redact((p.stdout or "") + (p.stderr or ""))
    kept = [ln.strip() for ln in out.splitlines()
            if any(n in ln for n in needles)]
    return (f"$ {redact(subprocess.list2cmdline(argv))}\n"
            f"[note] {note}\n"
            f"[exit] {p.returncode}\n"
            f"[filtered] lines containing: {', '.join(needles)}\n"
            + "\n".join(kept) + "\n\n")


def fxc_vs_dxc():
    body = (
        "# manual case: FXC/DXBC reaches the two-output instruction from the\n"
        "# same HLSL that DXC/DXIL lowers to two separate operations.\n"
        "#\n"
        "# DXBC has one `udiv destQUOT, destREM, src0, src1` instruction and one\n"
        "# `imul destHI, destLO, src0, src1` instruction. DXIL keeps them as\n"
        "# opcodes 43 and 41 (op class binaryWithTwoOuts) but no HLSL spelling\n"
        "# in DXC lowers to either.\n\n")
    body += fxc_body(
        [FXC, "/nologo", "/T", "cs_5_0", "/E", "main", "control-fxc-divrem.hlsl"],
        "quotient and remainder of one operand pair -> ONE `udiv` with two "
        "destination registers")
    body += dxc_grep(
        [DXC, "-T", "cs_6_0", "-E", "main", "control-fxc-divrem.hlsl"],
        "the identical source through DXC -> two independent instructions, "
        "no dx.op call",
        ["udiv", "urem", "binaryWithTwoOuts"])
    body += fxc_body(
        [FXC, "/nologo", "/T", "cs_5_0", "/E", "main", "control-no-divide.hlsl"],
        "an ordinary 32-bit multiply is ALREADY the two-output instruction in "
        "DXBC: `imul null, r1.y, ...` discards the high half into null, which "
        "is the half HLSL cannot ask for")
    body += dxc_grep(
        [DXC, "-T", "cs_6_0", "-E", "main", "repro.hlsl"],
        "the repro through DXC: the high half costs a 64-bit multiply and the "
        "optional 64-bit feature flag",
        ["64-Bit", "mul nuw", "lshr", "trunc i64", "udiv", "urem"])
    return body


def clause_table():
    import re
    clauses = [r"define void @main\(\)", r"udiv i32", r"urem i32",
               r"binaryWithTwoOuts"]
    files = ["out-main-debug.txt",
             "variant-control-parse-error-main-debug.txt",
             "variant-control-no-divide-main-debug.txt",
             "variant-control-token-visible-main-debug.txt"]
    body = (
        "# manual case: which clause of match.json each control isolates.\n"
        "# match.json is all_of[ regex 'define void @main()', regex 'udiv i32',\n"
        "#                      regex 'urem i32', not_regex 'binaryWithTwoOuts' ]\n"
        "# so a control is only informative if it flips exactly one column.\n"
        "# Re-derive with: python make-manual-cases.py\n\n")
    head = f"{'capture':52}" + "".join(f"{c:26}" for c in clauses)
    body += head + "\n" + "-" * len(head) + "\n"
    for f in files:
        with open(os.path.join(HERE, f), encoding="utf-8",
                  errors="replace") as fh:
            text = fh.read()
        row = f"{f:52}"
        for c in clauses:
            row += f"{str(bool(re.search(c, text, re.MULTILINE))):26}"
        body += row + "\n"
    body += (
        "\nparse-error   emits no DXIL at all, so every positive anchor is "
        "absent while the absence clause is satisfied for free.\n"
        "              Under a bare not_regex this run would have scored as a "
        "textbook reproduction; the anchors are what stop it.\n"
        "no-divide     flips only the udiv/urem anchors: the predicate is not "
        "vacuously true of any clean compile.\n"
        "token-visible flips only binaryWithTwoOuts (via -Zi -Qembed_debug "
        "echoing the source into !dx.source.contents):\n"
        "              the absence clause is falsifiable, not merely unmet.\n")
    return body


def main():
    for name, text in (("manual-case-fxc-vs-dxc.txt", fxc_vs_dxc()),
                       ("manual-case-clause-table.txt", clause_table())):
        with open(os.path.join(HERE, name), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(text)
        print("wrote", name)


if __name__ == "__main__":
    main()
