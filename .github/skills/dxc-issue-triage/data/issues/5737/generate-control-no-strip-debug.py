"""Generate variant-no-strip-debug-main-debug.txt: same two-step lib+link
build as repro.hlsl/cmd.txt, with -Qstrip_debug removed from the link line.

This is a negative control for match.json: it proves the reported failure
(`DXIL container does not contain the given part`) is specific to combining
-Fd with -Qstrip_debug at link time, not to linking a stripped-reflection
lib_6_3 library in general. Run from the issue directory.

Not run through `triage.py run --shader`, because that swaps only the HLSL
source operand and this control instead removes one flag from the SECOND
line of a two-invocation cmd.txt while keeping the first line and the
shader identical -- a variation `--shader`/`--args` cannot express (SKILL.md,
step 5: "Use labelled --args captures for single arms or a command-echoing
matrix harness when the whole chain needs different arguments"). Kept as a
committed, re-runnable generator per SKILL.md step 11's rule that every
manual-case/variant capture must be produced by a script that echoes the
command it runs, rather than transcribed by hand.
"""
import os
import subprocess
import sys

# dxc.exe is found from $DXC, else <repo>/build/Debug/bin/dxc.exe, derived
# from this script's own path -- never hardcoded, so the generator still
# works from a differently-rooted checkout (SKILL.md's path-hygiene rule).
_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", ".."))
EXE = os.environ.get(
    "DXC", os.path.join(_REPO_ROOT, "build", "Debug", "bin", "dxc.exe"))
CMDS = [
    ["-T", "lib_6_3", "-Zi", "-Qstrip_reflect", "-Qembed_debug",
     "-Fd", "testc.pdb", "-Fo", "test.lib", "repro.hlsl"],
    # -Qstrip_debug removed here; everything else is identical to cmd.txt.
    ["-link", "-T", "lib_6_3", "-Zi", "-Qstrip_reflect",
     "-Fd", "test.pdb", "-Fo", "test.bin", "test.lib"],
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
    "# variant: no-strip-debug (control-cmd, -Qstrip_debug removed from link line)\n"
    "# expect: no-match\n"
)

with open("variant-no-strip-debug-main-debug.txt", "w", encoding="utf-8") as f:
    f.write(header + "\n" + text)

print(f"verdict={verdict} expect=no-match "
      f"{'OK' if verdict == 'no-repro' else 'WARNING: control expected no-match but scored repro'}")
sys.exit(0)
