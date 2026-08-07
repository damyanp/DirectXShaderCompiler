"""microsoft/DirectXShaderCompiler#2188 -- full Compiler Explorer output, captured.

`triage.py godbolt` prints only the first line per compiler, which is not enough to judge
a Clang pane: SKILL.md requires a *control* before believing any cross-compiler
difference, and "exit=0" alone does not show whether Clang honoured `-E`/`-T` or quietly
ignored them. This dumps the full text for every compiler in the link, for both the repro
and the reporter's inlined-constant control, so the comparison is on disk rather than in a
console scrollback.

It reuses triage.py's own `ce_compile`/`annotate`, so the captured output is produced by
exactly the request the published link is built from (same filters, same banner).

    python run-ce.py            # from data/issues/2188/, writes manual-case-ce.txt
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRIAGE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts",
                                       "triage.py"))
spec = importlib.util.spec_from_file_location("triage", TRIAGE)
triage = importlib.util.module_from_spec(spec)
sys.modules["triage"] = triage
spec.loader.exec_module(triage)

ISSUE = 2188
DXC_ARGS = "-T cs_6_0 -E csMain"
FXC_ARGS = "/T cs_5_0 /E csMain"
COMPILERS = [("fxc_10_0_19041", FXC_ARGS),
             ("dxc_1_6_2112", DXC_ARGS),
             ("dxc_trunk", DXC_ARGS),
             ("hlsl_clang_trunk", DXC_ARGS)]
SOURCES = [("repro.hlsl", "the reported shader"),
           ("control-inlined.hlsl",
            "CONTROL: reporter's inlined-constant version. Every compiler must "
            "accept this, or a failure on repro.hlsl is not evidence about this "
            "issue -- it is evidence about the shader or the pane.")]

# Diagnostics come first in ce_compile's text, the disassembly after, so a tail cap keeps
# every message while stopping a clean Clang pane from burying the file in DWARF metadata.
MAX_LINES = 45

out = ["# what: full Compiler Explorer output behind this issue's link",
       "# how:  python run-ce.py (reuses triage.py's ce_compile and annotate)",
       "# note: NOT a probe -- CE runs Release Linux builds and dxc_trunk is a",
       "#       rolling build, so this corroborates the local run, never overrules it.",
       ""]

for name, why in SOURCES:
    src = triage.annotate(ISSUE, open(os.path.join(HERE, name),
                                      encoding="utf-8").read())
    out.append("=" * 78)
    out.append(f"==== {name} -- {why}")
    out.append("=" * 78)
    for cid, args in COMPILERS:
        rc, text, crashed = triage.ce_compile(src, cid, args)
        out.append(f"\n---- {cid}   args: {args}")
        out.append(f"     exit={rc}  internal_failure={crashed}")
        lines = text.splitlines()
        for line in lines[:MAX_LINES]:
            out.append("     " + line)
        if len(lines) > MAX_LINES:
            out.append(f"     ... [{len(lines) - MAX_LINES} further lines of "
                       f"disassembly trimmed; re-run run-ce.py for all of it]")
    out.append("")

open(os.path.join(HERE, "manual-case-ce.txt"), "w", encoding="utf-8").write(
    "\n".join(out) + "\n")
print("\n".join(out))
