"""Generate #5079's manual-case captures.

Not a dxc invocation, so this bypasses `triage.py run`/`cmd.txt` entirely --
see expected.md for why. Echoes the exact command it runs
(subprocess.list2cmdline) so the capture is reproducible, per the skill's
rule that a transcribed command line is otherwise an unchecked assertion.

Paths are derived relative to this script's own location (not hardcoded to
this machine), anchored on the repository layout: this file lives at
<repo>/.github/skills/dxc-issue-triage/data/issues/5079/, so climbing five
parents reaches <repo>.

Usage (from this directory):
    python gen-manual-case.py
"""
import subprocess
import sys
from pathlib import Path

ISSUE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ISSUE_DIR.parents[5]  # .../5079 -> issues -> data -> dxc-issue-triage -> skills -> .github -> repo
assert (REPO_ROOT / "include" / "dxc" / "dxcapi.h").is_file(), (
    f"repo root guess {REPO_ROOT} looks wrong -- include/dxc/dxcapi.h not found")

# `redact_paths` (read-only import, not a modification of triage.py) is the
# skill's own machine-path tokeniser: it turns this machine's absolute
# checkout path into `<repo>` inside committed captures, per SKILL.md's
# path-redaction rule, without touching any of the compiler-output content
# that actually carries information (`check_paths.py` enforces this).
SCRIPTS_DIR = ISSUE_DIR.parents[2] / "scripts"  # .../dxc-issue-triage/scripts
sys.path.insert(0, str(SCRIPTS_DIR))
from triage import redact_paths  # noqa: E402

CLANG = r"C:\Program Files\LLVM\bin\clang.exe"

DXC_INCLUDE = REPO_ROOT / "include"
DXH_INCLUDE = REPO_ROOT / "external" / "DirectX-Headers" / "include"
DXH_WSL_STUBS = DXH_INCLUDE / "wsl" / "stubs"

# This machine has no Linux sysroot, so WinAdapter.h's few POSIX-only calls
# (dlopen/dlsym/dlclose, locale_t & friends) are not declared by anything on
# a Windows host. These two issue-local files supply just those
# declarations -- never called, never linked, `-fsyntax-only` does neither
# -- so parsing can reach the typedef conflict under test. See their own
# header comments and notes.md for why this is not part of the conflict
# under test.
POSIX_SHIM_DIR = ISSUE_DIR / "posix-shim"          # provides <dlfcn.h>
LOCALE_PRELUDE = ISSUE_DIR / "posix-locale-prelude.h"  # force-included

CASES = [
    # (output filename, source filename, extra include dirs beyond DXH_INCLUDE/DXH_WSL_STUBS/DXC_INCLUDE)
    ("manual-case-clang-conflict.txt", "repro.cpp"),
    ("manual-case-clang-control-dxc-only.txt", "control-dxc-only.cpp"),
    ("manual-case-clang-control-directx-headers-only.txt",
     "control-directx-headers-only.cpp"),
]

for out_name, src_name in CASES:
    src = ISSUE_DIR / src_name
    argv = [
        CLANG,
        "-fsyntax-only",
        "-std=c++17",
        "-U_WIN32",           # force the non-Windows branch of both shims
        f"-I{DXH_INCLUDE}",
        f"-I{DXH_WSL_STUBS}",
        f"-I{DXC_INCLUDE}",
        f"-I{POSIX_SHIM_DIR}",
        f"-include{LOCALE_PRELUDE}",
        str(src),
    ]
    printed_cmd = redact_paths(subprocess.list2cmdline(argv))
    proc = subprocess.run(argv, capture_output=True, text=True)
    out_path = ISSUE_DIR / out_name
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# generator: gen-manual-case.py\n")
        f.write(f"# command: {printed_cmd}\n")
        f.write(f"# exit: {proc.returncode} (0x{proc.returncode & 0xffffffff:08x})\n")
        f.write("# stdout+stderr follows\n")
        f.write(redact_paths(proc.stdout))
        f.write(redact_paths(proc.stderr))
    print(f"{out_name}: exit {proc.returncode}")
