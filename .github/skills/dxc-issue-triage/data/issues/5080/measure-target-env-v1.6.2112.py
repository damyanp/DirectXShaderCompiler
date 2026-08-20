"""Per-release target-env control for #5080.

`cmd.txt`'s `-fspv-target-env=vulkan1.3` postdates v1.6.2112 (the first stable
release advertising `-fspv-debug=vulkan-with-source` at all -- see
out-v1.4.1907.txt, out-v1.5.2010.txt, out-v1.6.2104.txt, out-v1.6.2106.txt,
which are all correctly classified invalid-probe for lacking the debug-info
mode). v1.6.2112 rejects the target-env *value* it does not recognise before
reaching the code under test (out-v1.6.2112.txt: "unknown SPIR-V target
environment 'vulkan1.3'", allowed options vulkan1.0/1.1/1.2/universal1.5),
which `triage.py`'s current invalid-probe classifier does not yet recognise
(see method-notes.md) -- so the tool-driven bisect scored it a false
"no-repro" instead of "invalid-probe".

This script re-probes v1.6.2112 with `vulkan1.0`, the oldest environment
value that release accepts, changing nothing else about the command. If the
symptom appears there, v1.6.2112 was never clean; the tool's automatic
capture at vulkan1.3 was an artifact of the option value, not of the defect.
"""
import os
import subprocess
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", "..", "..", ".."))

EXE = os.path.join(
    _REPO_ROOT, "build", "tools", "clang", "test", "dxc_releases", "v1.6.2112",
    "dxc_2021_12_08", "bin", "x64", "dxc.exe")


def display_exe(path):
    """Machine-independent spelling of the compiler path, matching
    triage.py's `display_exe` convention (`<repo>`-relative), for committed
    output."""
    rel = os.path.relpath(os.path.abspath(path), _REPO_ROOT)
    return "<repo>\\" + rel.replace("/", "\\")


CASES = [
    ("as-filed (vulkan1.3, rejected value)",
     [EXE, "-spirv", "-fspv-target-env=vulkan1.3", "-T", "ps_6_2", "-E", "ps_main",
      "-fvk-use-dx-layout", "-fspv-debug=vulkan-with-source", "repro.hlsl"]),
    ("substituted (vulkan1.0, oldest accepted value)",
     [EXE, "-spirv", "-fspv-target-env=vulkan1.0", "-T", "ps_6_2", "-E", "ps_main",
      "-fvk-use-dx-layout", "-fspv-debug=vulkan-with-source", "repro.hlsl"]),
]

for label, argv in CASES:
    print(f"=== {label} ===")
    display_argv = [display_exe(argv[0])] + argv[1:]
    print("$", subprocess.list2cmdline(display_argv))
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=".")
    print(f"[exit] {proc.returncode} (0x{proc.returncode & 0xffffffff:08X})")
    print("--- stdout ---")
    print(proc.stdout)
    print("--- stderr ---")
    print(proc.stderr)
    print()
