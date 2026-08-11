"""Release matrix for #4605.

`triage.py run --shader` only retargets the registered ground-truth compiler, so
the feature-presence control cannot be run per release through the tool. This
harness holds the shaders fixed and varies the compiler executable, taking each
release's `dxc.exe` from the catalog's `releases.cached_path` column.

Why it exists: the repro's symptom is a *diagnostic*, and templated
`Load<T>`/`Store<T>` on byte-address buffers is a feature that arrived at a
particular point in time. A release that predates the feature rejects the ROV
repro too -- with the *same* message -- so the primary probe would score
`repro` on a build that could not have answered the question. The only thing
that separates "the ROV type is the problem" from "this build has no templated
byte-address accessors at all" is running the RWByteAddressBuffer control on the
same binary. That is what this file measures.

Every command is echoed with subprocess.list2cmdline(argv), i.e. exactly what
was executed, and every case is scored with triage.classify -- the same
function that scores committed captures -- so nothing here is a transcription.
A self-check prints a loud marker if a version string or an expected case is
missing, so "nothing was measured" cannot be mistaken for "nothing was wrong".

    python measure-release-matrix.py > manual-case-release-matrix.txt
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scripts"))
sys.path.insert(0, SCRIPTS)
import triage  # noqa: E402

ISSUE = 4605
ARGS = ["-T", "ps_6_0"]

# label, shader, predicate, what the control asserts
CASES = [
    ("repro", "repro.hlsl", "match.json", "match",
     "ROV templated Load -- the reported symptom"),
    ("control-rwbab", "control-rwbab.hlsl", "match.json", "no-match",
     "FEATURE PRESENCE: same shader on RWByteAddressBuffer"),
    ("control-rov-untemplated", "control-rov-untemplated.hlsl", "match.json",
     "no-match", "ROV type usable at all, untemplated Load"),
    ("store-rov", "store-rov.hlsl", "match-store.json", "match",
     "ROV templated Store"),
    ("control-rwbab-store", "control-rwbab-store.hlsl", "match-store.json",
     "no-match", "FEATURE PRESENCE: templated Store on RWByteAddressBuffer"),
]


def compilers():
    """Ground truth first, then every stable release with a cached dxc."""
    out = []
    c = triage.con()
    row = c.execute("SELECT id, exe_path FROM compilers WHERE id=?",
                    ("main-debug",)).fetchone()
    if row:
        out.append((row["id"], row["exe_path"], "ground truth"))
    for r in c.execute(
            "SELECT tag, cached_path FROM releases "
            "WHERE bisectable=1 AND prerelease=0 AND cached_path IS NOT NULL "
            "ORDER BY build_date"):
        out.append((r["tag"], r["cached_path"], "release"))
    c.close()
    return out


def run(exe, argv):
    p = subprocess.run([exe] + argv, cwd=HERE, capture_output=True, text=True)
    return p.returncode, triage.redact_paths((p.stdout or "") + (p.stderr or ""))


def first_diag(text):
    for line in text.splitlines():
        if re.search(r"\b(error|fatal error|warning)\b\s*:", line):
            return line.strip()
    return ""


def ident_of(text):
    """`!llvm.ident` from a successful compile: the binary's own self-report.

    Releases before v1.6.2112 reject `--version` outright, so the tag on the
    cache directory would be the only thing attributing those results to a
    compiler. The DXIL the control emits carries a producer string, which is
    attribution from inside the artifact rather than from the filename.

    It is only *sometimes* attribution: v1.5.2010 through v1.7.2207 emit the
    generic upstream `clang version 3.7 (tags/RELEASE_370/final)` and no DXC
    build identity at all. Report exactly what was found and let the caller
    say which kind it is, rather than silently presenting one as the other.
    """
    m = re.search(r"^!llvm\.ident = !\{!(\d+)\}", text, re.MULTILINE)
    if not m:
        return ""
    n = m.group(1)
    m2 = re.search(r'^!%s = !\{!"([^"]*)"\}' % n, text, re.MULTILINE)
    return m2.group(1) if m2 else ""


def main():
    rows = []
    problems = []
    for cid, exe, kind in compilers():
        if not exe or not os.path.isfile(exe):
            problems.append(f"{cid}: executable not found -- NOT MEASURED")
            continue
        vrc, vtext = run(exe, ["--version"])
        version = " | ".join(l.strip() for l in vtext.splitlines() if l.strip())
        if not version or "Unknown argument" in version:
            version = f"<--version rejected by this build: {version or 'no output'}>"
        print(f"=== {cid}  ({kind})")
        print(f"    exe:     {triage.display_exe(exe)}")
        print(f"    version: {version}")
        seen = 0
        ident = ""
        for label, shader, mf, expect, why in CASES:
            argv = ARGS + [shader]
            rc, text = run(exe, argv)
            if not ident:
                ident = ident_of(text)
            verdict = triage.classify(ISSUE, text, rc, False, mf)
            ok = ((expect == "match" and verdict == "repro")
                  or (expect == "no-match" and verdict == "no-repro"))
            diag = first_diag(text)
            print(f"    $ {subprocess.list2cmdline([os.path.basename(exe)] + argv)}")
            print(f"      predicate={mf} exit=0x{rc & 0xFFFFFFFF:08X} "
                  f"verdict={verdict} expect={expect} "
                  f"{'OK' if ok else 'UNEXPECTED'}")
            print(f"      first diagnostic: {diag or '<none; compile succeeded>'}")
            if not ok:
                problems.append(f"{cid}/{label}: expected {expect}, got {verdict}")
            rows.append((cid, label, verdict, ok, diag))
            seen += 1
        print(f"    !llvm.ident from this run's DXIL: {ident or '<none>'}")
        if not ident:
            problems.append(f"{cid}: MATRIX-4605 PARSE-WARNING: no !llvm.ident "
                            f"in any successful compile; this binary is "
                            f"attributed only by its cache path")
        elif not re.search(r"dxc", ident, re.IGNORECASE):
            print(f"      note: generic upstream ident, no DXC build identity; "
                  f"this binary is attributed by its catalog cached_path")
        if seen != len(CASES):
            problems.append(f"{cid}: MATRIX-4605 PARSE-WARNING: only {seen} of "
                            f"{len(CASES)} cases ran")
        print()

    print("=== summary: repro vs feature-presence control, per compiler")
    print(f"{'compiler':<16} {'ROV Load':<10} {'RW Load':<10} "
          f"{'ROV Store':<10} {'RW Store':<10}")
    by = {}
    for cid, label, verdict, ok, diag in rows:
        by.setdefault(cid, {})[label] = verdict
    for cid in by:
        d = by[cid]
        print(f"{cid:<16} {d.get('repro',''):<10} "
              f"{d.get('control-rwbab',''):<10} "
              f"{d.get('store-rov',''):<10} "
              f"{d.get('control-rwbab-store',''):<10}")

    print()
    print("=== self-check")
    print(f"compilers measured: {len(by)}; cases per compiler: {len(CASES)}; "
          f"rows: {len(rows)}")
    if problems:
        print(f"MATRIX-4605 PARSE-WARNING: {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
    else:
        print("matrix-selftest=pass: every compiler ran every case and every "
              "case matched its declared expectation")


if __name__ == "__main__":
    main()
