#!/usr/bin/env python3
"""issue #4792 -- multithreaded concurrent-invocation probe against dxcompiler.dll.

Runs bin/mt-harness.exe (built from mt-harness.cpp in this directory) against the
registered main-debug dxcompiler.dll at a fixed schedule of thread counts and
repeat attempts, and writes a full transcript -- including the exact argv
used for each attempt -- to manual-case-mt-harness.txt.

This is not a plain `dxc` invocation (the symptom only appears when many
threads call the *same loaded* compiler library concurrently), so it is
captured as a manual-case per SKILL.md rather than through `triage.py run`.
"""
import subprocess
import sys
import time
from pathlib import Path

ISSUE_DIR = Path(__file__).resolve().parent
HARNESS = ISSUE_DIR / "bin" / "mt-harness.exe"
REPO_ROOT = ISSUE_DIR.parents[5]
DXCOMPILER_DLL = REPO_ROOT / "build" / "Debug" / "bin" / "dxcompiler.dll"
REPRO = ISSUE_DIR / "repro.hlsl"

# (thread_count, attempts, timeout_ms)
SCHEDULE = [
    (8, 1, 15000),
    (16, 1, 15000),
    (32, 1, 15000),
    (64, 1, 20000),
    (96, 1, 20000),
    (128, 1, 20000),
    (256, 4, 45000),
    (512, 3, 60000),
]


def main():
    if not HARNESS.exists():
        print(f"ERROR: {HARNESS} not found; build mt-harness.cpp first", file=sys.stderr)
        return 1
    if not DXCOMPILER_DLL.exists():
        print(f"ERROR: {DXCOMPILER_DLL} not found", file=sys.stderr)
        return 1

    lines = []
    lines.append(f"# compiler: main-debug")
    lines.append(f"# dxcompiler.dll: <repo>/build/Debug/bin/dxcompiler.dll")
    lines.append(f"# harness: bin/mt-harness.exe (built from mt-harness.cpp, this directory)")
    lines.append(f"# ran: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    lines.append("")

    total_attempts = 0
    total_hangs = 0
    for threads, attempts, timeout_ms in SCHEDULE:
        for attempt in range(1, attempts + 1):
            argv = [
                str(HARNESS),
                str(DXCOMPILER_DLL),
                str(threads),
                str(timeout_ms),
                str(REPRO),
                "-T", "cs_6_0", "-E", "main",
            ]
            cmdline = subprocess.list2cmdline(argv)
            display_cmdline = cmdline.replace(str(REPO_ROOT), "<repo>").replace(
                str(REPO_ROOT).replace("\\", "\\\\"), "<repo>"
            )
            lines.append(f"$ {display_cmdline}")
            t0 = time.time()
            proc = subprocess.run(argv, cwd=str(ISSUE_DIR), capture_output=True, text=True)
            elapsed = time.time() - t0
            total_attempts += 1
            hang = proc.returncode == 124
            if hang:
                total_hangs += 1
            lines.append(f"[exit] {proc.returncode}  [wall {elapsed:.1f}s]  [threads={threads} attempt={attempt}/{attempts}]")
            lines.append("--- stdout ---")
            lines.append(proc.stdout.rstrip("\n"))
            if proc.stderr.strip():
                lines.append("--- stderr ---")
                lines.append(proc.stderr.rstrip("\n"))
            lines.append("")

    lines.append(f"# summary: {total_hangs}/{total_attempts} attempts hung (exit 124)")
    out = "\n".join(lines) + "\n"
    out_path = ISSUE_DIR / "manual-case-mt-harness.txt"
    out_path.write_text(out, encoding="utf-8")
    print(f"wrote {out_path} ({total_attempts} attempts, {total_hangs} hangs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
