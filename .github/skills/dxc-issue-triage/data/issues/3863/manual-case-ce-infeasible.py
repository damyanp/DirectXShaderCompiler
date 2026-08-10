"""Issue 3863: can Compiler Explorer demonstrate this at all?

Before recording a `--skip`, measure the claim instead of asserting it. This
issue is about an *include trace*, so a demonstration needs a real `#include`
and a header file next to it. A CE pane is single-source -- triage.py's own
ce_args() says "CE supplies the source itself" -- so there is nowhere to put
the header.

Three questions, asked of CE's dxc_trunk through the same API the triage tool
uses:

  1  no #include, normal compile with -H
     If `-H` printed a trace for the main file, a single-file pane could still
     show the working case. Expect nothing: `-H` traces *opened* files.
  2  #include "inc-pp-a.h", normal compile with -H
     Can a pane supply its own header? Expect a file-not-found error.
  3  #include, -P -Fi out.i -H
     The symptom itself, for the record.

If 1 shows no trace and 2 cannot resolve the header, then a pane can produce
neither the positive control nor the symptom, and an empty CE output pane would
be indistinguishable from "nothing ran" -- which is worse than no link.

Usage (from the workspace root):
    python data/issues/3863/manual-case-ce-infeasible.py > \
           data/issues/3863/manual-case-ce-infeasible.txt
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

PLAIN = """\
float4 main() : SV_Target {
  return 3.0;
}
"""

WITH_INCLUDE = """\
#include "inc-pp-a.h"

float4 main() : SV_Target {
  return ppmarker3863 + ppnested3863;
}
"""

CASES = [
    ("1  no #include, compile +-H", PLAIN, "-T ps_6_0 -E main -H"),
    ("2  #include, compile +-H", WITH_INCLUDE, "-T ps_6_0 -E main -H"),
    ("3  #include, -P -Fi out.i -H", WITH_INCLUDE,
     "-T ps_6_0 -E main -P -Fi out.i -H"),
]


def main():
    compiler = triage.CE_TRUNK
    print("compiler explorer: %s, compiler id %s" % (triage.CE, compiler))
    print("note: CE appends -Zi -Qembed_debug -Fc - to every DXC pane, so the")
    print("      arguments below are not the whole command line.")
    print()
    seen_trace = []
    for label, source, args in CASES:
        print("== %s" % label)
        print("   userArguments: %s" % args)
        rc, text, crashed = triage.ce_compile(source, compiler, args)
        traced = "Opening file [" in text
        seen_trace.append(traced)
        print("   exit=%s crashed=%s  contains 'Opening file ['=%s"
              % (rc, crashed, traced))
        body = text.strip()
        shown = [ln for ln in body.splitlines() if ln.strip()][:6]
        for ln in shown:
            print("   | %s" % ln[:110])
        if not shown:
            print("   | (no output)")
        print()

    print("conclusion inputs")
    print("  case 1 produced an include trace with no headers: %s" % seen_trace[0])
    print("  case 2 (pane tried to #include its own header) resolved it: %s"
          % seen_trace[1])
    print("  case 3 (-P with -H) produced a trace: %s" % seen_trace[2])


if __name__ == "__main__":
    main()
