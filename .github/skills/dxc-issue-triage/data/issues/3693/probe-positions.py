"""Compile every case in case-positions.hlsl and record the result.

Writes manual-case-position-matrix.txt: one block per case with the exact command, the
exit status, every diagnostic line, and whether DXIL was emitted. The compiler path comes
from the environment (DXC) or defaults to the repo's Debug build, so this is runnable from
a fresh clone rather than pinned to one machine.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DXC = os.path.normpath(
    os.path.join(HERE, "..", "..", "..", "..", "..", "..", "build", "Debug", "bin", "dxc.exe"))
DXC = os.environ.get("DXC", DEFAULT_DXC)

DESCR = {
    1: "uint x = indices[3];                       plain local initializer",
    2: "g_vertices[indices[3]].x                   index of a resource operator[]  (reporter's shape)",
    3: "float3 n[3] = { ..., g_vertices[indices[3]] };  same, inside an initializer list",
    4: "take(indices[3])                           ordinary function call argument",
    5: "m[3] = 7;                                  assignment left-hand side",
    6: "indices[3] + 1                             arithmetic subexpression",
    7: "indices.w                                  swizzle spelling of the same access",
    8: "g_vertices[a[3]].x                         ARRAY index of a resource operator[]",
    9: "uint x = a[3];                             ARRAY, plain local initializer",
    10: "arr[indices[3]]                            index of a plain array subscript",
    11: "indices[indices[3]]                        index of a vector subscript",
}

HEADER = """# Where does DXC's existing out-of-bounds subscript check fire?
#
# Each case in case-positions.hlsl is compiled on its own with -D CASE=n against the
# ground-truth Debug build. Recorded per case: the exact command, the exit status, every
# error:/warning: line, and whether DXIL was emitted ("; shader hash:" present in stdout).
#
# Run by: python probe-positions.py   (writes this file)
"""


def main():
    ver = subprocess.run([DXC, "--version"], capture_output=True, text=True)
    out = [HEADER, "# dxc: %s" % DXC,
           "# version: %s" % ver.stdout.strip().splitlines()[0], ""]
    for case in sorted(DESCR):
        args = ["-T", "cs_6_0", "-E", "main", "-Od", "-D", "CASE=%d" % case,
                "case-positions.hlsl"]
        p = subprocess.run([DXC] + args, capture_output=True, text=True, cwd=HERE)
        text = p.stdout + p.stderr
        diags = [ln.rstrip() for ln in text.splitlines()
                 if "error:" in ln or "warning:" in ln]
        out.append("=" * 78)
        out.append("CASE %d  %s" % (case, DESCR[case]))
        out.append("# cmd: dxc %s" % " ".join(args))
        out.append("# exit: 0x%08X" % (p.returncode & 0xFFFFFFFF))
        out.append("# dxil emitted: %s" % ("yes" if "; shader hash:" in text else "no"))
        if diags:
            out.extend(diags)
        else:
            out.append("<no error: or warning: line in stdout+stderr>")
        out.append("")
    path = os.path.join(HERE, "manual-case-position-matrix.txt")
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(out))
    print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
