"""#5255 release history -- has any shipped DXC release ever kept the
declaration of a struct type that is only referenced as the ELEMENT TYPE of
an ARRAY-typed cbuffer member, when run through `dxr -remove-unused-globals
-remove-unused-functions`?

`triage.py bisect` cannot answer this and refuses to try (`refuse_harness_bisect`
in triage.py): the reported surface is the standalone rewriter driver `dxr.exe`
forwarding to `IDxcRewriter2`/`RewriteUnused`, and `dxc.exe` never calls it.
bisect resolves a release tag to that release's own **dxc.exe**, which would
silently answer a different question -- the same shape as #4273, #3237 and
#2923.

The rewriter lives inside **dxcompiler.dll**, which every release ships (no
release archive in the catalog ships `dxr.exe` itself, confirmed empirically
below via `optcheck`/`noopts` never needing a release dxr). So the ground-truth
`dxr.exe` (built at 89e2f98e2, the commit this batch's ground truth is pinned
to) is copied next to each release's own `dxcompiler.dll` in a scratch
directory under `.cache/rw5255`; Windows' DLL search order loads that
directory's `dxcompiler.dll` first, so the release's OWN rewriter code runs,
driven by a fixed, known-good driver.

FOUR probes per release, matching the #4273 pattern:

  repro     repro.hlsl, the reporter's exact options. InstanceDataStructType
            is used ONLY as `InstanceDataStructType mData[2]` (an array field)
            inside two cbuffers.
  control   control-scalar.hlsl, same options, same struct used as a SCALAR
            cbuffer member (`InstanceDataStructType mData;`, no array). Locally
            (ground truth), this control does NOT reproduce -- the struct
            declaration is correctly retained -- which is what isolates the
            defect to the array-typed member specifically (root-caused in
            notes.md to `Type::getAsTagDecl()` not unwrapping
            `ConstantArrayType`, in `VisitHLSLBufferDecl`,
            tools/clang/tools/libclang/dxcrewriteunused.cpp). If this control
            ever scored `repro-like` on some release, that would mean the
            release's rewriter behaves differently for the scalar case, so is
            not a fair analogue of the current build; none did.
  optcheck  `-unchanged repro.hlsl` -- does this release's rewriter accept the
            rewriter option surface at all?
  noopts    `repro.hlsl`, no options -- does this release's rewriter run at
            all? optcheck failing while noopts succeeds means the repro cannot
            be expressed on that release (invalid-probe), not that it is clean.

Scoring for `repro` and `control` is `triage.classify`, imported from
scripts/triage.py, using this issue's own match.json -- the identical code
that scores out-*.txt / variant-*.txt.

Usage:
    python measure.py             # ground truth (dxr-5255-release) only
    python measure.py --history   # every stable cached release, then ground truth
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
DB = os.path.join(SKILL, ".cache", "triage.db")
SCRATCH = os.path.join(SKILL, ".cache", "rw5255")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import triage  # noqa: E402

ISSUE = 5255
# No dxr.exe under build/Debug/bin in this ground-truth checkout (rebuilding
# it would touch the shared Debug target other batch-019 workers may be
# measuring, which this triage run must not do). build/Release/bin/dxr.exe
# and dxc.exe both self-report the same commit as the registered main-debug
# (dxc) ground truth -- "89e2f98e2" -- so it is used as-is, read-only.
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Release", "bin")
DXR = os.path.join(BUILD_BIN, "dxr.exe")

REPRO_ARGS = ["-remove-unused-functions", "-remove-unused-globals",
              "-E", "vs_main"]
PROBES = [
    ("repro", REPRO_ARGS, "repro.hlsl", True),
    ("control", REPRO_ARGS, "control-scalar.hlsl", True),
    ("optcheck", ["-unchanged"], "repro.hlsl", False),
    ("noopts", [], "repro.hlsl", False),
]


def redact(path):
    """Absolute path -> the placeholders triage.py writes in capture headers."""
    p = os.path.abspath(path).replace(os.sep, "/")
    for base, token in ((os.path.join(SKILL, ".cache"), "<cache>"),
                        (SKILL, "<triage>"), (REPO, "<repo>")):
        b = os.path.abspath(base).replace(os.sep, "/")
        if p.lower() == b.lower():
            return token
        if p.lower().startswith(b.lower() + "/"):
            return token + p[len(b):]
    return p


def releases():
    """(tag, build_date, release_bin_dir) for every STABLE cached release."""
    if not os.path.isfile(DB):
        sys.exit(f"no triage database at {DB}; run `triage.py catalog` first")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT tag, build_date, cached_path, bisectable, prerelease"
        " FROM releases ORDER BY build_date").fetchall()
    con.close()
    usable, skipped = [], []
    for tag, date, path, bisectable, pre in rows:
        if not bisectable or pre:
            skipped.append((tag, date, "prerelease" if pre
                            else "not bisectable"))
            continue
        d = os.path.dirname(path) if path else None
        if not d or not os.path.isfile(os.path.join(d, "dxcompiler.dll")):
            skipped.append((tag, date, "no cached dxcompiler.dll"))
            continue
        usable.append((tag, date, d))
    return usable, skipped


def stage(tag, release_bin):
    """Copy dxr.exe beside a release's dxcompiler.dll; return the staged exe."""
    d = os.path.join(SCRATCH, tag)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(DXR, d)
    for name in ("dxcompiler.dll", "dxil.dll"):
        src = os.path.join(release_bin, name)
        if os.path.isfile(src):
            shutil.copy2(src, d)
    return os.path.join(d, "dxr.exe")


