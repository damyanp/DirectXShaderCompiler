"""Generates manual-case-gh-continue.txt for DXC issue #6073.

Runs main-debug's dxc.exe under cdb, using `gh` ("go handled") to continue past
the Debug-only assert in clang::LinkageComputer::getLVForDecl -- this emulates
what an NDEBUG (Release) build does, since assert() is a no-op there and
execution simply continues. This shows whether the compiler, past that assert,
reaches the exact "Declaration may not be in a Comdat!" text quoted in the
issue. Run from the issue directory:  python measure-gh-continue.py

Machine paths are resolved from this script's own location (same convention as
triage.py's REPO_ROOT) rather than hardcoded, and the repo-root prefix is
replaced with the portable "<repo>" marker in the committed transcript --
never in the live cdb invocation, since cdb needs a real path to run.
"""
import os
import subprocess

ISSUE_DIR = os.path.dirname(os.path.abspath(__file__))
# data/issues/6073 -> issues -> data -> dxc-issue-triage -> skills -> .github -> repo root
REPO_ROOT = os.path.abspath(os.path.join(ISSUE_DIR, *([os.pardir] * 6)))
DXC = os.path.join(REPO_ROOT, "build", "Debug", "bin", "dxc.exe")
CDB = r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"

# sxe -c "gh" e0000001 : on the Debug-only assert exception (e0000001), just
#   "go handled" -- continue as if the assert had not fired, matching NDEBUG.
# sxe -c "gh" e06d7363 : on the C++ exception (e06d7363) DXC's fatal-error
#   handler throws, also continue -- this is what happens on every normal run
#   (no debugger attached), it is not an NDEBUG-specific behaviour.
argv = [CDB, "-c", 'sxe -c "gh" e0000001; sxe -c "gh" e06d7363; g; q',
        DXC, "-T", "cs_6_0", "-E", "main", "repro.hlsl"]


def redact(text):
    return text.replace(REPO_ROOT, "<repo>")


def main():
    cmdline = subprocess.list2cmdline(argv)
    print("$", redact(cmdline))
    proc = subprocess.run(argv, capture_output=True, text=True)
    print("[cdb exit]", proc.returncode)
    print(redact(proc.stdout))
    if proc.stderr:
        print("--- stderr ---")
        print(redact(proc.stderr))


if __name__ == "__main__":
    main()
