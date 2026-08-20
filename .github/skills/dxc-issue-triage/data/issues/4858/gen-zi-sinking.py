r"""Generates manual-case-zi-sinking.txt: confirms the illegal code motion in #4858 survives
under the debug-info flags Compiler Explorer always appends to its DXC panes (-Zi -Qembed_debug
-Fc <file>), so the godbolt link below is expected to show the same defect rather than an
artifact of stripped debug info. Not scored by match.json/triage.py run: `-Zi` renames basic
blocks from numeric labels (`%9`) to source-derived ones (`if.then`), so match.json's
`label %(\d+)` anchor does not apply to this capture -- this script exists only to make the
CE corroboration reproducible from a committed command, not to feed `audit`/`reindex`.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(REPO, "build", "Debug", "bin")
DXC = os.path.join(BUILD_BIN, "dxc.exe")
ARGS = [DXC, "-T", "ps_6_0", "-E", "main", "-Zi", "-Qembed_debug", "-Fc", "zi-sinking-out.txt", "repro.hlsl"]


def redact(text):
    return text.replace(REPO, "<repo>").replace(REPO.replace("\\", "\\\\"), "<repo>")


if __name__ == "__main__":
    printed_cmd = subprocess.list2cmdline(ARGS).replace(DXC, "<repo>\\build\\Debug\\bin\\dxc.exe")
    print("$", printed_cmd)
    proc = subprocess.run(ARGS, capture_output=True, text=True)
    with open("manual-case-zi-sinking.txt", "w") as f:
        f.write("$ " + printed_cmd + "\n")
        f.write(f"# exit: {proc.returncode}\n\n")
        f.write(redact(proc.stdout))
        f.write(redact(proc.stderr))
        try:
            with open("zi-sinking-out.txt") as fc:
                f.write("\n--- -Fc file contents ---\n")
                f.write(redact(fc.read()))
        except FileNotFoundError:
            f.write("\n--- -Fc file was not produced ---\n")
    sys.exit(proc.returncode)
