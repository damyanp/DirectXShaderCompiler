"""#2952 -- ground-truth witnesses that share no code with refl2952.exe.

Three questions, three tools, so that no single reader decides the verdict
(SKILL.md, "A control cannot catch a broken reader", measured on #2923):

  1. `dxa -dumpreflection` drives ID3D12LibraryReflection through DXC's own
     D3DReflectionDumper (lib/DxilContainer/D3DReflectionDumper.cpp). It prints
     what the D3D12 reflection API can see. If the payload size were reachable
     from that API, this is where it would appear.
  2. `dxa -dumprdat` prints the container's RDAT part. If the payload size is
     recorded anywhere in the container, this is where it appears.
  3. A listing of what each release package ships in `inc/`. The RDAT reader
     DXC uses internally lives in include/dxc/DxilContainer/, which is not part
     of any release package -- so "the data is in the container" and "an
     application can read it" are different claims, and this is the evidence
     for the gap between them.

Every command is echoed with subprocess.list2cmdline from the argv that
actually ran, so the transcript is derived rather than transcribed, and paths
are collapsed to <cache>/<triage>/<repo>.

Usage: python capture-witnesses.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
RELEASES = os.path.join(SKILL, ".cache", "compilers", "releases")
OUTDIR = os.path.join(HERE, "out")


def redact(path):
    p = os.path.abspath(path).replace(os.sep, "/")
    for base, token in ((os.path.join(SKILL, ".cache"), "<cache>"),
                        (SKILL, "<triage>"), (REPO, "<repo>")):
        b = os.path.abspath(base).replace(os.sep, "/")
        if p.lower() == b.lower():
            return token
        if p.lower().startswith(b.lower() + "/"):
            return token + p[len(b):]
    return p


def run(out, argv, cwd=HERE):
    shown = redact(argv[0]) + " " + subprocess.list2cmdline(
        [redact(a) if os.path.isabs(a) else a for a in argv[1:]])
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=cwd, timeout=300)
    out += [f"$ {shown}", f"[exit] {p.returncode}"]
    out += ["  " + ln for ln in (p.stdout + p.stderr).rstrip().splitlines()]
    out.append("")
    return p


def main():
    dxc = os.path.join(BUILD_BIN, "dxc.exe")
    dxa = os.path.join(BUILD_BIN, "dxa.exe")
    for tool in (dxc, dxa):
        if not os.path.isfile(tool):
            sys.exit(f"missing {tool}")
    os.makedirs(OUTDIR, exist_ok=True)
    dxil = os.path.join(OUTDIR, "repro-witness.dxil")

    out = [
        "#2952 ground-truth witnesses",
        "",
        "Produced by `python capture-witnesses.py`. Three independent readers",
        "of the same container, so that no single one decides the verdict.",
        "",
        "1. dxa -dumpreflection  -- what the D3D12 reflection API can see",
        "                           (for a library dxa also dumps RDAT first;",
        "                           the API part starts at",
        "                           `ID3D12LibraryReflection:`)",
        "2. dxa -dumprdat        -- what the container actually records",
        "3. release inc/ listing -- what an application is given to read it with",
        "",
        "=== compile the repro with the ground-truth build ===", ""]
    run(out, [dxc, "-T", "lib_6_3", "repro.hlsl", "-Fo", dxil])

    out += ["=== 1. dxa -dumpreflection: the D3D12 reflection view ===",
            "",
            "For a library container this prints two things, because dxa walks",
            "the container's parts and dumps both the RDAT part and the DXIL",
            "part's ID3D12LibraryReflection (tools/clang/tools/dxa/dxa.cpp,",
            "DxaContext::DumpReflection). Scroll to `ID3D12LibraryReflection:`",
            "for the part that matters here: D3DReflectionDumper",
            "(lib/DxilContainer/D3DReflectionDumper.cpp) printing each",
            "D3D12_FUNCTION_DESC. It shares no code with refl2952.exe. Note",
            "what it does and does not print. `Shader Version: AnyHit 6.3` is",
            "the dumper decoding D3D12_FUNCTION_DESC.Version through",
            "D3D12_SHVER_GET_TYPE -- so the shader kind IS reachable from the",
            "reflection API. No payload size appears anywhere in that block,",
            "because D3D12_FUNCTION_DESC has no field that could hold one.",
            ""]
    run(out, [dxa, "-dumpreflection", dxil])

    out += ["=== 2. dxa -dumprdat: what the container records ===",
            "",
            "Every entry carries ShaderKind, PayloadSizeInBytes and",
            "AttributeSizeInBytes. repro.hlsl declares a 28-byte payload, an",
            "8-byte attribute struct and a 12-byte callable parameter, and all",
            "three appear below. The data the issue asks for is therefore",
            "already in the container; what is missing is a way to read it.",
            ""]
    run(out, [dxa, "-dumprdat", dxil])

    out += ["=== 3. what a release package gives an application ===",
            "",
            "hlsl::RDAT::DxilRuntimeData -- the reader dxa uses above, and the",
            "one refl2952.exe uses -- is declared in",
            "include/dxc/DxilContainer/DxilRuntimeReflection.h with its",
            "implementation in DxilRuntimeReflection.inl and the record layout",
            "in RDAT_LibraryTypes.inl. None of those is shipped. Listing of",
            "inc/ in the cached release packages:",
            ""]
    if os.path.isdir(RELEASES):
        for tag in sorted(os.listdir(RELEASES)):
            for root, dirs, files in os.walk(os.path.join(RELEASES, tag)):
                if os.path.basename(root).lower() != "inc":
                    continue
                names = []
                for r2, _d2, f2 in os.walk(root):
                    for f in f2:
                        names.append(
                            os.path.relpath(os.path.join(r2, f), root)
                            .replace(os.sep, "/"))
                out.append(f"  {tag:>18}  inc/: " +
                           (", ".join(sorted(names)) if names else "(empty)"))
                dirs[:] = []
    else:
        out.append(f"  (no cached release tree at {redact(RELEASES)})")
    out += ["",
            "  v1.4.1907's package is a bare dxc.exe/dxcompiler.dll pair with",
            "  no inc/ directory at all.",
            ""]

    path = os.path.join(HERE, "manual-case-ground-truth-witnesses.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {redact(path)}")


if __name__ == "__main__":
    main()
