"""Measure the FORM of the failure for issue #3377 across repeated runs.

The defect is an out-of-bounds ``std::vector`` index at
``lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:4792``, guarded only by a ``DXASSERT``
that ``NDEBUG`` compiles out of release builds (``include/dxc/Support/Global.h:356``). What the
process does after the bad index therefore depends on whatever heap bytes happen to follow the
vector, so the *exit status* and the *message* both vary -- across releases and, on some
builds, between runs of the same binary.

That variability is the reason ``match.json`` is exit-status based (``internal_failure``) and
not text based: 8 of the 20 release binaries fail with completely empty stderr, so a predicate
matching "Internal compiler error" or an assert message would score them clean and invent a fix
boundary. This script makes that claim countable instead of asserted.

Usage (run from this directory)::

    python crash-form.py                       # ground-truth Debug build, 10 runs
    python crash-form.py <dxc.exe> [runs]

It only ever runs the repro; it changes nothing.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", ".."))
DEFAULT_DXC = os.path.join(REPO, "build", "Debug", "bin", "dxc.exe")
ARGS = ["-T", "ps_6_0", "-E", "main_fragment", "repro.hlsl"]


def main() -> int:
    dxc = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DXC
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print("### dxc:  %s" % dxc)
    print("### args: %s" % " ".join(ARGS))
    print("### runs: %d" % runs)
    tally = {}
    for i in range(1, runs + 1):
        p = subprocess.run([dxc] + ARGS, cwd=HERE, capture_output=True, text=True)
        status = p.returncode & 0xFFFFFFFF
        err = (p.stderr or "").strip().splitlines()
        first = err[0] if err else "<no output>"
        print("run %2d: exit=0x%08X  stderr=%s" % (i, status, first))
        tally[(status, first)] = tally.get((status, first), 0) + 1

    print("### tally")
    for (status, first), n in sorted(tally.items()):
        print("  %2d/%d  exit=0x%08X  %s" % (n, runs, status, first))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
