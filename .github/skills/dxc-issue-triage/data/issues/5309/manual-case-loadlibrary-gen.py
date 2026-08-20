"""Generator for manual-case-loadlibrary.txt (#5309).

Compiles manual-case-loadlibrary-harness.cpp with MSVC (via vcvarsall.bat) and
runs it, recording the exact commands used with subprocess.list2cmdline so the
capture is reproducible rather than a transcribed claim. This does not touch
the DXC CMake build in build/ at all -- it is a standalone, out-of-tree compile
of one .cpp file, following the same pattern as #4786's ABI harness.

Run from the issue directory:
    python manual-case-loadlibrary-gen.py
"""
import os
import subprocess
import sys

VCVARSALL = (
    r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\VC\Auxiliary"
    r"\Build\vcvarsall.bat"
)
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "manual-case-loadlibrary-harness.cpp")


def main():
    log = []
    out_dir = os.path.join(HERE, "_scratch-loadlibrary")
    os.makedirs(out_dir, exist_ok=True)
    exe_name = "harness_x64.exe"
    exe_path = os.path.join(out_dir, exe_name)
    src_rel = os.path.relpath(SRC, out_dir)

    cl_cmd = (
        f'call "{VCVARSALL}" x64 >nul && '
        f'cl.exe /nologo /EHsc /Fe:"{exe_name}" "{src_rel}"'
    )
    log.append("--- compile (x64) ---")
    log.append("$ " + cl_cmd)
    p = subprocess.run(cl_cmd, shell=True, cwd=out_dir, capture_output=True,
                        text=True)
    log.append(p.stdout)
    if p.stderr:
        log.append(p.stderr)
    log.append(f"[compile exit {p.returncode}]")

    if p.returncode != 0 or not os.path.isfile(exe_path):
        log.append("BUILD FAILED, skipping run")
    else:
        log.append("--- run ---")
        log.append("$ " + subprocess.list2cmdline([exe_name]))
        pr = subprocess.run([exe_path], cwd=out_dir, capture_output=True,
                             text=True)
        log.append(pr.stdout)
        if pr.stderr:
            log.append(pr.stderr)
        log.append(f"[exit {pr.returncode}]")

    text = "\n".join(log)
    out_path = os.path.join(HERE, "manual-case-loadlibrary.txt")
    header = (
        "# issue: 5309\n"
        "# generator: manual-case-loadlibrary-gen.py\n"
        "# purpose: confirm that LoadLibraryExW(..., LOAD_LIBRARY_SEARCH_APPLICATION_DIR)\n"
        "#          failing on an absent module -- the exact call dxbc2dxil.cpp's\n"
        "#          Converter::GetDxcCreateInstance makes for \"dxilconv.dll\" --\n"
        "#          reports HRESULT 0x8007007e, matching the issue's reported\n"
        "#          \"Conversion failed - error code 0x8007007e\"\n"
        "# note: standalone compile via cl.exe, outside build/, no DXC target touched\n\n"
    )
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + text + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
