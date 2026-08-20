"""Regenerate manual-case-assert-stack.txt: capture the assert stack for issue #6005
via cdb's `gh` (go-handled) trick, which emulates NDEBUG so the Debug build's assert
throws exactly as a Release build's unchecked code path would run past it.

Every command is echoed with subprocess.list2cmdline before it runs, so the transcript
is what actually executed rather than a transcription of it (SKILL.md: "Generate every
manual-case-*.txt from a small script that echoes the command it is about to run").

Run from this directory: python gen-assert-stack.py
"""
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]  # 6005 -> issues -> data -> dxc-issue-triage -> skills -> .github -> <repo>
CDB = os.environ.get(
    "CDB_EXE", r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"
)
DXC = Path(os.environ.get("DXC_EXE", REPO / "build" / "Debug" / "bin" / "dxc.exe"))

DXC_ARGS = [
    "-spirv", "-HV", "202x", "-T", "cs_6_7", "-Zpr", "-enable-16bit-types",
    "-fvk-use-scalar-layout", "-Wno-c++11-extensions", "-Wno-c++1z-extensions",
    "-Wno-gnu-static-float-init", "-fspv-target-env=vulkan1.3",
    "-fspv-debug=source", "-fspv-debug=tool", "repro.hlsl",
]

argv = [CDB, "-c", 'sxe -c "kb 10; gh" e0000001; g; q', str(DXC)] + DXC_ARGS


def redact(text: str) -> str:
    """Replace this machine's layout with the workspace's <repo> convention."""
    for sep in ("\\\\", "\\", "/"):
        spelling = str(REPO).replace("\\", sep)
        text = text.replace(spelling, "<repo>")
        text = text.replace(spelling.lower(), "<repo>")
    return text


if __name__ == "__main__":
    cmd_line = redact(subprocess.list2cmdline(argv))
    print("$", cmd_line)
    result = subprocess.run(argv, capture_output=True, text=True, cwd=HERE)
    with open(HERE / "manual-case-assert-stack-full.txt", "w") as f:
        f.write("$ " + cmd_line + "\n")
        f.write(redact(result.stdout))
        f.write(redact(result.stderr))
    print("subprocess exit:", result.returncode)
    print("wrote manual-case-assert-stack-full.txt; trim by hand into "
          "manual-case-assert-stack.txt (header, assert, and a few stack frames only)")
