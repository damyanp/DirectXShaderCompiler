"""Generates manual-case-optlevels.txt for issue 3429.

Question it answers: the issue body says "When disabling optimization it works". At which
optimization levels does the shader actually compile? Every command is echoed with
subprocess.list2cmdline(), so the transcript is what ran rather than what someone typed.

Usage (from this directory):
    python make-optlevel-case.py [path-to-Debug-bin]
"""

import os
import subprocess
import sys

BIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "..",
    "build", "Debug", "bin")
BIN = os.path.abspath(BIN)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "manual-case-optlevels.txt")
DXC = os.path.join(BIN, "dxc.exe")

LEVELS = ["-Od", "-O0", "-O1", "-O2", "-O3"]
RULE = "TGSM pointers must originate from an unambiguous TGSM global variable."


def main():
    lines = [
        "# issue: 3429",
        "# what: which optimization levels reject repro.hlsl, and which compile it.",
        "# generator: make-optlevel-case.py (committed next to its output)",
        "# bin: " + BIN,
        "#",
        "# The issue body says: \"When disabling optimization it works, so it seems like some",
        "# optimization might change the generated DXIL.\"  Measured below.",
        "",
    ]
    seen_rule = 0
    for lvl in LEVELS:
        argv = [DXC, "-E", "main", "-T", "cs_6_0", lvl, "repro.hlsl"]
        p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
        combined = (p.stdout or "") + (p.stderr or "")
        hit = RULE in combined
        seen_rule += 1 if hit else 0
        lines.append("=" * 78)
        lines.append("$ " + subprocess.list2cmdline(argv))
        lines.append("[exit] %d (0x%08X)" % (p.returncode, p.returncode & 0xFFFFFFFF))
        lines.append("[TGSM rule emitted] %s" % ("yes" if hit else "no"))
        lines.append("--- stderr ---")
        lines.append(combined.strip() if hit else "(no TGSM diagnostic; "
                     "stdout is the disassembly, omitted)" if p.returncode == 0
                     else combined.strip())
        lines.append("")

    lines.append("=" * 78)
    lines.append("# summary: %d of %d optimization levels emit the rule" % (seen_rule, len(LEVELS)))
    if seen_rule == 0:
        lines.append("3429: PARSE-WARNING: the rule fired at NO optimization level -- either "
                     "the defect is gone or this script is not running the repro")
    if seen_rule == len(LEVELS):
        lines.append("3429: PARSE-WARNING: the rule fired at EVERY optimization level, "
                     "including -O0 -- the issue body's -Od workaround no longer holds")
    lines.append("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote " + OUT)


if __name__ == "__main__":
    main()
