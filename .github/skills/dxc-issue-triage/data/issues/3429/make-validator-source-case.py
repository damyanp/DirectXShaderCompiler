"""Generates manual-case-validator-source.txt for issue 3429.

Question it answers: is the DXIL that DXC's own front end + optimizer produce for repro.hlsl
actually rejected by the validator built from this repo's source, and does the rejected
value look like what lib/DxilValidation/DxilValidation.cpp refuses?

Every command is echoed with subprocess.list2cmdline(), so the transcript is what ran rather
than what someone typed.

Usage (from this directory):
    python make-validator-source-case.py [path-to-Debug-bin]
"""

import os
import subprocess
import sys

BIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "..",
    "build", "Debug", "bin")
BIN = os.path.abspath(BIN)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "manual-case-validator-source.txt")

CASES = [
    ("emit DXIL with validation disabled, so the optimizer's output survives",
     [os.path.join(BIN, "dxc.exe"), "-E", "main", "-T", "cs_6_0", "-Vd",
      "-Fc", "artifact-main-debug-Vd.ll", "-Fo", "artifact-main-debug-Vd.dxil",
      "repro.hlsl"]),
    ("validate that same DXIL with dxv.exe, which is built from this repo's source",
     [os.path.join(BIN, "dxv.exe"), "artifact-main-debug-Vd.dxil"]),
]


def main():
    lines = []
    lines.append("# issue: 3429")
    lines.append("# what: does the module DXC emits for repro.hlsl fail the validator built")
    lines.append("#       from this repo's own source, and is the rejected value a phi?")
    lines.append("# generator: make-validator-source-case.py (commit this next to its output)")
    lines.append("# bin: " + BIN)
    lines.append("")

    for why, argv in CASES:
        lines.append("=" * 78)
        lines.append("# " + why)
        lines.append("$ " + subprocess.list2cmdline(argv))
        p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
        lines.append("[exit] %d (0x%08X)" % (p.returncode, p.returncode & 0xFFFFFFFF))
        lines.append("--- stdout ---")
        lines.append(p.stdout.rstrip("\n"))
        lines.append("--- stderr ---")
        lines.append(p.stderr.rstrip("\n"))
        lines.append("")

    # Self-consistency: say loudly if the grep found nothing, so "nothing here" and
    # "nothing matched" cannot arrive through the same channel.
    ll_path = os.path.join(HERE, "artifact-main-debug-Vd.ll")
    lines.append("=" * 78)
    lines.append("# every TGSM-pointer-typed phi in the emitted DXIL")
    lines.append("$ grep -n 'phi .*addrspace(3)\\*' artifact-main-debug-Vd.ll")
    hits = []
    if os.path.exists(ll_path):
        with open(ll_path, encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f, 1):
                if "phi " in line and "addrspace(3)*" in line:
                    hits.append("%d: %s" % (n, line.rstrip()))
    else:
        lines.append("3429: PARSE-WARNING: %s does not exist" % ll_path)
    if hits:
        lines.extend(hits)
    else:
        lines.append("3429: PARSE-WARNING: 0 TGSM-pointer phis found -- "
                     "either the compile failed or the IR shape changed")
    lines.append("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote " + OUT)


if __name__ == "__main__":
    main()
