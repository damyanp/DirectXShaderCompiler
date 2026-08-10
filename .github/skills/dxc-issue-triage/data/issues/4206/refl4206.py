"""#4206 harness: compile with the DXC under test, then read reflection.

The reported symptom is a value returned by ``ID3D12ShaderReflection``
(``D3D12_SHADER_VARIABLE_DESC::uFlags``).  ``dxc.exe`` never calls that
interface, so no dxc invocation can score it.  ``dxa -dumpreflection`` does:
it drives the real accessors through DXC's own ``D3DReflectionDumper``
(``lib/DxilContainer/D3DReflectionDumper.cpp``), which prints ``uFlags`` at
line 104 via ``FlagsValue<D3D_SHADER_VARIABLE_FLAGS>`` after fetching the
struct with ``pVar->GetDesc()`` at line 254.

So this harness is registered as a compiler (SKILL.md, "When the symptom is in
a pass dxc.exe cannot run, register the harness as a compiler"), which keeps
``run``, ``--shader``, ``--expect``, ``audit`` and ``reindex`` all applicable.

Two knobs, so the same harness can date the behaviour:

  DXC_EXE       the dxc.exe that COMPILES the container   (the subject)
  DXC_READER    the dxa.exe that READS the container back (the instrument)

Both default to this repo's Debug build.  Holding DXC_READER fixed while
varying DXC_EXE is the single-variable experiment, and it is the right one:
the used/unused bit is computed at compile time by
``DxilLowerCreateHandleForLib::UpdateCBufferUsage`` and stored in DXIL
metadata (``kDxilFieldAnnotationCBUsedTag`` = 9), so the container already
carries the answer and the reader only reports it.

``dxa`` has no ``--version``, and its diagnostics print an absolute path, so
the instrument is identified instead by the SHA-256 of the ``dxcompiler.dll``
it will load -- machine-independent, and printed on every run so no capture is
ambiguous about which reader produced it.

Every command is echoed with ``subprocess.list2cmdline`` before it runs, so a
capture states what was executed rather than asserting it.
"""

import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", ".."))
DEFAULT_BIN = os.path.join(REPO, "build", "Debug", "bin")


def display(path):
    """Machine-independent rendering, anchored on the repository name."""
    p = os.path.abspath(path)
    marker = os.sep + "DirectXShaderCompiler" + os.sep
    i = p.find(marker)
    return "<repo>" + p[i + len(marker) - 1:] if i >= 0 else p


def tool(env_name, default_name):
    return os.environ.get(env_name) or os.path.join(DEFAULT_BIN, default_name)


def sha256_of(path):
    if not os.path.exists(path):
        return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(argv, cwd=None):
    print("$ " + subprocess.list2cmdline([display(argv[0])] + argv[1:]))
    sys.stdout.flush()
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    text = (p.stdout or "") + (p.stderr or "")
    if text:
        print(text if text.endswith("\n") else text + "\n", end="")
    return p.returncode, text


def banner(dxc, reader):
    reader_dll = os.path.join(os.path.dirname(os.path.abspath(reader)),
                              "dxcompiler.dll")
    print("refl4206-compiler=" + display(dxc))
    print("refl4206-reader=" + display(reader))
    print("refl4206-reader-dll=" + display(reader_dll)
          + " sha256=" + sha256_of(reader_dll)[:16])
    sys.stdout.flush()


def main():
    dxc = tool("DXC_EXE", "dxc.exe")
    reader = tool("DXC_READER", "dxa.exe")
    args = sys.argv[1:]

    if not args or "--version" in args or "-version" in args:
        print("refl4206 harness (issue 4206): compiles with DXC_EXE, then "
              "reads ID3D12ShaderReflection with DXC_READER -dumpreflection")
        banner(dxc, reader)
        run([dxc, "--version"])
        return 0

    banner(dxc, reader)

    src = next((a for a in reversed(args) if a.lower().endswith(".hlsl")), None)
    if src is None:
        print("refl4206: no .hlsl operand in " + subprocess.list2cmdline(args),
              file=sys.stderr)
        return 3
    stem = os.path.splitext(os.path.basename(src))[0]
    container = stem + ".refl4206.dxil"

    rc, _ = run([dxc] + args + ["-Fo", container])
    print(f"refl4206-compile-exit=0x{rc & 0xFFFFFFFF:08X}")
    if rc != 0 or not os.path.exists(container):
        print("refl4206: no container produced; reflection not attempted")
        return rc if rc != 0 else 4

    rrc, _ = run([reader, "-dumpreflection", container])
    print(f"refl4206-reflect-exit=0x{rrc & 0xFFFFFFFF:08X}")
    return rrc


if __name__ == "__main__":
    sys.exit(main())