def version_of(exe, extra=()):
    p = subprocess.run([exe, *extra, "--version"], capture_output=True,
                       text=True, errors="replace", cwd=HERE, timeout=120)
    return (p.stdout + p.stderr).strip()


def measure(label, exe, probe, extra=()):
    """Run one probe against one staged rewriter and score it."""
    name, opts, shader, scored = probe
    argv = [exe, *extra, *opts, shader]
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    text = p.stdout + p.stderr
    verdict, reason = (triage.classify(ISSUE, text, p.returncode, False,
                                       "match.json", explain=True)
                       if scored else (None, None))
    return {"label": label, "probe": name, "shader": shader,
            "cmd": redact(argv[0]) + " " + subprocess.list2cmdline(
                [redact(x) if os.path.isabs(x) else x for x in argv[1:]]),
            "exit": p.returncode, "verdict": verdict, "why": reason,
            "sha256": hashlib.sha256(
                text.encode("utf-8", "replace")).hexdigest(),
            "output": text}


def reading(rows, tag):
    """Per-release one-word reading of the four probes."""
    by = {r["probe"]: r for r in rows if r["label"] == tag}
    if by["optcheck"]["exit"] != 0 and by["noopts"]["exit"] == 0:
        return ("invalid-probe",
                "rewriter runs, but this release's option table carries no "
                "rewriter options at all, so the repro cannot be expressed here")
    if by["optcheck"]["exit"] != 0:
        return ("invalid-probe", "this release's rewriter did not run")
    return (by["repro"]["verdict"], "")


