"""#4256: run the same six modules through every stable release that ships dxv.

`bisect` cannot be used on this issue: the instrument is a harness, and bisect
would substitute each release's `dxc.exe` for it and report the inverse history
(SKILL.md, "bisect now hard-errors on a harness-as-compiler issue"). This is the
sanctioned replacement -- an explicit release matrix that holds the modules and
the question fixed and varies only the validator binary.

Coverage is bounded by packaging, not by the question: `dxv.exe` first appears
in a stable archive at v1.8.2502 (checked over every catalogued release below),
so releases older than that cannot be probed this way at all and are reported as
"no dxv in the archive" rather than silently omitted.

**Unpacked releases live in two roots**, and scanning one is how the first
version of this script got that floor wrong. The triage cache holds the tags
`triage.py` downloaded on demand; `build/tools/clang/test/dxc_releases` holds
the trees the lit release tests unpack, which `catalog --seed-from` adopts.
v1.8.2502 and v1.8.2505.1 exist **only** in the second, so a one-root walk drops
two releases that ship `dxv.exe` and reports the floor as v1.8.2505. Both roots
are searched here and reconciled through the catalog's `releases.cached_path`
column, which is the layer that knows about both (SKILL.md, "Setup").

Per-release controls are mandatory (SKILL.md): every release must accept full.ll
and reject badsig.ll and sm60.ll, or its result on the doctored modules says
nothing. Those three lines are printed for each release beside the measurement.

Run from this directory:  python release-matrix.py > manual-case-release-matrix.txt
"""

import os
import sqlite3
import subprocess
import sys
from urllib.request import pathname2url

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4256/ -> <skill>, <repo>
SKILL = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
REPO = os.path.abspath(os.path.join(SKILL, os.pardir, os.pardir, os.pardir))
RELEASE_ROOTS = [
    os.path.join(SKILL, ".cache", "compilers", "releases"),
    os.path.join(REPO, "build", "tools", "clang", "test", "dxc_releases"),
]
DB = os.path.join(SKILL, ".cache", "triage.db")

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


def catalog():
    """(tag, build_date, prerelease) for every unpacked release, oldest first.

    The catalog is the reconciliation layer for the two physical roots -- it
    records one `cached_path` per release whichever root holds it -- and it is
    also the only place the build date and the prerelease flag are recorded.
    Read-only, and opened read-only, so it is safe beside other sessions.
    """
    if not os.path.isfile(DB):
        print("[warning] no catalog at %s; falling back to a directory walk, "
              "so ordering is lexical and prereleases are unlabelled. Run "
              "`triage.py catalog --seed-from <repo>/build/tools/clang/test/"
              "dxc_releases`." % display(DB))
        return []
    con = sqlite3.connect("file:%s?mode=ro" % pathname2url(DB),
                          uri=True, timeout=60)
    try:
        rows = con.execute(
            "SELECT tag, build_date, prerelease FROM releases "
            "WHERE cached_path IS NOT NULL ORDER BY build_date").fetchall()
    finally:
        con.close()
    return rows


def release_trees():
    """tag -> unpacked directory, searching every root rather than the first."""
    trees = {}
    for root in RELEASE_ROOTS:
        if not os.path.isdir(root):
            print("[note] release root not present on this machine: %s"
                  % display(root))
            continue
        for tag in sorted(os.listdir(root)):
            path = os.path.join(root, tag)
            if os.path.isdir(path):
                trees.setdefault(tag, path)
    return trees


def find_dxv(root):
    """(chosen x64-or-any dxv.exe paths, every dxv.exe) under one release tree.

    The search is deliberately not restricted to `x64` directories: a release
    that packaged the tool elsewhere would otherwise be reported as shipping
    none, which is the same kind of under-count as scanning one root.
    """
    hits = []
    for dirpath, _, names in os.walk(root):
        if "dxv.exe" in names:
            hits.append(os.path.join(dirpath, "dxv.exe"))
    x64 = [p for p in hits if os.path.basename(os.path.dirname(p)) == "x64"]
    return sorted(x64 or hits), sorted(hits)


def main():
    trees = release_trees()
    if not trees:
        sys.exit("no unpacked releases in either root")

    ordered = [tuple(r) for r in catalog() if r[0] in trees]
    known = {tag for tag, _, _ in ordered}
    for tag in sorted(trees):
        if tag not in known:
            print("[warning] %s is unpacked but not catalogued; ordering it "
                  "last. Re-run `triage.py catalog`." % tag)
            ordered.append((tag, None, None))

    print("# %d unpacked release tree(s), found across both roots:" % len(trees))
    for root in RELEASE_ROOTS:
        print("#   %s" % display(root))
    print("# Ordering is the catalogued build date, not the tag or the publish")
    print("# date: servicing patches ship long after their snapshot.")

    ships = []
    for tag, date, prerelease in ordered:
        kind = ("not catalogued" if prerelease is None
                else "prerelease" if prerelease else "stable")
        print("\n================ %s (%s, %s) ================"
              % (tag, date or "build date unknown", kind))
        print("[tree] %s" % display(trees[tag]))
        chosen, every = find_dxv(trees[tag])
        print("[ships dxv.exe] %s%s"
              % ("yes" if every else "no",
                 " (%d arch flavour(s); using %s)"
                 % (len(every), display(chosen[0])) if every else ""))
        if not every:
            print("[skip] no dxv.exe in this release archive -- the validator "
                  "cannot be driven over a .ll module here")
            continue
        if prerelease:
            print("[skip] prerelease -- outside the stable history by policy "
                  "(SKILL.md); named here rather than silently omitted")
            continue
        ships.append(tag)
        matrix(chosen[0])

    print("\n================ coverage summary ================")
    print("# stable releases that ship dxv.exe, oldest first (%d): %s"
          % (len(ships), ", ".join(ships)))
    print("# every other catalogued release above ships no dxv.exe, so the")
    print("# measurable window starts at %s."
          % (ships[0] if ships else "<none>"))

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
