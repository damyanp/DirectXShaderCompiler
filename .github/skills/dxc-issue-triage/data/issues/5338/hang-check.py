"""Confirm v1.4.1907's timeout in bisect (60s) is a genuine hang, not a
marginal timeout, by re-running with 4x the default wall clock.

Usage (from this directory):
    python hang-check.py <path-to-v1.4.1907-dxc.exe> [timeout_seconds] [out_file]

Writes the exact command run (subprocess.list2cmdline) and whether the
process returned within the timeout directly to out_file (default:
manual-case-v1.4.1907-hang-check.txt), so the result survives regardless of
shell buffering/redirection behaviour.
"""
import os
import subprocess
import sys
import time

# Reuse the tool's own machine-independent path tokenisation (display_exe)
# instead of hand-redacting the capture afterwards.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                 "scripts"))
from triage import display_exe  # noqa: E402


def main():
    exe = sys.argv[1]
    timeout_s = float(sys.argv[2]) if len(sys.argv) > 2 else 240.0
    out_path = sys.argv[3] if len(sys.argv) > 3 \
        else "manual-case-v1.4.1907-hang-check.txt"
    argv = [exe, "-T", "vs_6_0", "repro.hlsl"]
    display_argv = [display_exe(exe)] + argv[1:]
    lines = []
    lines.append("# manual capture: confirm v1.4.1907's bisect timeout (60s "
                  "default) is a genuine hang, not a slow-start artefact")
    lines.append("# harness:  hang-check.py -- re-runnable")
    lines.append("$ " + subprocess.list2cmdline(display_argv))
    lines.append(f"# timeout: {timeout_s}s (tool default is 60s; this is "
                  f"{timeout_s / 60:.0f}x that)")
    start = time.time()
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=timeout_s,
                               text=True)
        elapsed = time.time() - start
        lines.append(f"# returned after {elapsed:.1f}s, exit={proc.returncode}")
        lines.append("--- stdout ---")
        lines.append(proc.stdout)
        lines.append("--- stderr ---")
        lines.append(proc.stderr)
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        lines.append(f"# TIMED OUT after {elapsed:.1f}s -- process killed, "
                      f"no output produced")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
