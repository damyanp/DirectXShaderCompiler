"""Measure the DXIL *linker* half of #3439.

`dxl` is a second executable, so this case is a two-tool pipeline and cannot be
expressed as a `cmd.txt` line -- `triage.py run` drives exactly one dxc
invocation. This script drives it instead, echoing every command it runs with
`subprocess.list2cmdline` so the committed capture is re-derivable rather than
transcribed (SKILL.md step 11).

Usage, from this directory:

    python measure-link.py                 # ground truth, writes manual-case-link.txt
    python measure-link.py --history       # every cached stable release too

No release package ships `dxl.exe` -- they contain only dxc.exe, dxv.exe,
dxcompiler.dll and dxil.dll -- so a release history cannot be taken by
substituting the driver. `--history` therefore uses the #3237 release-matrix
pattern instead: the locally built dxl.exe and dxc.exe are copied next to each
release's dxcompiler.dll, which Windows' exe-directory-first DLL search makes
that release's compiler and linker implementation. What varies across rows is
the DLL, which is where IDxcLinker actually lives; the drivers are held fixed.

The compiler directory is taken from the environment / --bin so no absolute
machine path is baked in.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
DEFAULT_BIN = os.path.join(REPO, "build", "Debug", "bin")
RELEASES = os.path.join(SKILL, ".cache", "compilers", "releases")
# `catalog --seed-from` adopts the release trees the DXC test infrastructure
# already downloaded, and several tags live only there. Both roots are searched
# so the matrix covers the same 20 stable releases `triage.py bisect` visits.
SEED_RELEASES = os.path.join(REPO, "build", "tools", "clang", "test",
                             "dxc_releases")
# `triage.py bisect` excludes prereleases from the stable sequence by policy,
# and this issue names none, so they are reported but kept out of the headline
# population count.
PRERELEASES = {"v1.5.2003", "v1.8.2306-preview", "v1.8.2405-mesh-nodes-preview",
               "v1.10.2605.2", "v1.10.2605.24"}
# Scratch lives under the issue directory, never in the system temp directory:
# a committed capture must not carry a user-profile path, and the gate in
# scripts/check_paths.py rejects one. Removed again before the script exits.
SCRATCH = os.path.join(HERE, "scratch-matrix")

# Clause 2 of match.json: an MSVC-mangled FUNCTION symbol.
MANGLED_FN = re.compile(
    r"\?[A-Za-z_][A-Za-z0-9_]*(?:@[A-Za-z_][A-Za-z0-9_]*)*@@[A-Z][A-Z0-9]")


def redact(s):
    for root, token in ((SCRATCH, "<scratch>"), (REPO, "<repo>")):
        s = s.replace(root, token).replace(root.replace("\\", "/"), token)
    return s


def run(argv, out):
    out.write("$ " + redact(subprocess.list2cmdline(argv)) + "\n")
    try:
        p = subprocess.run(argv, capture_output=True, text=True, cwd=HERE,
                           timeout=300)
    except FileNotFoundError:
        out.write("[exit] tool not found\n\n")
        return None, ""
    txt = (p.stdout or "") + (p.stderr or "")
    out.write(f"[exit] 0x{p.returncode & 0xFFFFFFFF:08X}\n")
    if txt.strip():
        out.write(redact(txt.rstrip()) + "\n")
    out.write("\n")
    return p.returncode, txt


def one_build(label, bindir, out, expect_local_version=True):
    dxc = os.path.join(bindir, "dxc.exe")
    dxl = os.path.join(bindir, "dxl.exe")
    out.write(f"----- {label} -----\n")
    if not os.path.isfile(dxc) or not os.path.isfile(dxl):
        out.write("dxc.exe or dxl.exe missing from this build; not probeable\n\n")
        return label, "no-dxl"
    _, ver = run([dxc, "--version"], out)
    # Self-consistency line. A release row is only evidence about that release
    # if the version string stopped being the local build's -- otherwise the
    # DLL substitution silently did not take and both arms report the same
    # thing for the same reason (SKILL.md: "a control cannot catch a broken
    # reader").
    if not expect_local_version and "triage" in ver:
        out.write("SUBSTITUTION-WARNING: dxc --version still reports the local "
                  "build, so this row did NOT run the release DLL; INVALID PROBE\n\n")
        return label, "invalid-probe"
    obj = f"link-{label}.dxil"
    rc, txt = run([dxc, "-T", "lib_6_3", "case-link-undef.hlsl", "-Fo", obj], out)
    if rc != 0:
        # Same rule for the compile step: try the older `/Fo` spelling before
        # concluding the release cannot express the input.
        out.write("compile failed; retrying with the '/Fo' spelling before "
                  "demoting this row\n")
        rc, txt = run([dxc, "-T", "lib_6_3", "case-link-undef.hlsl", "/Fo", obj],
                      out)
    if rc != 0:
        out.write("library did not compile on this build; INVALID PROBE\n\n")
        return label, "invalid-probe"
    rc, txt = run([dxl, "-T", "ps_6_3", "-E", "main", obj,
                   "-Fo", f"linked-{label}.dxil"], out)
    if "Cannot find definition of function" not in txt:
        # SKILL.md: an `Unknown argument` demotion is not evidence until
        # spelling variants have been tried, and the retry must not be keyed to
        # the *message*, only to the anchor being absent -- v1.4.1907's linker
        # rejects `-Fo` and does not always say so, so a message-keyed retry
        # silently skips it and demotes a release that in fact reproduces.
        out.write("anchor absent; retrying the link step with the '/Fo' "
                  "spelling before demoting this row\n")
        rc, txt = run([dxl, "-T", "ps_6_3", "-E", "main", obj,
                       "/Fo", f"linked-{label}.dxil"], out)
    m = MANGLED_FN.search(txt)
    anchored = "Cannot find definition of function" in txt
    if not anchored:
        out.write("anchor 'Cannot find definition of function' ABSENT; "
                  "INVALID PROBE -- this build did not reach the linker "
                  "diagnostic under test\n\n")
        return label, "invalid-probe"
    verdict = "mangled" if m else "readable"
    out.write(f"anchor=present  mangled-function-name={m.group(0) if m else 'NONE'}"
              f"  -> {verdict}\n\n")
    for f in (obj, f"linked-{label}.dxil"):
        if os.path.isfile(os.path.join(HERE, f)):
            os.remove(os.path.join(HERE, f))
    return label, verdict


def matrix_row(tag, localbin, dlldir, out):
    """One release row: local drivers, that release's dxcompiler.dll.

    Windows searches the executable's own directory before anything else, so
    copying dxc.exe/dxl.exe into a scratch directory alongside a release DLL
    makes them run that release's compiler and linker. `dxc --version` is
    printed for every row and it reports the DLL, not the driver -- that line
    is the proof the substitution took, and a row whose version still says the
    local build is not evidence about that release.
    """
    out.write(f"===== {tag} (release matrix: local drivers + {tag} dxcompiler.dll) =====\n")
    scratch = os.path.join(SCRATCH, tag)
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch, exist_ok=True)
    try:
        for exe in ("dxc.exe", "dxl.exe"):
            shutil.copy2(os.path.join(localbin, exe), scratch)
        for dll in os.listdir(dlldir):
            if dll.lower().endswith(".dll"):
                shutil.copy2(os.path.join(dlldir, dll), scratch)
        return one_build(tag, scratch, out, expect_local_version=False)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def discover_releases():
    """Map tag -> directory holding that release's dxcompiler.dll.

    Both cache roots are searched. The seed root nests one level deeper
    (`<tag>/<asset-name>/bin/x64`), so the DLL is located by walking rather
    than by assuming a fixed shape.
    """
    found = {}
    for root in (RELEASES, SEED_RELEASES):
        if not os.path.isdir(root):
            continue
        for tag in os.listdir(root):
            if tag in found:
                continue
            base = os.path.join(root, tag)
            if not os.path.isdir(base):
                continue
            hit = None
            for dirpath, _, files in os.walk(base):
                if "dxcompiler.dll" in files and os.sep + "x64" in dirpath + os.sep:
                    hit = dirpath
                    break
                if "dxcompiler.dll" in files and hit is None:
                    hit = dirpath
            if hit:
                found[tag] = hit
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default=os.environ.get("DXC_BIN", DEFAULT_BIN))
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--out", default="manual-case-link.txt")
    a = ap.parse_args()

    out = io.StringIO()
    out.write("# #3439 -- the DXIL linker half, driven by measure-link.py\n")
    out.write("# Every command below is echoed by the script that ran it.\n")
    out.write("# 'mangled' means the linker's own error named the function\n")
    out.write("# with its MSVC-mangled symbol rather than its HLSL name.\n")
    out.write("#\n")
    out.write("# No release ships dxl.exe, so release rows are a RELEASE MATRIX:\n")
    out.write("# the local dxc.exe/dxl.exe drivers are held fixed beside each\n")
    out.write("# release's own dxcompiler.dll, which is the component that\n")
    out.write("# implements IDxcLinker and emits the message under test.\n")
    out.write("# Rows tagged (prerelease) are outside the stable sequence and\n")
    out.write("# outside the headline population count, per SKILL.md step 6.\n\n")

    out.write("===== ground truth =====\n")
    results = [one_build("main-debug", a.bin, out)]
    if a.history:
        releases = discover_releases()
        if not releases:
            out.write("no cached releases\n")
        for tag in sorted(releases):
            results.append(matrix_row(tag, a.bin, releases[tag], out))

    out.write("===== summary =====\n")
    for label, verdict in results:
        pre = " (prerelease)" if label in PRERELEASES else ""
        out.write(f"{label:16s} {verdict}{pre}\n")
    stable = [v for l, v in results
              if l not in PRERELEASES and l != "main-debug"]
    out.write(f"\nstable releases probed: {len(stable)}; "
              f"mangled: {stable.count('mangled')}; "
              f"readable: {stable.count('readable')}; "
              f"invalid-probe: {stable.count('invalid-probe')}\n")

    path = os.path.join(HERE, a.out)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out.getvalue())
    shutil.rmtree(SCRATCH, ignore_errors=True)
    sys.stdout.write(out.getvalue())


if __name__ == "__main__":
    main()
