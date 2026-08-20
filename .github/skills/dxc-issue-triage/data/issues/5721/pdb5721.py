"""#5721 harness driver: build (once) and run pdb5721-harness.cpp.

The reported symptom -- IDxcLinker::Link's result never exposing
DXC_OUT_PDB via IDxcResult::GetOutput -- is a raw COM-API question that no
`dxc`/`dxl` command line can reach at all: `DxcContext::Link()`
(tools/clang/tools/dxclib/dxc.cpp) never calls `GetOutput(DXC_OUT_PDB, ...)`
or asks for `IDxcResult`, for any combination of flags (see expected.md).
So the "compiler" `triage.py run` drives here is this script wrapping a
small standalone C++ harness (pdb5721-harness.cpp, beside this file),
compiled out-of-tree with cl.exe -- it does not build or touch any part of
the DXC CMake project under build/. Registered per SKILL.md ("When the
symptom is in a pass dxc.exe cannot run, register the harness as a
compiler"), so `run`, `--shader`, `--expect` and `reindex` all keep working.

The compiled harness and the ground-truth dxcompiler.dll/dxil.dll it is
paired with are cached in `_build/` (gitignored, rebuilt automatically if
pdb5721-harness.cpp is newer than the cached exe) so a normal `run` does not
recompile on every invocation.

Argument convention for a `cmd.txt` line handed to this compiler: exactly
one argument, the HLSL source file to use as the library (same convention
`run --shader` expects: it retargets the one source-like argument in the
line and leaves everything else alone).

Usage (called by run-pdb5721.cmd, which is what gets registered):
    python pdb5721.py --version
    python pdb5721.py <source.hlsl>
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[os.pardir] * 6))
SKILL = os.path.abspath(os.path.join(HERE, *[os.pardir] * 3))

VCVARSALL = (
    r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\VC\Auxiliary"
    r"\Build\vcvarsall.bat"
)
CPP_SRC = os.path.join(HERE, "pdb5721-harness.cpp")
BUILD_DIR = os.path.join(HERE, "_build")
EXE_PATH = os.path.join(BUILD_DIR, "harness_x64.exe")
DEBUG_BIN = os.path.join(REPO, "build", "Debug", "bin")
DEBUG_LIB = os.path.join(REPO, "build", "Debug", "lib")
INCLUDE_DIR = os.path.join(REPO, "include")
BUILD_INCLUDE_DIR = os.path.join(REPO, "build", "include")


def display(path):
    """Machine-independent spelling of a path, for committed captures."""
    full = os.path.abspath(path)
    for root, name in ((SKILL, "<skill>"), (REPO, "<repo>")):
        if full.lower().startswith(root.lower() + os.sep):
            return name + full[len(root):].replace("\\", "/")
    return full


def ensure_built():
    """(Re)compile the harness if missing or stale. Prints what it did."""
    need_build = not os.path.isfile(EXE_PATH)
    if not need_build:
        need_build = os.path.getmtime(CPP_SRC) > os.path.getmtime(EXE_PATH)
    if not need_build:
        return

    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    for name in ("dxcompiler.dll", "dxil.dll"):
        src = os.path.join(DEBUG_BIN, name)
        if os.path.isfile(src):
            shutil.copy2(src, BUILD_DIR)

    rel_src = os.path.relpath(CPP_SRC, BUILD_DIR)
    rel_inc = os.path.relpath(INCLUDE_DIR, BUILD_DIR)
    rel_binc = os.path.relpath(BUILD_INCLUDE_DIR, BUILD_DIR)
    rel_lib = os.path.relpath(DEBUG_LIB, BUILD_DIR)
    cl_cmd = (
        f'call "{VCVARSALL}" x64 >nul && '
        f'cl.exe /nologo /EHsc /I"{rel_inc}" /I"{rel_binc}" '
        f'/Fe:"harness_x64.exe" "{rel_src}" /link /LIBPATH:"{rel_lib}"'
    )
    print("$ " + cl_cmd.replace(REPO, "<repo>"))
    p = subprocess.run(cl_cmd, shell=True, cwd=BUILD_DIR,
                        capture_output=True, text=True)
    if p.stdout:
        print(p.stdout.rstrip("\n"))
    if p.stderr:
        print(p.stderr.rstrip("\n"))
    print(f"[compile exit {p.returncode}]")
    if p.returncode != 0 or not os.path.isfile(EXE_PATH):
        sys.exit("pdb5721: harness build failed")


def emit_version():
    ensure_built()
    dxc = os.path.join(DEBUG_BIN, "dxc.exe")
    ver = ""
    if os.path.isfile(dxc):
        p = subprocess.run([dxc, "--version"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
        ver = (p.stdout or p.stderr or "").strip().replace("\n", " ")
    print(f"pdb5721 harness (IDxcLinker + IDxcResult COM probe); "
          f"exe {display(EXE_PATH)}; dxcompiler: {ver}")
    return 0


def main(argv):
    if not argv or argv[0] in ("--version", "-version", "/version"):
        return emit_version()

    ensure_built()
    shader = os.path.abspath(argv[0])
    print("$ " + subprocess.list2cmdline(
        [display(EXE_PATH), display(shader)]))
    sys.stdout.flush()
    p = subprocess.run([EXE_PATH, shader], cwd=BUILD_DIR,
                        capture_output=True, text=True)
    if p.stdout:
        print(p.stdout.rstrip("\n"))
    if p.stderr:
        print(p.stderr.rstrip("\n"))
    print(f"[exit {p.returncode}]")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
