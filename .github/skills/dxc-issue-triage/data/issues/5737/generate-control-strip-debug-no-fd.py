"""Generate variant-strip-debug-no-fd-main-debug.txt: the same two-step
lib+link build as repro.hlsl/cmd.txt, but with -Fd removed from the link
line entirely (only -Qstrip_debug remains).

This isolates which flag on the link line is load-bearing for the reported
failure. The issue's title and body describe the defect as combining -Fd
WITH -Qstrip_debug; this control asks whether -Qstrip_debug alone (with no
-Fd at all) is sufficient. Run from the issue directory. See
generate-control-no-strip-debug.py's docstring for why this cannot be
expressed with `triage.py run --shader`/`--args`: it changes flags on the
second line of a two-invocation chain while keeping the first line and
shader identical, and the second line's own input file depends on the first
line having already run.
"""
import os
import subprocess
import sys

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", ".."))
EXE = os.environ.get(
    "DXC", os.path.join(_REPO_ROOT, "build", "Debug", "bin", "dxc.exe"))
CMDS = [
    ["-T", "lib_6_3", "-Zi", "-Qstrip_reflect", "-Qembed_debug",
     "-Fd", "testc.pdb", "-Fo", "test.lib", "repro.hlsl"],
    # -Fd removed here; -Qstrip_debug (and everything else) kept, unlike
    # generate-control-no-strip-debug.py which keeps -Fd and drops
    # -Qstrip_debug instead.
    ["-link", "-T", "lib_6_3", "-Zi", "-Qstrip_reflect", "-Qstrip_debug",
     "-Fo", "test.bin", "test.lib"],
]

parts = []
worst_rc = 0
for argv in CMDS:
    full = [EXE] + argv
    printed_cmd = subprocess.list2cmdline(["dxc"] + argv)
    proc = subprocess.run(full, capture_output=True, text=True)
    worst_rc = proc.returncode if proc.returncode else worst_rc
    parts.append(
        f"$ {printed_cmd}\n[exe] <repo>/build/Debug/bin/dxc.exe\n"
        f"[exit] {proc.returncode}\n--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}\n"
    )

text = "\n".join(parts)
positive = "DXIL container does not contain the given part" in text
verdict = "repro" if positive else "no-repro"

header = (
    "# compiler: main-debug\n"
    "# exe: <repo>/build/Debug/bin/dxc.exe\n"
    "# cmd: " + " ; ".join(subprocess.list2cmdline(a) for a in CMDS) + "\n"
    f"# exit: {worst_rc}\n# timed_out: 0\n# match: match.json\n"
    f"# verdict: {verdict}\n"
    "# variant: strip-debug-no-fd (control-cmd, -Fd removed from link line, "
    "-Qstrip_debug kept)\n"
    "# expect: match\n"
)

with open("variant-strip-debug-no-fd-main-debug.txt", "w", encoding="utf-8") as f:
    f.write(header + "\n" + text)

print(f"verdict={verdict} expect=match "
      f"{'OK' if verdict == 'repro' else 'WARNING: control expected match but scored no-repro'}")
sys.exit(0)
