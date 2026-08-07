"""Verify the published Compiler Explorer link for #2528 pane by pane.

`triage.py godbolt` prints only the FIRST line of each pane, which SKILL.md warns
is routinely a stray warning rather than the finding -- and on this issue the first
line of the DXC 1.6.2112 pane is a "DXIL.dll not found" warning. A link must be
verified before it is handed over, so this reproduces exactly what the link
contains: the SAME annotated source (repro.hlsl with godbolt-note.txt prepended)
and the SAME per-pane arguments recorded in godbolt.txt, printed in full.

Writes nothing and touches no database. Run from the skill directory:

    python data\\issues\\2528\\ce-verify.py > data\\issues\\2528\\manual-case-ce-panes.txt
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import triage  # noqa: E402

ISSUE = 2528
source = triage.annotate(
    ISSUE, open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8").read())
default_args, _ = triage.ce_args(ISSUE)
spec = open(os.path.join(HERE, "godbolt.txt"), encoding="utf-8").read().strip()

print(f"# link: {open(os.path.join(HERE, 'godbolt-url.txt')).read().strip()}")
print(f"# spec: {spec}")
print(f"# default CE args (from cmd.txt line 1): {default_args}")
print()

for entry in spec.split(","):
    cid, _, override = entry.strip().partition(":")
    args = override.strip() or default_args
    rc, text, crashed = triage.ce_compile(source, cid, args)
    print(f"$ {cid} {args}")
    print(f"[exit] {rc}{'  CRASH' if crashed else ''}")
    print("--- output ---")
    print(text)
    print()
