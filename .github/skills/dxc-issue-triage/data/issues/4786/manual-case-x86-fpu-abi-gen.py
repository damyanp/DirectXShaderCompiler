"""Generator for manual-case-x86-fpu-abi.txt (#4786).

Compiles manual-case-x86-fpu-abi-harness.cpp for x86 and for x64 with MSVC
(via vcvarsall.bat) and runs both binaries, recording the exact commands used
with subprocess.list2cmdline so the capture is reproducible rather than a
transcribed claim. This does not touch the DXC CMake build in build/ at all --
it is a standalone, out-of-tree compile of one .cpp file.

Run from the issue directory:
    python manual-case-x86-fpu-abi-gen.py
"""
import os
import subprocess
import sys

VCVARSALL = (
    r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\VC\Auxiliary"
    r"\Build\vcvarsall.bat"
)
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "manual-case-x86-fpu-abi-harness.cpp")


def run_logged(argv, cwd, log, display_argv=None):
    log.append("$ " + subprocess.list2cmdline(display_argv or argv))
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    log.append(p.stdout)
    if p.stderr:
        log.append(p.stderr)
    log.append(f"[exit {p.returncode}]")
    return p.returncode


def build_and_run(vc_arch, exe_name, log):
    out_dir = os.path.join(HERE, f"_scratch-{vc_arch}")
    os.makedirs(out_dir, exist_ok=True)
    exe_path = os.path.join(out_dir, exe_name)
    src_rel = os.path.relpath(SRC, out_dir)
    # vcvarsall.bat and cl.exe must run in the SAME cmd.exe process, so chain
    # them with && inside one `cmd /c` invocation. Run and log with cwd=out_dir
    # and relative names so the captured command line carries no machine
    # checkout path (only the VS install path, which is not contributor-owned).
    cl_cmd = (
        f'call "{VCVARSALL}" {vc_arch} >nul && '
        f'cl.exe /nologo /EHsc /Fe:"{exe_name}" "{src_rel}"'
    )
    log.append(f"--- compile ({vc_arch}) ---")
    log.append("$ " + cl_cmd)
    p = subprocess.run(cl_cmd, shell=True, cwd=out_dir, capture_output=True,
                        text=True)
    log.append(p.stdout)
    if p.stderr:
        log.append(p.stderr)
    log.append(f"[compile exit {p.returncode}]")
    if p.returncode != 0 or not os.path.isfile(exe_path):
        log.append(f"BUILD FAILED for {vc_arch}, skipping run")
        return None
    log.append(f"--- run ({vc_arch}) ---")
    rc = run_logged([exe_path], out_dir, log, display_argv=[exe_name])
    return rc


def main():
    log = []
    for vc_arch, exe_name in (("x86", "harness_x86.exe"), ("x64", "harness_x64.exe")):
        build_and_run(vc_arch, exe_name, log)
        log.append("")

    text = "\n".join(log)
    out_path = os.path.join(HERE, "manual-case-x86-fpu-abi.txt")
    header = (
        "# issue: 4786\n"
        "# generator: manual-case-x86-fpu-abi-gen.py\n"
        "# purpose: isolate the float-return-by-value ABI mechanism the issue "
        "attributes the corruption to, independent of DxbcConverter/dxc.exe\n"
        "# note: standalone compile via cl.exe, outside build/, no DXC target "
        "touched\n\n"
    )
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + text + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
