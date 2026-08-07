"""Probe Compiler Explorer for #3092 and print a capture-style record.

Used for the Clang panes and their controls, which `triage.py run` cannot
reach -- it only drives locally installed compilers. Re-runnable:

    python ce-probe.py <source.hlsl> <ce-compiler-id> [args...]

Run from this directory. `dxc_trunk` and `hlsl_clang_trunk` are rolling
builds, so re-running may not reproduce an exact message; the class of
failure is what the evidence rests on.
"""
import os
import sys
import datetime

sys.path.insert(0, os.path.join("..", "..", "..", "scripts"))
import triage  # noqa: E402

src_name, compiler = sys.argv[1], sys.argv[2]
args = " ".join(sys.argv[3:]) or "-T cs_6_0 -E main -spirv"
source = open(src_name, encoding="utf-8").read()
rc, text, crashed = triage.ce_compile(source, compiler, args)

print(f"# compiler-explorer: {compiler}")
print(f"# source: {src_name}")
print(f"# args: {args}")
print(f"# ran: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
print(f"# exit: {rc}")
print(f"# internal-failure: {int(crashed)}")
print()
print(text)
print()
