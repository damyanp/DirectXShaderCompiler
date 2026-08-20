"""Capture the assert stack for #5357's primary repro via cdb.

Run from the issue directory: python capture-stack.py
Prints and writes manual-case-assert-stack.txt. The command line and the assert's `File:`
line are made machine-independent -- anchored on the repo name and a repo-relative dxc.exe
path -- rather than baking in one machine's absolute layout (see #3377/#3883's trim-cdb.py
for the same convention). The address/module-load columns of the raw transcript are dropped;
a full stack dump is noise, only the named frames matter.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ANCHOR = "DirectXShaderCompiler"
THIS_FILE = Path(__file__).resolve()
# .../<repo>/.github/skills/dxc-issue-triage/data/issues/5357/capture-stack.py
REPO_ROOT = THIS_FILE.parents[6]
DXC = REPO_ROOT / "build" / "Debug" / "bin" / "dxc.exe"
CDB = r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"

FRAME = re.compile(r"^[0-9a-f]{2}\s+[0-9a-f`]+\s+[0-9a-f`]+\s+(?P<frame>\S.*)$")


def redact(line: str) -> str:
    """Anchor an absolute path at the repo name rather than one machine's layout."""
    idx = line.find(REPO_ANCHOR)
    if idx == -1:
        return line
    return "<repo>" + line[idx + len(REPO_ANCHOR) :]


if __name__ == "__main__":
    argv = [CDB, "-c", "g;kn 40;q", str(DXC), "-T", "lib_6_8", "repro.hlsl"]
    cmd_line = "$ " + subprocess.list2cmdline(
        [redact(CDB), "-c", "g;kn 40;q", redact(str(DXC)), "-T", "lib_6_8", "repro.hlsl"]
    )
    result = subprocess.run(argv, capture_output=True, text=True)
    text = result.stdout + result.stderr
    keep = [cmd_line]
    started = False
    prev_was_file = False
    for line in text.splitlines():
        if "Error: assert(" in line:
            started = True
        if not started:
            continue
        if prev_was_file:
            keep.append(redact(line))
            prev_was_file = False
            continue
        m = FRAME.match(line)
        if m:
            keep.append("    " + m.group("frame"))
            continue
        if line.startswith(("Error:", "File:", "Func:")) or "Unknown exception" in line:
            keep.append(line)
            prev_was_file = line.startswith("File:")
        if "RtlUserThreadStart" in line:
            break
    out = "\n".join(keep) + "\n"
    with open("manual-case-assert-stack.txt", "w") as f:
        f.write(out)
    print(out)
