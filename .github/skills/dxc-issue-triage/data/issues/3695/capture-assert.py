"""Capture the assert stack for #3695 and the NDEBUG-emulated continuation.

Every command is echoed with subprocess.list2cmdline(argv), i.e. exactly what
was executed -- a transcribed command line is an assertion nobody checks.

cdb is invoked through cmd.exe, not PowerShell: from PowerShell, `cdb -c "..."`
produces no output at all (SKILL.md), which reads as "the debugger found
nothing". Here it is launched directly by subprocess, which has the same
property of not re-quoting the arguments.

Writes manual-case-assert-stack.txt (cdb's banner and ModLoad noise trimmed
by `trim` below, so the file stays re-derivable rather than hand-edited).

Usage:  python capture-assert.py
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# .../<repo>/.github/skills/dxc-issue-triage/data/issues/3695 -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *[os.pardir] * 6))
CDB = shutil.which("cdb.exe") or os.path.join(
    os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    "Windows Kits", "10", "Debuggers", "x64", "cdb.exe")
DXC = os.environ.get(
    "DXC_TRIAGE_DXC",
    os.path.join(REPO, "build", "Debug", "bin", "dxc.exe"))
ARGS = ["-T", "cs_6_0", "-E", "main", "repro.hlsl"]

CASES = [
    ("assert stack (C++-exception form, exit 0xE0000001): break on the "
     "exception itself and dump frames",
     'sxe -c "kn 30; gh" e0000001; g; q'),
    ("NDEBUG emulation: `gh` continues PAST the assert, running the code a "
     "Release build (asserts compiled out) would have run",
     'sxe -c "gh" e0000001; g; .lastevent; kn 20; q'),
]


def trim(text):
    """Drop cdb's own noise, keeping the header, the assert and the frames.

    SKILL.md: commit the trimmed capture, a full stack dump is noise. Doing it
    here rather than by hand keeps the file re-derivable -- hand-editing a
    capture is falsification.
    """
    drop = (
        "ModLoad:", "Symbol search path", "Executable search path",
        "*** WARNING", "************", "   ---->", "      ---->",
        "   Extension", "   Use", "   Allow", "   NonInteractive",
        "   EnableRedirect", "   -- Configuring", ">>>>>>>>",
        "Microsoft (R) Windows Debugger", "Copyright (c)", "Response ",
        "Deferred ", "| ", "+---", "Path ", "NatVis script", "quit:",
        "First chance exceptions", "This exception may be expected",
        # cdb's own initial breakpoint, before dxc has run anything. Dropped
        # because a reader scanning for exception codes would otherwise see a
        # 0x80000003 here and take it for the assert, which arrives as
        # 0xE0000001 (a C++ exception) in this build.
        "ntdll!LdrpDoDebuggerBreak", "Break instruction exception",
    )
    keep = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if any(s.startswith(p) or ln.startswith(p) for p in drop):
            continue
        # Same reasoning, but the line is prefixed with cdb's "(pid.tid): ".
        if "Break instruction exception" in s:
            continue
        if s.endswith("int     3"):
            continue
        keep.append(ln.rstrip())
    return "\n".join(keep)


def main():
    out = []
    for title, ccmd in CASES:
        argv = [CDB, "-c", ccmd, DXC] + ARGS
        out.append("=" * 74)
        out.append(title)
        out.append("=" * 74)
        out.append("$ " + subprocess.list2cmdline(argv))
        out.append("")
        p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                           timeout=600)
        out.append(trim(p.stdout))
        if p.stderr.strip():
            out.append("--- cdb stderr ---")
            out.append(trim(p.stderr))
        out.append("[cdb exit] %d" % p.returncode)
        out.append("")

    path = os.path.join(HERE, "manual-case-assert-stack.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    sys.stdout.write("wrote %s\n" % path)


if __name__ == "__main__":
    main()
