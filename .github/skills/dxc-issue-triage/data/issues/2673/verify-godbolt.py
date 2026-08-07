"""Verify the published Compiler Explorer link really shows #2673's symptom.

Recompiles the exact source and arguments `triage.py godbolt` published, on the
same two CE compilers, and prints the two metadata nodes the godbolt-note
banner tells a reader to look at. Kept next to the evidence so the verification
is re-runnable rather than a claim about a page somebody once opened.
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
import triage  # noqa: E402

ISSUE = 2673
d = os.path.dirname(os.path.abspath(__file__))
source = triage.annotate(ISSUE, open(os.path.join(d, "repro.hlsl"), encoding="utf-8").read())
args, _ = triage.ce_args(ISSUE)

for compiler in ("dxc_1_6_2112", "dxc_trunk"):
    rc, text, crashed = triage.ce_compile(source, compiler, args)
    defines = re.search(r"^!dx\.source\.defines = !\{!(\d+)\}", text, re.M)
    node = None
    if defines:
        node = re.search(r"^!%s = (.*)$" % defines.group(1), text, re.M)
    argsnode = re.search(r'^!\d+ = !\{!"-E".*$', text, re.M)
    print(f"== {compiler}  exit={rc} crashed={crashed}")
    print(f"   args:            {args}")
    print(f"   defines node:    {node.group(1) if node else '(not found)'}")
    print(f"   dx.source.args:  {argsnode.group(0) if argsnode else '(not found)'}")
    print(f"   match.json says: {triage.classify(ISSUE, text, rc, False)}")
