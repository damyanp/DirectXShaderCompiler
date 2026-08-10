"""Which validator produced #3902's diagnostic?

The ground-truth build directory contains a dxil.dll (an out-of-band validator build,
FileVersion 1.9.0.5393, product string "damyanp/fix-resource-struct-zero-init, dc2088b20-dirty"),
and dxc loads dxil.dll when it can find one.  So the "Flags must match usage." error captured
in out-main-debug.txt was emitted by *that* DLL, not necessarily by main's own validator code.

This script re-runs the repro and the two controls with dxc.exe and dxcompiler.dll copied into
a scratch directory that contains no dxil.dll, which forces the internal validator that was
built from main.  If both configurations agree, the diagnostic is main's own.

It prints every command it runs with subprocess.list2cmdline, so the capture cannot claim a
command that was not executed.  Run it from anywhere:

    python probe-internal-validator.py

Set DXC_BIN to point somewhere else than <repo>/build/Debug/bin.
"""

import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[5]
BIN = pathlib.Path(os.environ.get("DXC_BIN", REPO / "build" / "Debug" / "bin"))
SCRATCH = HERE / "scratch-no-dxil"
OUT = HERE / "manual-case-internal-validator.txt"

CASES = [
    ("repro.hlsl", ["-T", "cs_6_5", "-E", "computeRTAO", "repro.hlsl"]),
    ("control-used.hlsl", ["-T", "cs_6_5", "-E", "computeRTAO", "control-used.hlsl"]),
    ("control-hello.hlsl", ["-T", "cs_6_5", "-E", "computeRTAO", "control-hello.hlsl"]),
    ("repro.hlsl (valver 1.7)",
     ["-T", "cs_6_5", "-E", "computeRTAO", "-validator-version", "1.7", "repro.hlsl"]),
]


def display(path):
    return str(path).replace(str(REPO), "<repo>").replace("\\", "/")


def run(exe, args, lines):
    argv = [str(exe)] + args
    lines.append("$ " + subprocess.list2cmdline([display(exe)] + args))
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
    lines.append("[exit] %d (0x%08X)" % (p.returncode, p.returncode & 0xFFFFFFFF))
    if p.returncode == 0:
        lines.append("<compiled cleanly; disassembly elided>")
    else:
        for name, text in (("stdout", p.stdout), ("stderr", p.stderr)):
            body = text.strip()
            if body:
                lines.append("--- %s ---" % name)
                lines.extend(body.splitlines()[:10])
    lines.append("")
    return p.returncode


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir()
    for name in ("dxc.exe", "dxcompiler.dll"):
        shutil.copy2(BIN / name, SCRATCH / name)
    assert not (SCRATCH / "dxil.dll").exists()

    lines = []
    lines.append("Which validator emits #3902's error: the external dxil.dll, or main's own?")
    lines.append("")
    lines.append("A. dxc.exe as registered (%s) -- dxil.dll IS present beside it" % display(BIN))
    lines.append("   dxil.dll FileVersion: " + dxil_version())
    lines.append("")
    for title, args in CASES:
        lines.append("# %s" % title)
        run(BIN / "dxc.exe", args, lines)

    lines.append("B. same dxc.exe + dxcompiler.dll copied to a directory with NO dxil.dll,")
    lines.append("   which forces the internal validator built from main")
    lines.append("")
    for title, args in CASES:
        lines.append("# %s" % title)
        run(SCRATCH / "dxc.exe", args, lines)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    shutil.rmtree(SCRATCH)
    for stray in ("shader.cso",):
        p = HERE / stray
        if p.exists():
            p.unlink()
    print(OUT)


def dxil_version():
    ps = ["powershell", "-NoProfile", "-Command",
          "(Get-Item '%s').VersionInfo.ProductVersion" % (BIN / "dxil.dll")]
    return subprocess.run(ps, capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
