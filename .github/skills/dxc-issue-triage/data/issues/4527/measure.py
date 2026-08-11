"""Issue 4527: release matrix and container-level evidence.

Two things `triage.py run`/`bisect` cannot answer on their own, both needed here:

1. **History below the mesh-shader barrier.** `repro.hlsl` is the reporter's file verbatim and
   also contains a mesh-shader entry point, so v1.4.1907 rejects it with
   `unknown type name 'indices'` -- a feature-absence rejection that `bisect` correctly
   classifies as an unprobeable release rather than a result. `repro-min.hlsl` restates the
   construct without mesh syntax. Running it over every stable release settles whether
   v1.4.1907 is unprobeable because of the *construct* or only because of the *file*.

2. **The reported symptom is about the container, not the diagnostics.** The report is
   "compiles with no errors, and D3D12 then rejects the bytecode as unsigned". Whether a
   container was produced, whether its digest is zero, and whether its DXIL validates are all
   facts about a file on disk that never reach stdout.

3. **Where the array's definition ends up.** The validator's wording ("External declaration
   ... is unused") reads like the initializer was dropped during serialization. Disassembling
   the container with `-dumpbin` and printing its globals tests that reading against a control.

Every command is printed exactly as executed (`subprocess.list2cmdline`), and every path is
run through `triage.redact_paths` so nothing machine-specific lands in a committed file.
Re-run this script to re-derive both captures:

    python measure.py

Self-consistency: the container reader asserts the DXBC magic and prints
`4527-SELFTEST:` lines saying what it saw. A reader that silently returns "nothing here"
would otherwise be indistinguishable from a real absence -- the whole point of the
signed/unsigned measurement is an absence, so the reader has to be able to fail loudly.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def skill_root(start):
    d = start
    while True:
        if os.path.exists(os.path.join(d, "scripts", "triage.py")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit("could not locate the triage skill root above " + start)
        d = parent


ROOT = skill_root(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import triage                                                   # noqa: E402

SCRATCH = os.path.join(HERE, "scratch")
DXV = os.path.join(triage.REPO_ROOT, "build", "Debug", "bin", "dxv.exe")


def red(text):
    return triage.redact_paths(text)


def run(argv, cwd=HERE):
    """Execute argv, returning (echo, exit status, combined output)."""
    echo = "$ " + red(subprocess.list2cmdline(argv))
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       errors="replace")
    out = red((p.stdout or "") + (p.stderr or "")).strip()
    return echo, p.returncode, out


def status(rc):
    return f"0x{rc & 0xFFFFFFFF:08X}"


def container_facts(path):
    """Describe a DXIL container: magic, size, and the 16-byte header digest.

    The digest is written by the signing step. All-zero means the container was never
    signed, which is exactly what the D3D12 message "Pixel Shader is unsigned" reports.
    """
    if not os.path.exists(path):
        return ["4527-SELFTEST: reader ran, no container file was produced"]
    blob = open(path, "rb").read()
    if len(blob) < 20:
        return [f"4527-SELFTEST: PARSE-WARNING: {len(blob)} bytes, too short to be a container"]
    magic = blob[:4].decode("ascii", "replace")
    if magic != "DXBC":
        return [f"4527-SELFTEST: PARSE-WARNING: magic {magic!r}, not a DXBC container"]
    digest = blob[4:20].hex()
    signed = "UNSIGNED (digest is all zero)" if set(digest) == {"0"} else "signed"
    return [f"4527-SELFTEST: DXBC container, {len(blob)} bytes, digest={digest} -> {signed}"]


def dxv(path, lines):
    if not os.path.exists(path):
        return
    echo, rc, out = run([DXV, path])
    lines.append(echo)
    lines.append(f"[exit] {status(rc)}")
    lines.extend("    " + ln for ln in out.splitlines())


def stable_releases():
    rows = triage.con().execute(
        "SELECT tag, build_date, cached_path FROM releases "
        "WHERE prerelease = 0 AND cached_path IS NOT NULL "
        "ORDER BY build_date").fetchall()
    return [(r["tag"], r["build_date"], r["cached_path"]) for r in rows]


def ground_truth():
    row = triage.con().execute(
        "SELECT exe_path FROM compilers WHERE id = 'main-debug'").fetchone()
    return row["exe_path"]


def probe(exe, label, source, extra, lines, keep=False):
    obj = os.path.join(SCRATCH, f"{label}.dxil")
    if os.path.exists(obj):
        os.remove(obj)
    argv = [exe, "-T", "ps_6_0", "-E", "mainPS", source] + extra + ["-Fo", obj]
    echo, rc, out = run(argv)
    lines.append(echo)
    lines.append(f"[exit] {status(rc)}")
    for ln in out.splitlines():
        lines.append("    " + ln)
    lines.extend("    " + ln for ln in container_facts(obj))
    dxv(obj, lines)
    if not keep and os.path.exists(obj):
        os.remove(obj)
    return rc


def version_of(exe):
    _, _, out = run([exe, "--version"])
    return out.splitlines()[0] if out else "(no version output)"


def release_matrix():
    lines = [
        "# issue 4527 -- release matrix over repro-min.hlsl",
        "#",
        "# Generated by measure.py, which is committed beside this file. Every command is",
        "# echoed exactly as executed. Re-run `python measure.py` to re-derive it.",
        "#",
        "# Why this exists: bisect runs the reporter's file (repro.hlsl), whose mesh-shader",
        "# entry point v1.4.1907 cannot parse, so that release is unprobeable there. This",
        "# matrix runs the same construct without mesh syntax, which is the feature-presence",
        "# control that says whether v1.4.1907 is unprobeable for the construct too.",
        "#",
        "# Default flags: validation on, so this is what a stock toolchain does.",
        "#",
        "# `[version]` reads `dxc --version`; releases older than v1.8 predate that option and",
        "# answer `Unknown argument`, so for those the tag and build date identify the binary.",
        "",
    ]
    for tag, date, exe in stable_releases():
        lines.append(f"=== {tag}  (build {date})")
        lines.append(f"[version] {version_of(exe)}")
        probe(exe, f"min-{tag}", "repro-min.hlsl", [], lines)
        lines.append("")
    lines.append("=== main-debug (ground truth)")
    gt = ground_truth()
    lines.append(f"[version] {version_of(gt)}")
    probe(gt, "min-main-debug", "repro-min.hlsl", [], lines)
    lines.append("")
    lines.append("=== main-debug (ground truth), CONTROL: the same command on a shader whose")
    lines.append("=== static array is declared at global scope instead")
    probe(gt, "min-control", "control-global-scope-static.hlsl", [], lines)
    lines.append("")
    return "\n".join(lines) + "\n"


def unsigned_container():
    """The reported symptom -- silent success, unsigned container -- and what produces it."""
    gt = ground_truth()
    rel = dict((t, e) for t, _, e in stable_releases()).get("v1.7.2207")
    lines = [
        "# issue 4527 -- container-level evidence",
        "#",
        "# Generated by measure.py (committed beside this file); every command is echoed",
        "# exactly as executed. Re-run `python measure.py` to re-derive it.",
        "#",
        "# The report is: the shader compiles with no errors, and D3D12 then rejects the",
        "# bytecode with CREATEPIXELSHADER_INVALIDSHADERBYTECODE, 'Pixel Shader is unsigned'.",
        "# Under default flags no build I can run compiles it at all, so this file measures",
        "# which configurations do produce a container, and what is in it.",
        "#",
        "# READ THE CONTROL BEFORE THE RESULT: -Vd suppresses validation, and every -Vd",
        "# container measured below comes back with an all-zero digest -- the known-good",
        "# shader's as well as the failing one's. 'Unsigned' is therefore not by itself",
        "# evidence of this bug. What separates the two is whether the DXIL inside validates.",
        "",
        "=== ground truth, default flags (validation on)",
    ]
    lines.append(f"[version] {version_of(gt)}")
    probe(gt, "vd-gt-default", "repro-min.hlsl", [], lines)
    lines.append("")

    lines.append("=== ground truth, -Vd (validation disabled)")
    probe(gt, "vd-gt", "repro-min.hlsl", ["-Vd"], lines)
    lines.append("")

    lines.append("=== CONTROL: ground truth, -Vd, on a shader with no static local in a member")
    lines.append("=== function. Also unsigned (that is what -Vd does) but its DXIL validates.")
    probe(gt, "vd-control", "control-global-scope-static.hlsl", ["-Vd"], lines)
    lines.append("")

    if rel:
        lines.append("=== v1.7.2207 (2022-07-18, the stable release nearest the report's build")
        lines.append("=== date of 2022-06-22), default flags")
        lines.append(f"[version] {version_of(rel)}")
        probe(rel, "vd-rel-default", "repro-min.hlsl", [], lines)
        lines.append("")
        lines.append("=== v1.7.2207, -Vd")
        probe(rel, "vd-rel", "repro-min.hlsl", ["-Vd"], lines)
        lines.append("")

        # The other way a container can come out unsigned: dxil.dll missing entirely.
        nodxil = os.path.join(SCRATCH, "nodxil")
        os.makedirs(nodxil, exist_ok=True)
        import shutil
        srcdir = os.path.dirname(rel)
        for name in ("dxc.exe", "dxcompiler.dll"):
            shutil.copy2(os.path.join(srcdir, name), nodxil)
        lines.append("=== v1.7.2207 with dxil.dll deliberately absent: dxc.exe and")
        lines.append("=== dxcompiler.dll copied to a directory holding nothing else, so the")
        lines.append("=== external validator/signer cannot be loaded.")
        # Not a shell command: measure.py does this with shutil.copy2, and printing it with a
        # `$` prompt would assert that a command line ran which did not.
        lines.append("[setup] shutil.copy2 of " + red(os.path.join(srcdir, "dxc.exe"))
                     + " and " + red(os.path.join(srcdir, "dxcompiler.dll"))
                     + " into " + red(nodxil))
        lines.append("[dir] " + ", ".join(sorted(os.listdir(nodxil))))
        probe(os.path.join(nodxil, "dxc.exe"), "nodxil", "repro-min.hlsl", [], lines)
        lines.append("")
        shutil.rmtree(nodxil, ignore_errors=True)
    return "\n".join(lines) + "\n"


def globals_in_container(exe, label, source, lines):
    """Compile to a container with -Vd, then read the globals back out of it.

    `-dumpbin` disassembles the DXIL *inside the container*, i.e. after serialization,
    which is the only way to check whether the array's initializer survives that far.
    """
    obj = os.path.join(SCRATCH, f"{label}.dxil")
    if os.path.exists(obj):
        os.remove(obj)
    echo, rc, out = run([exe, "-T", "ps_6_0", "-E", "mainPS", source, "-Vd", "-Fo", obj])
    lines.append(echo)
    lines.append(f"[exit] {status(rc)}")
    lines.extend("    " + ln for ln in out.splitlines())
    lines.extend("    " + ln for ln in container_facts(obj))
    if not os.path.exists(obj):
        lines.append("    4527-SELFTEST: no container, nothing to disassemble")
        return
    echo, rc, out = run([exe, "-dumpbin", obj])
    lines.append(echo)
    lines.append(f"[exit] {status(rc)}")
    all_lines = out.splitlines()
    picked = [ln for ln in all_lines if ln.startswith(("@", "$"))]
    lines.append(f"    4527-SELFTEST: disassembly is {len(all_lines)} lines; "
                 f"{len(picked)} of them declare a module-scope global or comdat "
                 f"(line starts with '@' or '$'); those {len(picked)} are shown in full")
    lines.extend("    " + ln for ln in picked)
    os.remove(obj)


def container_symbol():
    """Does the array's definition survive into the container, and with what linkage?"""
    gt = ground_truth()
    lines = [
        "# issue 4527 -- the array's linkage, read back out of the container",
        "#",
        "# Generated by measure.py (committed beside this file); every command is echoed",
        "# exactly as executed. Re-run `python measure.py` to re-derive it.",
        "#",
        "# The validator calls the array an 'External declaration', which reads like the",
        "# initializer was dropped somewhere. This file tests that reading directly: compile",
        "# with -Vd so a container is produced at all, then disassemble the container with",
        "# -dumpbin and print every module-scope global it contains.",
        "#",
        "# CONTROL: the same two commands on a shader whose array is at global scope, which",
        "# compiles and validates. It is the linkage word that differs between the two, and",
        "# `dxilutil::IsStaticGlobal` (lib/DXIL/DxilUtil.cpp) tests exactly that word.",
        "",
        "=== the repro: static const array declared inside a member function",
    ]
    lines.append(f"[version] {version_of(gt)}")
    globals_in_container(gt, "sym-repro", "repro-min.hlsl", lines)
    lines.append("")
    lines.append("=== CONTROL: the same array declared at global scope")
    globals_in_container(gt, "sym-control", "control-global-scope-static.hlsl", lines)
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    for name, text in (("manual-case-release-matrix.txt", release_matrix()),
                       ("manual-case-unsigned-container.txt", unsigned_container()),
                       ("manual-case-container-symbol.txt", container_symbol())):
        with open(os.path.join(HERE, name), "w", newline="\n") as f:
            f.write(text)
        print("wrote", name)
    # The containers are derived; the text captures above are the evidence.
    import shutil
    shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()
