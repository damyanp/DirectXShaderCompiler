"""Show FULL Compiler Explorer pane output for #2792, plus a Clang control.

`triage.py godbolt` records only the first line of each pane, which on
hlsl_clang_trunk is a `-Qembed_debug` unused-argument warning -- so the tool can
print nothing of the finding while the link is perfect (SKILL.md step 7). This
prints everything, and additionally compiles a trivial shader through Clang
with the same flags, because "a Clang error is not evidence until you have a
control".

Run from the skill root:

    python data/issues/2792/ce-panes.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import triage  # noqa: E402

REPRO = open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8").read()
TRIVIAL = "float main() : SV_Target { return 0; }\n"
FITS = open(os.path.join(HERE, "control-rootconst-fits.hlsl"),
            encoding="utf-8").read()
MISMATCH = open(os.path.join(HERE, "control-rs-register-mismatch.hlsl"),
                encoding="utf-8").read()
GARBAGE_RS = REPRO.replace(
    'RootFlags(0), RootConstants(b0, num32BitConstants = 1)',
    'RootFlags(0), NotARootSignatureClause(zzz')

CASES = [
    ("dxc_1_6_2112",    "-T ps_6_0 -E main", REPRO,   "repro"),
    ("dxc_trunk",       "-T ps_6_0 -E main", REPRO,   "repro"),
    ("dxc_trunk",       "-T ps_6_0 -E main", FITS,
     "control: num32BitConstants=2, i.e. correct"),
    ("hlsl_clang_trunk", "-T ps_6_0 -E main", REPRO,  "repro"),
    ("hlsl_clang_trunk", "-T ps_6_0 -E main", TRIVIAL,
     "CONTROL: one-line shader, same flags"),
    ("hlsl_clang_trunk", "-T ps_6_0 -E main -fsyntax-only", REPRO,
     "repro, front end only"),
    ("hlsl_clang_trunk", "-T ps_6_0 -E main -fsyntax-only", TRIVIAL,
     "CONTROL: one-line shader, front end only"),
    # A Clang NON-error is not evidence either. Before reading "clang does not
    # diagnose the overrun" as a finding, show clang says something about a
    # root signature at all.
    ("hlsl_clang_trunk", "-T ps_6_0 -E main -fsyntax-only", GARBAGE_RS,
     "CONTROL: syntactically broken root signature"),
    ("hlsl_clang_trunk", "-T ps_6_0 -E main -fsyntax-only", MISMATCH,
     "CONTROL: root sig binds b1, cbuffer is at b0 (dxc errors on this)"),
    ("dxc_trunk", "-T ps_6_0 -E main", GARBAGE_RS,
     "CONTROL: syntactically broken root signature"),
]

for compiler, args, src, what in CASES:
    rc, text, crashed = triage.ce_compile(src, compiler, args)
    print("=" * 78)
    print(f"{compiler}  {args}   [{what}]")
    print(f"exit={rc} crashed={crashed}")
    print("-" * 78)
    print(text.strip() or "(no output)")
    print()