def report(rows, skipped, versions):
    out = [
        "#5255 release history -- does dxr's -remove-unused-globals ever keep",
        "the declaration of a struct used only as an array-typed cbuffer",
        "member's element type?",
        "",
        "Produced by `python measure.py --history`. Each row drives THAT",
        "RELEASE's own rewriter: the ground-truth dxr.exe driver (89e2f98e2) is",
        "copied next to that release's dxcompiler.dll in a scratch directory",
        "under .cache/rw5255, so Windows loads the release rewriter and the",
        "release's own option table sees exactly the reporter's options and",
        "nothing else.",
        "",
        "triage.py bisect cannot produce this table and refuses to try: it",
        "would substitute each release's dxc.exe, which never enters the",
        "rewriter.",
        "",
        "SCORING for `repro`/`control` is triage.classify with this issue's",
        "match.json, imported from scripts/triage.py -- the same code that",
        "scores out-*.txt/variant-*.txt. repro = InstanceDataStructType is",
        "referenced as a cbuffer array-field type AND its own struct",
        "declaration is missing from the output.",
        "",
        "PROBES (each is one dxr invocation against this release's rewriter)",
        "  repro     repro.hlsl " + " ".join(REPRO_ARGS),
        "  control   control-scalar.hlsl, same options, same struct used as a",
        "            SCALAR cbuffer member instead of an array element.",
        "  optcheck  `-unchanged repro.hlsl`: does this release accept the",
        "            rewriter option surface at all?",
        "  noopts    `repro.hlsl` alone: does this release's rewriter run at",
        "            all?",
        "",
        "  optcheck failing while noopts succeeds is what separates 'this",
        "  release predates the rewriter option set' from 'this release",
        "  rewrote it clean'.",
        "",
    ]
    tags = []
    for r in rows:
        if r["label"] not in tags:
            tags.append(r["label"])

    out += [f"{'release':>16} {'repro':>12} {'control':>12} {'optcheck':>9}"
            f" {'noopts':>7}  reading",
            f"{'-' * 16} {'-' * 12} {'-' * 12} {'-' * 9} {'-' * 7}  {'-' * 7}"]
    for tag in tags:
        by = {r["probe"]: r for r in rows if r["label"] == tag}
        verdict, why = reading(rows, tag)
        out.append(
            f"{tag:>16} {by['repro']['verdict']:>12} "
            f"{by['control']['verdict']:>12} "
            f"{('ok' if by['optcheck']['exit'] == 0 else 'exit ' + str(by['optcheck']['exit'])):>9} "
            f"{('ok' if by['noopts']['exit'] == 0 else 'exit ' + str(by['noopts']['exit'])):>7}"
            f"  {verdict}" + (f"  [{why}]" if why else ""))
    out.append("")

    out += ["VERSION reported by each staged driver (`dxr.exe --version`),",
            "which is the DLL's own version string:", ""]
    for tag in tags:
        out.append(f"  {tag:<16} {versions.get(tag, '(not recorded)')}")
    out.append("")

    out += ["SKIPPED (not in the stable-release population)", ""]
    for tag, date, why in skipped:
        out.append(f"  {tag:<32} {date or '(no build date)':<12} {why}")
    out += ["",
            "#5255's text names no prerelease, so none opts in under",
            "release-policy.json.", ""]

    out += ["", "VERBATIM. The oldest release in the population, the first",
            "release, the newest release, and ground truth.", ""]
    want = [tags[0], tags[1], tags[-2], tags[-1]] if len(tags) > 3 else tags
    seen = set()
    for tag in want:
        if tag in seen:
            continue
        seen.add(tag)
        for r in rows:
            if r["label"] == tag and r["probe"] == "repro":
                out += [f"=== {tag}  probe: repro ===", f"$ {r['cmd']}",
                        f"[exit] {r['exit']}", f"[verdict] {r['verdict']}", "",
                        r["output"].rstrip("\n"), ""]
        for r in rows:
            if r["label"] == tag and r["probe"] in ("optcheck", "noopts"):
                out += [f"=== {tag}  probe: {r['probe']} ===", f"$ {r['cmd']}",
                        f"[exit] {r['exit']}", "",
                        r["output"].rstrip("\n"), ""]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history", action="store_true",
                    help="probe every stable cached release as well")
    a = ap.parse_args()
    if not os.path.isfile(DXR):
        sys.exit(f"no dxr.exe at {redact(DXR)}; set DXC_BUILD_BIN")

    targets, skipped = (releases() if a.history else ([], []))

    rows, versions = [], {}
    for tag, _date, release_bin in targets:
        exe = stage(tag, release_bin)
        versions[tag] = version_of(exe)
        for probe in PROBES:
            rows.append(measure(tag, exe, probe))
    versions["dxr-5255-release"] = version_of(DXR)
    for probe in PROBES:
        rows.append(measure("dxr-5255-release", DXR, probe))

    for r in rows:
        print(f"{r['probe']:>9} {r['label']:>16} exit={r['exit']:<11}"
              f" {r['verdict'] or '-'}")

    with open(os.path.join(HERE, "measure.json"), "w") as f:
        json.dump({"versions": versions, "rows": rows}, f, indent=2)
    path = os.path.join(HERE, "manual-case-release-history.txt")
    with open(path, "w", newline="\n") as f:
        f.write(report(rows, skipped, versions))
    print("wrote", redact(path))


if __name__ == "__main__":
    main()
