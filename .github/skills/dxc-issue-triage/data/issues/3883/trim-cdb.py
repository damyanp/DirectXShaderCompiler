"""Trim the raw cdb transcript from assert-stack.cmd down to what is worth committing, #3883.

Keeps the case markers, the assert text (Error/File/Func plus the value of `File:`, which dxc
prints on the FOLLOWING line), exception notices, dxc's own diagnostics, and the *named* stack
frames -- dropping the address columns, loader chatter, NatVis noise and module loads, as
SKILL.md asks ("a full stack dump is noise").

Usage:  python trim-cdb.py <raw.txt> [dxc.exe]   # prints the trimmed transcript
"""

import re
import subprocess
import sys

HEADER = """\
# Trimmed cdb transcript for #3883, produced by:
#     cmd /c .\\assert-stack.cmd > raw-cdb.txt 2>&1
#     python trim-cdb.py raw-cdb.txt > manual-case-assert-stack.txt
# Both scripts are committed beside this file; raw-cdb.txt is not (it is noise and is
# re-derivable). The `### $ cdb ...` lines are echoed by the harness, so they are the
# commands that actually ran rather than a transcription of them. Re-running the pipeline
# reproduces this file exactly apart from the per-run (pid.tid) prefixes.
#
# Compiler: main-debug, <repo>/build/Debug/bin/dxc.exe
#           {version}
#           (upstream-equivalent commit 13730886e; the self-reported ab5400907 is fork-local)
"""

DEFAULT_DXC = "..\\..\\..\\..\\..\\..\\build\\Debug\\bin\\dxc.exe"
# `kb` lines look like:  <retaddr> : <4 args> : dxcompiler!Some::Frame+0x51
FRAME = re.compile(r"^[0-9a-f`]{8,}\s+:\s+(?:[0-9a-f`]+\s+){2,}:\s+(?P<frame>\S.*)$")

KEEP = re.compile(
    r"^(###|Error:\s|File:|Func:|Last event:|"
    r"\([0-9a-f]+\.[0-9a-f]+\): |"            # (pid.tid): exception notice
    r".*\bwarning: |.*\berror: |"             # dxc's own diagnostics
    r"\s+(uint|~+\s|\s*\^))"                  # the caret/source lines under a diagnostic
)
DROP = re.compile(
    r"^(ModLoad:|NatVis|\s*$|0:000> cdb: Reading|ntdll!LdrpDoDebuggerBreak|"
    r"\*\*\* WARNING: Unable to verify checksum|RetAddr\b|quit:|"
    r"Microsoft \(R\) Windows Debugger|Copyright \(c\)|CommandLine:|"
    r"Symbol search path|Executable search path|"
    r"[0-9a-f]{8}`[0-9a-f]{8} cc\b)"
)


def version_line(dxc: str) -> str:
    """dxc --version, as one line, so the header names the exact binary that was traced."""
    out = subprocess.run([dxc, "--version"], capture_output=True, text=True).stdout
    return " - ".join(p.strip() for p in out.split("\n") if p.strip())


def main() -> int:
    dxc = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DXC
    print(HEADER.format(version=version_line(dxc)))
    prev_was_file = False
    with open(sys.argv[1], "r", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if DROP.match(line):
                prev_was_file = False
                continue
            if prev_was_file:
                # Make the assert's source file machine-independent: anchor on the repo
                # name rather than on one machine's absolute layout.
                print(re.sub(r"^.*?DirectXShaderCompiler\\", "<repo>\\\\", line))
                prev_was_file = False
                continue
            m = FRAME.match(line)
            if m:
                print("    " + m.group("frame"))
                continue
            if KEEP.match(line):
                print(line)
                prev_was_file = line.startswith("File:")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
