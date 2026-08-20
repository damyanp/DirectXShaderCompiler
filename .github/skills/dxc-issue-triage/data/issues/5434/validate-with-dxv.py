"""Harness for issue 5434: runs a hand-constructed DXIL (.ll) file through the
standalone DXIL validator (dxv.exe) using a *chosen* dxcompiler.dll, so the
same host executable can be pointed at either the ground-truth (main-debug)
validator or a released one -- the "component cross-probe" pattern from
SKILL.md (dxopt -external), adapted to dxv.

Why this indirection is needed: only dxc.exe was built for main-debug (per
the batch's shared build); dxv.exe was not, and building it was out of scope
for this issue ("no rebuild"). dxv.exe loads its validator through
DxcCreateInstance in whichever dxcompiler.dll sits beside it (confirmed: with
dxcompiler.dll removed from the harness directory, dxv.exe fails immediately
with 0x8007007E, ERROR_MOD_NOT_FOUND -- see manual-case-dll-swap-proof.txt).
So a scratch directory holding a *released* dxv.exe + dxil.dll, with
main-debug's own dxcompiler.dll copied in beside them, runs main-debug's
validator logic through an unmodified host binary. This copies files; it
does not invoke cmake or msbuild, and it never touches the registered
main-debug dxc.exe.

Usage:
    python validate-with-dxv.py --harness-dir <dir> <file.ll> [<file.ll> ...]

<dir> must already contain dxv.exe, dxil.dll and the dxcompiler.dll to be
measured, laid out as described in notes.md.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# Machine-independent spelling for captured output, mirroring triage.py's own
# display_exe(): committed run output must not bake one contributor's absolute
# directory layout into the repo. The scratch harness directory lives under
# .cache/, which is exactly what "<cache>" denotes there.
SKILL_DIR = Path(__file__).resolve().parents[3]
CACHE_ROOT = SKILL_DIR / ".cache"


def display(path: Path) -> str:
    p = path.resolve()
    try:
        rel = p.relative_to(CACHE_ROOT)
        return "<cache>/" + str(rel).replace(os.sep, "/")
    except ValueError:
        return str(p).replace(os.sep, "/")


def run_one(harness_dir: Path, ll_path: Path) -> str:
    dxv = harness_dir / "dxv.exe"
    argv = [str(dxv), str(ll_path)]
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(harness_dir))
    lines = []
    lines.append("$ " + display(dxv) + " " + ll_path.name)
    lines.append("# cwd: " + display(harness_dir))
    lines.append("# exit: " + str(proc.returncode))
    lines.append("--- stdout+stderr ---")
    lines.append(proc.stdout + proc.stderr)
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--harness-dir", required=True)
    ap.add_argument("ll_files", nargs="+")
    args = ap.parse_args()
    harness_dir = Path(args.harness_dir)
    for ll_file in args.ll_files:
        sys.stdout.write(run_one(harness_dir, Path(ll_file)))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
