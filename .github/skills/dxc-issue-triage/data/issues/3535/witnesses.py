"""Witness generator for DXC issue 3535.

Two outputs, both committed beside this script:

  manual-case-witnesses.txt        ground-truth evidence, six sections
  manual-case-reflection-matrix.txt   per-release ID3D12ShaderReflection walk

Every command is echoed with subprocess.list2cmdline before it runs, so the
transcript is what actually executed rather than a transcription of it
(SKILL.md: "Generate every manual-case-*.txt from a small script that echoes
the command it is about to run").

Each section carries an explicit self-check that prints PASS or a loud
WITNESS-FAIL marker. A harness that can return "nothing here" and "nothing
matched" through the same channel will eventually be believed, so the checks
assert presence as well as absence.

Nothing here writes to any file the triage tool scores. Containers and copied
binaries go to out/, which is gitignored.

Usage:
    python witnesses.py                 # ground-truth witnesses
    python witnesses.py --matrix        # per-release reflection walk
    python witnesses.py --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
SKILL = HERE.parents[2]
BIN = Path(os.environ.get("DXC_BIN", REPO / "build" / "Debug" / "bin"))
DXC = BIN / "dxc.exe"
DXA = BIN / "dxa.exe"
OUT = HERE / "out"
DB = SKILL / ".cache" / "triage.db"


def redact(text: str) -> str:
    """Replace this machine's layout with the workspace's <repo> convention.

    Both the plain and the JSON/IR-escaped separator forms, because an escaped
    path does not contain the literal the obvious scan looks for.
    """
    for root, token in ((str(REPO), "<repo>"),):
        for sep in ("\\\\", "\\", "/"):
            spelling = root.replace("\\", sep)
            text = text.replace(spelling, token)
            text = text.replace(spelling.lower(), token)
    return text


class Report:
    def __init__(self, path: Path, title: str):
        self.path = path
        self.lines: list[str] = [title, "=" * len(title), ""]
        self.failures = 0

    def w(self, line: str = "") -> None:
        self.lines.append(line)

    def run(self, argv: list[str], cwd: Path | None = None) -> tuple[int, str]:
        printable = subprocess.list2cmdline([str(a) for a in argv])
        self.w("$ " + redact(printable))
        proc = subprocess.run(
            [str(a) for a in argv],
            cwd=str(cwd or HERE),
            capture_output=True,
            text=True,
            errors="replace",
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.w(f"[exit] {proc.returncode}")
        return proc.returncode, out

    def check(self, label: str, ok: bool) -> None:
        if ok:
            self.w(f"[check] PASS  {label}")
        else:
            self.failures += 1
            self.w(f"[check] WITNESS-FAIL  {label}")

    def excerpt(self, text: str, patterns: list[str], context: str = "") -> None:
        if context:
            self.w(context)
        hits = 0
        for line in text.splitlines():
            if any(re.search(p, line) for p in patterns):
                self.w("    " + redact(line.rstrip()))
                hits += 1
        if hits == 0:
            self.w("    (no matching lines)")

    def save(self) -> None:
        if self.failures:
            self.lines.append("")
            self.lines.append(
                f"WITNESS-FAIL: {self.failures} self-check(s) failed; do not cite this file"
            )
        else:
            self.lines.append("")
            self.lines.append("all self-checks passed")
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print(f"wrote {self.path.name} ({'FAIL' if self.failures else 'ok'})")


def ground_truth() -> int:
    OUT.mkdir(exist_ok=True)
    r = Report(
        HERE / "manual-case-witnesses.txt",
        "3535 ground-truth witnesses: what reflection carries for a struct used "
        "as a VS input",
    )
    r.w("compiler: main-debug (see .cache/compilers/main-debug.json); the binary")
    r.w("self-reports a fork-local commit, cite 13730886e.")
    r.w()
    rc, ver = r.run([DXC, "--version"])
    r.w("    " + redact(ver.strip()))
    r.w()

    # ---------------------------------------------------------------- 1
    r.w("-" * 72)
    r.w("1. The whole ID3D12ShaderReflection surface for the repro")
    r.w("-" * 72)
    r.w("dxa -dumpreflection walks ID3D12ShaderReflection through DXC's own")
    r.w("D3DReflectionDumper and prints every field of every descriptor it can")
    r.w("reach. This is the answer to 'what can an application actually ask for'.")
    r.w()
    dxo = OUT / "repro.dxo"
    rc, _ = r.run([DXC, "-T", "vs_6_0", "-E", "VS", "-Fo", dxo, "repro.hlsl"])
    r.check("repro compiled", rc == 0 and dxo.exists())
    rc, refl = r.run([DXA, "-dumpreflection", dxo])
    r.w()
    for line in refl.splitlines():
        r.w("    " + redact(line.rstrip()))
    r.w()
    r.check(
        "the walk reached input parameters",
        "InputParameter Elements: 2" in refl,
    )
    r.check(
        "the walk reached constant-buffer type reflection (self-test: the "
        "instrument does read type information)",
        "D3D12_SHADER_TYPE_DESC: Name: CbStruct" in refl,
    )
    r.check(
        "no input-struct member name anywhere in the reflection walk",
        not re.search(r"\bmPos\b|\bmColor\b", refl),
    )

    # ---------------------------------------------------------------- 2
    r.w("-" * 72)
    r.w("2. The member names dxc prints come from the reflection part")
    r.w("-" * 72)
    r.w("Three measurements. (a) A default compile prints the cbuffer struct's")
    r.w("HLSL field names, though the DXIL module it prints has no")
    r.w("!dx.typeAnnotations to hold them. (b) Disassembling the container with")
    r.w("-dumpbin prints them too. (c) -Qstrip_reflect removes the reflection")
    r.w("part and they disappear. So the names are rendered from reflection data.")
    r.w()
    rc, plain = r.run([DXC, "-T", "vs_6_0", "-E", "VS", "repro.hlsl"])
    r.excerpt(plain, [r"cbAlpha", r"dx\.typeAnnotations"], "(a) default compile:")
    r.check("(a) cbuffer field name printed", "cbAlpha" in plain)
    r.check(
        "(a) module carries no !dx.typeAnnotations to print it from",
        "dx.typeAnnotations" not in plain,
    )
    r.w()
    rc, dumped = r.run([DXC, "-dumpbin", dxo])
    r.excerpt(dumped, [r"cbAlpha"], "(b) -dumpbin of the same container:")
    r.check("(b) container disassembly prints the field name", "cbAlpha" in dumped)
    r.w()
    stripped = OUT / "stripped.dxo"
    rc, _ = r.run(
        [DXC, "-T", "vs_6_0", "-E", "VS", "-Qstrip_reflect", "-Fo", stripped,
         "repro.hlsl"]
    )
    rc, parts_full = r.run([DXA, "-listparts", dxo])
    r.w("    " + redact(parts_full.replace("\n", "\n    ").rstrip()))
    rc, parts_strip = r.run([DXA, "-listparts", stripped])
    r.w("    " + redact(parts_strip.replace("\n", "\n    ").rstrip()))
    rc, stripdis = r.run([DXC, "-dumpbin", stripped])
    r.check("(c) STAT present when reflection is kept", "STAT" in parts_full)
    r.check("(c) STAT gone with -Qstrip_reflect", "STAT" not in parts_strip)
    r.check(
        "(c) field name gone with the reflection part",
        "cbAlpha" not in stripdis,
    )
    r.check(
        "(c) the shader is otherwise unchanged: buffer-definitions block still "
        "emitted",
        "Buffer Definitions" in stripdis,
    )

    # ---------------------------------------------------------------- 3
    r.w("-" * 72)
    r.w("3. The front end holds the field name and the semantic together")
    r.w("-" * 72)
    r.w("-fcgl stops before DXIL lowering. Tag 6 is")
    r.w("kDxilFieldAnnotationFieldNameTag and tag 4 is")
    r.w("kDxilFieldAnnotationSemanticStringTag")
    r.w("(include/dxc/DXIL/DxilMetadataHelper.h:247,249), so one annotation")
    r.w("carries both halves of the mapping the reporter is asking for.")
    r.w()
    rc, fcgl = r.run([DXC, "-T", "vs_6_0", "-E", "VS", "-fcgl", "repro.hlsl"])
    r.excerpt(fcgl, [r'!"mPos"', r'!"mColor"', r'!"cbAlpha"', r"struct\.VertexIn undef"])
    r.check(
        "field name and semantic appear in one annotation before lowering",
        bool(re.search(r'i32 6, !"mPos".*i32 4, !"POSITION"', fcgl)),
    )

    # ---------------------------------------------------------------- 4
    r.w("-" * 72)
    r.w("4. What survives into reflection metadata after lowering")
    r.w("-" * 72)
    r.w("-Qkeep_reflect_in_dxil keeps the reflection metadata in the DXIL part so")
    r.w("it can be read directly. The constant-buffer struct is annotated; the")
    r.w("input struct has no annotation at all, and its type is gone.")
    r.w()
    rc, keep = r.run(
        [DXC, "-T", "vs_6_0", "-E", "VS", "-Qkeep_reflect_in_dxil", "repro.hlsl"]
    )
    r.excerpt(keep, [r"dx\.typeAnnotations", r"^!\d+ = !\{i32 0, %struct",
                     r'!"cbAlpha"', r'!"mPos"', r"^%struct\."])
    r.check("reflection metadata is present to inspect", "dx.typeAnnotations" in keep)
    r.check("cbuffer struct is annotated with its field names", '!"cbAlpha"' in keep)
    r.check(
        "input struct has no field-name annotation", '!"mPos"' not in keep
    )
    r.check(
        "input struct type is not even declared in the module",
        "%struct.VertexIn" not in keep,
    )

    # ---------------------------------------------------------------- 5
    r.w("-" * 72)
    r.w("5. The names do survive in debug info")
    r.w("-" * 72)
    r.w("-Zi keeps DWARF-style member metadata. This is not reflection and is not")
    r.w("reachable through ID3D12ShaderReflection, but it does mean the names")
    r.w("still exist in a -Zi build's debug module. It is also why a Compiler")
    r.w("Explorer pane cannot be searched for these identifiers: CE appends")
    r.w("-Zi -Qembed_debug to every DXC pane.")
    r.w()
    rc, zi = r.run(
        [DXC, "-T", "vs_6_0", "-E", "VS", "-Zi", "-Qembed_debug", "repro.hlsl"]
    )
    r.excerpt(zi, [r"DW_TAG_member, name: \"m", r"DW_TAG_structure_type, name: \"VertexIn"])
    r.check(
        "debug info names the struct members",
        bool(re.search(r'DW_TAG_member, name: "mPos"', zi)),
    )

    # ---------------------------------------------------------------- 6
    r.w("-" * 72)
    r.w("6. D3D12_SIGNATURE_PARAMETER_DESC is the whole of what a signature")
    r.w("   element can report, and no call reaches a type from one")
    r.w("-" * 72)
    r.w("Quoted from the header this build compiles against.")
    r.w()
    hdr = REPO / "external" / "DirectX-Headers" / "include" / "directx" / "d3d12shader.h"
    text = hdr.read_text(encoding="utf-8", errors="replace")
    start = text.find("typedef struct _D3D12_SIGNATURE_PARAMETER_DESC")
    end = text.find("D3D12_SIGNATURE_PARAMETER_DESC;", start)
    r.w("    " + redact(str(hdr.relative_to(REPO)).replace("\\", "/")))
    for line in text[start:end + len("D3D12_SIGNATURE_PARAMETER_DESC;")].splitlines():
        r.w("    " + line.rstrip())
    r.check(
        "SemanticName is the only string in the descriptor",
        text[start:end].count("LPCSTR") == 1,
    )
    r.w()
    r.w("And there is no indirect route either. ID3D12ShaderReflectionType is")
    r.w("the only interface that can name a struct's members")
    r.w("(GetMemberTypeName), and the whole of ID3D12ShaderReflection is:")
    r.w()
    istart = text.find("DECLARE_INTERFACE_(ID3D12ShaderReflection, IUnknown)")
    iend = text.find("};", istart)
    methods = [
        ln.strip()
        for ln in text[istart:iend].splitlines()
        if "STDMETHOD" in ln
    ]
    for ln in methods:
        r.w("    " + ln)
    r.w()
    r.w("Only GetConstantBufferByIndex/ByName and GetVariableByName lead to a")
    r.w("type object. Nothing accepts a signature parameter index and returns")
    r.w("one, so GetMemberTypeName cannot be called for an input struct at all.")
    r.w("This is a COM vtable, so it is fixed for every version of the API.")
    r.check(
        "no method maps a signature parameter to a reflection type",
        not any(
            "ShaderReflectionType*" in m and "Parameter" in m for m in methods
        ),
    )
    r.check(
        "the only routes to a type object are the two cbuffer accessors and "
        "GetVariableByName",
        sum(
            1
            for m in methods
            if "ShaderReflectionConstantBuffer*" in m
            or "ShaderReflectionVariable*" in m
        )
        == 3,
    )
    r.w()
    r.w("Note what this means for the instrument in section 1:")
    r.w("D3DReflectionDumper never calls GetMemberTypeName, so the absence of a")
    r.w("member name from that dump is on its own ambiguous. The dump settles")
    r.w("that no *other* printed descriptor field carries the identifier; this")
    r.w("section is what settles that no reachable call could return it.")

    r.save()
    return 1 if r.failures else 0


def release_rows() -> list[tuple[str, str]]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT tag, cached_path FROM releases "
        "WHERE prerelease=0 AND bisectable=1 AND cached_path IS NOT NULL "
        "ORDER BY build_date"
    ).fetchall()
    con.close()
    return rows


def matrix() -> int:
    OUT.mkdir(exist_ok=True)
    r = Report(
        HERE / "manual-case-reflection-matrix.txt",
        "3535 release matrix: has any shipped ID3D12ShaderReflection ever named "
        "an input struct's members?",
    )
    r.w("`triage.py bisect` cannot answer this: it substitutes each release's")
    r.w("dxc.exe, and dxc.exe never calls a reflection interface. So the")
    r.w("instrument is held fixed (dxa.exe from the ground-truth build, which")
    r.w("statically links D3DReflectionDumper) while the thing under test -- the")
    r.w("reflection implementation, which lives in dxcompiler.dll -- is varied by")
    r.w("copying each release's DLL next to it. Each release also compiles the")
    r.w("repro with its own dxc.exe, so the container is period-correct too.")
    r.w()
    r.w("Columns:")
    r.w("  api-member-names : hits for mPos/mColor anywhere in the reflection walk")
    r.w("  selftest         : the walk reached constant-buffer type reflection,")
    r.w("                     so a zero in the previous column is a finding and")
    r.w("                     not a walk that stopped early")
    r.w("  module-annot     : the release's own disassembly carries a field-name")
    r.w("                     annotation for the input struct (!\"mPos\")")
    r.w()

    rows = release_rows()
    table: list[tuple[str, str, str, str, str]] = []
    for tag, exe_path in rows:
        exe = Path(exe_path)
        r.w("-" * 72)
        r.w(f"release {tag}")
        r.w("-" * 72)
        if not exe.exists():
            r.w(f"    [skip] no local tree")
            table.append((tag, "n/a", "n/a", "n/a", "no local tree"))
            continue
        work = OUT / f"probe-{tag}"
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        for name in ("dxcompiler.dll", "dxil.dll"):
            src = exe.parent / name
            if src.exists():
                shutil.copy2(src, work / name)
        shutil.copy2(DXA, work / "dxa.exe")
        digest = hashlib.sha256((work / "dxcompiler.dll").read_bytes()).hexdigest()[:12]
        r.w(f"    dxcompiler.dll under test: sha256:{digest}")

        dxo = work / "repro.dxo"
        rc, _ = r.run([exe, "-T", "vs_6_0", "-E", "VS", "-Fo", dxo, "repro.hlsl"])
        if rc != 0 or not dxo.exists():
            r.check(f"{tag}: repro compiled", False)
            table.append((tag, "n/a", "n/a", "n/a", "compile failed"))
            continue
        rc, dis = r.run([exe, "-T", "vs_6_0", "-E", "VS", "repro.hlsl"])
        rc, refl = r.run([work / "dxa.exe", "-dumpreflection", dxo])

        hits = len(re.findall(r"\bmPos\b|\bmColor\b", refl))
        selftest = "D3D12_SHADER_TYPE_DESC: Name: CbStruct" in refl
        inputs = "InputParameter Elements: 2" in refl
        annot = '!"mPos"' in dis
        sems = re.findall(r"SemanticName: (\S+)", refl)
        r.w(f"    semantic names reported : {' '.join(sems) if sems else '(none)'}")
        r.w(f"    api-member-names        : {hits}")
        r.w(f"    selftest(type walk)     : {'ok' if selftest else 'FAILED'}")
        r.w(f"    input params reached    : {'ok' if inputs else 'FAILED'}")
        r.w(f"    module-annot(!\"mPos\")   : {'yes' if annot else 'no'}")
        r.check(f"{tag}: reflection walk reached type information", selftest)
        r.check(f"{tag}: reflection walk reached the input signature", inputs)
        table.append(
            (
                tag,
                str(hits),
                "ok" if selftest else "FAILED",
                "yes" if annot else "no",
                "",
            )
        )
        r.w()

    r.w("=" * 72)
    r.w("summary")
    r.w("=" * 72)
    r.w(f"{'release':<16}{'api-member-names':>18}{'selftest':>11}{'module-annot':>14}")
    for tag, hits, st, annot, note in table:
        r.w(f"{tag:<16}{hits:>18}{st:>11}{annot:>14}  {note}")
    r.w()
    r.w(f"releases measured: {len(table)}")
    r.check(
        "no release exposed an input-struct member name through the API",
        all(t[1] == "0" for t in table),
    )
    r.save()

    (HERE / "reflection-matrix.json").write_text(
        json.dumps(
            [
                {
                    "release": t[0],
                    "api_member_name_hits": t[1],
                    "selftest": t[2],
                    "module_field_annotation": t[3],
                    "note": t[4],
                }
                for t in table
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 1 if r.failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    rc = 0
    if a.all or not a.matrix:
        rc |= ground_truth()
    if a.all or a.matrix:
        rc |= matrix()
    return rc


if __name__ == "__main__":
    sys.exit(main())
