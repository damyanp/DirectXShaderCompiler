"""Reproduce the assert stack for #4958 (committed alongside its output; re-run to re-derive).

Passes the argv list directly to subprocess.run rather than through another shell, per
SKILL.md's cdb guidance. The compiler path is resolved relative to the repository root rather
than hardcoded, and the captured text is passed through triage.py's own `redact_paths` before
being written, so the committed file spells this machine's checkout the same way every other
captured evidence file in this tree does (`<repo>/...`) instead of leaking an absolute path.
"""
import os
import subprocess
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))
from triage import REPO_ROOT, redact_paths  # noqa: E402

CDB = r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"
DXC = os.path.join(REPO_ROOT, "build", "Debug", "bin", "dxc.exe")

argv = [
    CDB,
    "-c", 'sxe -c "kb 12; gh" e0000001; g; q',
    DXC,
    "-T", "hs_6_6", "-E", "mainHS", "-Fo", "output.dxil", "repro.hlsl",
]

cmdline = redact_paths(subprocess.list2cmdline(argv))
r = subprocess.run(argv, capture_output=True, text=True, timeout=180)

out_path = os.path.join(os.path.dirname(__file__), "manual-case-assert-stack-full.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("$ " + cmdline + "\n")
    f.write("[exit] " + str(r.returncode) + "\n\n")
    f.write(redact_paths(r.stdout))
    f.write(redact_paths(r.stderr))

print("EXIT", r.returncode)
