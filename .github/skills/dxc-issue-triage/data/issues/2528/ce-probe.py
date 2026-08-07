"""Probe Compiler Explorer directly for #2528, without publishing a link.

`triage.py godbolt` publishes and records a URL, and prints only the first line of
each pane -- which SKILL.md warns is often a stray warning rather than the finding.
This script reuses triage.py's own `ce_compile` (so the request, the language and
the output filters are identical to what the published link will use) and prints
each pane in full, so a Clang pane can be judged, and CONTROLLED, before it is
adopted or rejected.

It touches no database and writes nothing; run it from the skill directory:

    python data\\issues\\2528\\ce-probe.py > data\\issues\\2528\\manual-case-ce-clang.txt
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import triage  # noqa: E402

REPRO = open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8").read()
UNTOUCHED = open(os.path.join(HERE, "control-untouched.hlsl"),
                 encoding="utf-8").read()

# The control SKILL.md demands before believing any cross-compiler difference:
# something trivially valid, compiled with the same flags. If Clang fails on this
# too, a Clang failure on the repro says nothing about #2528.
TRIVIAL = """\
// Trivial control: a vertex shader that is unambiguously valid and involves no
// inout signature element at all.
float4 main(float4 p : POSITION) : SV_Position {
  return p;
}
"""

CASES = [
    ("hlsl_clang_trunk", "-T vs_6_0 -E main", "repro", REPRO),
    ("hlsl_clang_trunk", "-T vs_6_0 -E main", "trivial-control", TRIVIAL),
    ("hlsl_clang_trunk", "-T vs_6_0 -E main -fsyntax-only", "repro +fsyntax-only",
     REPRO),
    ("hlsl_clang_trunk", "-T vs_6_0 -E main -fsyntax-only",
     "trivial-control +fsyntax-only", TRIVIAL),
    ("hlsl_clang_trunk", "-T vs_6_0 -E main", "control-untouched", UNTOUCHED),
]

for cid, args, label, source in CASES:
    rc, text, crashed = triage.ce_compile(source, cid, args)
    print(f"$ {cid} {args}   [{label}]")
    print(f"[exit] {rc}{'  CRASH' if crashed else ''}")
    print("--- output ---")
    print(text)
    print()
