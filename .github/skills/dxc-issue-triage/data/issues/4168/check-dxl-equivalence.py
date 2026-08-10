#!/usr/bin/env python
"""#4168: is `dxc.exe -link` the same thing as `dxl.exe`?

The release history for this issue has to run the link step, and no stable
release archive ships `dxl.exe` (manual-case-release-tools.txt). The harness
therefore substitutes `dxc.exe -link` on releases. tools/clang/tools/dxl/dxl.cpp
says that is exactly what `dxl.exe` is -- a `main` that appends `-link` to argv
and calls `dxc::main` -- but SKILL.md is explicit that a command-line deviation
must be *measured* with an equivalence control rather than called inert.

This runs both spellings on the ground-truth build over the issue's own repro
and compares the produced containers byte for byte. It echoes every command it
runs (subprocess.list2cmdline, not a transcription) and carries a self-test: it
also hashes a container that is known to be DIFFERENT, so a hash comparison that
can only ever say "equal" is visible as broken rather than believed.
"""

import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
BIN = os.environ.get("DXC_LINK4168_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
WORK = os.path.join(HERE, "scratch-dxl-equiv")


def show(path):
    full = os.path.abspath(path)
    if full.lower().startswith(REPO.lower() + os.sep):
        return "<repo>" + full[len(REPO):].replace("\\", "/")
    return full


def run(argv):
    print("$ " + subprocess.list2cmdline([show(argv[0])] + argv[1:]))
    p = subprocess.run(argv, cwd=WORK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for stream in (p.stdout, p.stderr):
        if stream and stream.strip():
            print(stream.rstrip())
    print(f"[exit] {p.returncode}")
    return p.returncode


def sha(name):
    with open(os.path.join(WORK, name), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    shutil.copy2(os.path.join(HERE, "repro.hlsl"), WORK)

    dxc = os.path.join(BIN, "dxc.exe")
    dxl = os.path.join(BIN, "dxl.exe")

    print("ground truth: " + show(BIN))
    print()
    rc = run([dxc, "-T", "lib_6_x", "-Fo", "lib.dxo", "repro.hlsl"])
    rc |= run([dxl, "-T", "ps_6_0", "-E", "main", "-Fo", "via-dxl.dxo",
               "lib.dxo"])
    rc |= run([dxc, "-T", "ps_6_0", "-E", "main", "-Fo", "via-dxc-link.dxo",
               "lib.dxo", "-link"])
    # The self-test arm: a container that must NOT hash the same as the other
    # two, so an always-equal comparison is detectable.
    rc |= run([dxc, "-T", "ps_6_0", "-E", "main", "-Fo", "direct.dxo",
               "repro.hlsl"])
    print()

    a, b, c = sha("via-dxl.dxo"), sha("via-dxc-link.dxo"), sha("direct.dxo")
    print(f"sha256 via-dxl.dxo       {a}")
    print(f"sha256 via-dxc-link.dxo  {b}")
    print(f"sha256 direct.dxo        {c}   (self-test arm)")
    print()
    print("dxl.exe == dxc.exe -link : "
          + ("EQUAL" if a == b else "DIFFERENT"))
    print("self-test (a different input must hash differently): "
          + ("pass" if c not in (a, b) else "FAIL -- the comparison is dead"))
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
