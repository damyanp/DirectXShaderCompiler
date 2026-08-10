"""#4256: run the same six modules through every stable release that ships dxv.

`bisect` cannot be used on this issue: the instrument is a harness, and bisect
would substitute each release's `dxc.exe` for it and report the inverse history
(SKILL.md, "bisect now hard-errors on a harness-as-compiler issue"). This is the
sanctioned replacement -- an explicit release matrix that holds the modules and
the question fixed and varies only the validator binary.

Coverage is bounded by packaging, not by the question: `dxv.exe` first appears
in a stable archive at v1.8.2505 (checked over every catalogued release below),
so releases older than that cannot be probed this way at all and are reported as
"no dxv in the archive" rather than silently omitted.

Per-release controls are mandatory (SKILL.md): every release must accept full.ll
and reject badsig.ll and sm60.ll, or its result on the doctored modules says
nothing. Those three lines are printed for each release beside the measurement.

Run from this directory:  python release-matrix.py > manual-case-release-matrix.txt
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4256/ -> <skill>, <repo>
SKILL = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
REPO = os.path.abspath(os.path.join(SKILL, os.pardir, os.pardir, os.pardir))
RELEASES = os.path.join(SKILL, ".cache", "compilers", "releases")

# The doctored modules, and what each one is for.
CASES = [
    ("val18-full.ll", "CONTROL, must validate: unmodified DXC output"),
    ("val18-badsig.ll", "CONTROL, must fail: storeOutput with an out-of-range sig id"),
    ("val18-sm60.ll", "CONTROL, must fail: ViewID op under shader model 6.0"),
    ("val18-nostate.ll", "SUBJECT: dx.viewIdState deleted"),
    ("val18-zerodeps.ll", "SUBJECT: state kept, every dependency bit cleared"),
    ("val18-wrongdeps.ll", "SUBJECT: state kept, dependency bits replaced with a lie"),
]


def display(path):
    p = os.path.abspath(path)
    for root, label in ((SKILL, "<triage>"), (REPO, "<repo>")):
        rel = os.path.relpath(p, root)
        if not rel.startswith(os.pardir):
            return label + "/" + rel.replace(os.sep, "/")
    return os.path.basename(p)


def run(argv, cwd=HERE):
    print("$ " + subprocess.list2cmdline([display(argv[0])] + argv[1:]))
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    text = (p.stdout + p.stderr).strip()
    if text:
        print(text)
    print("[exit] 0x%08X" % (p.returncode & 0xFFFFFFFF))
    return p.returncode, text


def main():
    if not os.path.isdir(RELEASES):
        sys.exit("no cached releases at " + display(RELEASES))

    for tag in sorted(os.listdir(RELEASES)):
        root = os.path.join(RELEASES, tag)
        if not os.path.isdir(root):
            continue
        dxvs = []
        for dirpath, _, names in os.walk(root):
            if "dxv.exe" in names and os.path.basename(dirpath) in ("x64", ""):
                dxvs.append(os.path.join(dirpath, "dxv.exe"))
        print("\n================ %s ================" % tag)
        if not dxvs:
            print("[skip] no dxv.exe in this release archive -- the validator "
                  "cannot be driven over a .ll module here")
            continue
        matrix(sorted(dxvs)[0])

    print("\n================ ground truth (main @ 13730886e) ============")
    print("# equivalence control: the same val18 set on the build the verdict")
    print("# rests on. If these lines match the default-valver captures, the")
    print("# `-validator-version 1.8` deviation did not change the answer.")
    matrix(os.path.join(REPO, "build", "Debug", "bin", "dxv.exe"))


def matrix(dxv):
    bindir = os.path.dirname(dxv)
    dxc = os.path.join(bindir, "dxc.exe")
    if os.path.isfile(dxc):
        run([dxc, "--version"])
    print("[dxil.dll beside dxv] %s"
          % ("yes" if os.path.isfile(os.path.join(bindir, "dxil.dll"))
             else "no"))
    print("[DXC_DXIL_DLL_PATH] %s"
          % (os.environ.get("DXC_DXIL_DLL_PATH") or "<unset>"))
    for module, why in CASES:
        print("\n---- %s: %s" % (module, why))
        run([dxv, module])


if __name__ == "__main__":
    main()
