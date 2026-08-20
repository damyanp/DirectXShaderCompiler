"""#5290 release history -- across every shipped DXC release, does `dxr
-remove-unused-functions -remove-unused-globals -E ps_main` ever keep the
declaration of a struct type that is referenced ONLY by (a) the entry point's
own otherwise-unread parameter, or (b) a local variable's declaration/cast,
when neither is ever subsequently read via a DeclRefExpr?

`triage.py bisect` cannot answer this and refuses to try (`refuse_harness_bisect`
in triage.py): the reported surface is the standalone rewriter driver
`dxr.exe` forwarding to `IDxcRewriter2`/`RewriteUnused`, and `dxc.exe` never
calls it -- confirmed for this issue in variant-dxc-rejects-rewrite-flags-
main-debug.txt, and independently in #5255 (same batch). bisect resolves a
release tag to that release's own **dxc.exe**, which would silently answer a
different question -- the same shape as #4273, #5255, #3237 and #2923.

The rewriter lives inside dxcompiler.dll, which every release ships. So the
ground-truth dxr.exe (built at 89e2f98e2, this batch's assigned commit) is
copied next to each release's own dxcompiler.dll in a scratch directory under
`.cache/rw5290`; Windows' DLL search order then loads that directory's
dxcompiler.dll first, so the release's OWN rewriter code runs, driven by a
fixed, known-good driver. Same staging pattern as #4273 and #5255.

SIX probes per release:

  ask1        repro.hlsl, the reporter's exact options. VS_OUTPUT types
              ps_main's own parameter, which is never read in the body.
  ask1-ctrl   control-param-used.hlsl, identical shape but the parameter IS
              read (`return input.color;`). Should NOT reproduce -- isolates
              the trigger to the parameter being itself unused.
  ask2        repro2.hlsl, the second comment's shape: a local variable
              `Material mtl = (Material)0;` inside ps_main, never read
              afterwards.
  ask2-ctrl   control-local-used.hlsl, identical shape but `mtl` IS read
              afterwards (`return mtl.colors[0].r;`). Should NOT reproduce.
  optcheck    `-unchanged repro.hlsl` -- does this release's rewriter accept
              the rewriter option surface at all?
  noopts      `repro.hlsl`, no options -- does this release's rewriter run at
              all? optcheck failing while noopts succeeds means the repro
              cannot be expressed on that release (invalid-probe).

Scoring is triage.classify, imported from scripts/triage.py, using this
issue's own match.json (ask1/ask1-ctrl) and match-nested.json (ask2/ask2-ctrl)
-- the identical code that scores out-*.txt / variant-*.txt.

Usage:
    python measure.py             # ground truth (dxr-5290-release) only
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
SCRATCH = os.path.join(SKILL, ".cache", "rw5290")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import triage  # noqa: E402

ISSUE = 5290
# No dxr.exe under build/Debug/bin in this checkout (rebuilding it would touch
# the shared Debug target other batch-019 workers may be measuring, which
# this triage run must not do). build/Release/bin/dxr.exe and dxc.exe both
# self-report the same commit as the registered main-debug (dxc) ground
# truth -- "89e2f98e2" -- so it is used as-is, read-only. Same binary #5255
# used in this batch (registered there as dxr-5255-release).
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Release", "bin")
DXR = os.path.join(BUILD_BIN, "dxr.exe")

REPRO_ARGS = ["-remove-unused-functions", "-remove-unused-globals",
              "-E", "ps_main"]
PROBES = [
    ("ask1", REPRO_ARGS, "repro.hlsl", "match.json"),
    ("ask1-ctrl", REPRO_ARGS, "control-param-used.hlsl", "match.json"),
    ("ask2", REPRO_ARGS, "repro2.hlsl", "match-nested.json"),
    ("ask2-ctrl", REPRO_ARGS, "control-local-used.hlsl", "match-nested.json"),
    ("optcheck", ["-unchanged"], "repro.hlsl", None),
    ("noopts", [], "repro.hlsl", None),
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


def measure(label, exe, probe):
    """Run one probe against one staged rewriter and score it."""
    name, opts, shader, match_file = probe
    argv = [exe, *opts, shader]
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    text = p.stdout + p.stderr
    verdict, reason = (triage.classify(ISSUE, text, p.returncode, False,
                                       match_file, explain=True)
                       if match_file else (None, None))
    return {"label": label, "probe": name, "shader": shader,
            "match_file": match_file,
            "cmd": redact(argv[0]) + " " + subprocess.list2cmdline(
                [redact(x) if os.path.isabs(x) else x for x in argv[1:]]),
            "exit": p.returncode, "verdict": verdict, "why": reason,
            "sha256": hashlib.sha256(
                text.encode("utf-8", "replace")).hexdigest(),
            "output": text}


def reading(rows, tag):
    """Per-release one-word readings for ask1 and ask2."""
    by = {r["probe"]: r for r in rows if r["label"] == tag}
    if by["optcheck"]["exit"] != 0 and by["noopts"]["exit"] == 0:
        return ("invalid-probe", "invalid-probe",
                "rewriter runs, but this release's option table carries no "
                "rewriter options at all, so the repro cannot be expressed here")
    if by["optcheck"]["exit"] != 0:
        return ("invalid-probe", "invalid-probe",
                "this release's rewriter did not run")
    return (by["ask1"]["verdict"], by["ask2"]["verdict"], "")


def report(rows, skipped, versions):
    out = [
        "#5290 release history -- does dxr's -remove-unused-globals ever keep",
        "a struct declaration referenced only by the entry point's own unused",
        "parameter (ask 1) or by an unread local variable's cast (ask 2)?",
        "",
        "Produced by `python measure.py --history`. Each row drives THAT",
        "RELEASE's own rewriter: the ground-truth dxr.exe driver (89e2f98e2) is",
        "copied next to that release's dxcompiler.dll in a scratch directory",
        "under .cache/rw5290, so Windows loads the release rewriter and the",
        "release's own option table sees exactly the reporter's options and",
        "nothing else.",
        "",
        "triage.py bisect cannot produce this table and refuses to try: it",
        "would substitute each release's dxc.exe, which never enters the",
        "rewriter.",
        "",
        "SCORING for ask1/ask1-ctrl uses match.json; ask2/ask2-ctrl uses",
        "match-nested.json; both via triage.classify, imported from",
        "scripts/triage.py -- the same code that scores out-*.txt/variant-*.txt.",
        "",
        "PROBES (each is one dxr invocation against this release's rewriter)",
        "  ask1       repro.hlsl " + " ".join(REPRO_ARGS),
        "  ask1-ctrl  control-param-used.hlsl, same options, ps_main's",
        "             parameter IS read in the body.",
        "  ask2       repro2.hlsl, same options: local var Material mtl is",
        "             declared/cast but never read.",
        "  ask2-ctrl  control-local-used.hlsl, same options, mtl IS read",
        "             afterwards.",
        "  optcheck   `-unchanged repro.hlsl`: does this release accept the",
        "             rewriter option surface at all?",
        "  noopts     `repro.hlsl` alone: does this release's rewriter run at",
        "             all?",
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

    out += [f"{'release':>16} {'ask1':>10} {'ask1-ctrl':>10} {'ask2':>10}"
            f" {'ask2-ctrl':>10} {'optcheck':>9} {'noopts':>7}  reading",
            f"{'-' * 16} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}"
            f" {'-' * 9} {'-' * 7}  {'-' * 7}"]
    for tag in tags:
        by = {r["probe"]: r for r in rows if r["label"] == tag}
        r1, r2, why = reading(rows, tag)
        out.append(
            f"{tag:>16} {by['ask1']['verdict']:>10} "
            f"{by['ask1-ctrl']['verdict']:>10} "
            f"{by['ask2']['verdict']:>10} "
            f"{by['ask2-ctrl']['verdict']:>10} "
            f"{('ok' if by['optcheck']['exit'] == 0 else 'exit ' + str(by['optcheck']['exit'])):>9} "
            f"{('ok' if by['noopts']['exit'] == 0 else 'exit ' + str(by['noopts']['exit'])):>7}"
            f"  ask1={r1} ask2={r2}" + (f"  [{why}]" if why else ""))
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
            "#5290's text names no prerelease, so none opts in under",
            "release-policy.json.", ""]

    out += ["", "VERBATIM. The oldest release in the population, the first",
            "release, the newest release, and ground truth.", ""]
    want = [tags[0], tags[1], tags[-2], tags[-1]] if len(tags) > 3 else tags
    seen = set()
    for tag in want:
        if tag in seen:
            continue
        seen.add(tag)
        for probe_name in ("ask1", "ask2", "optcheck", "noopts"):
            for r in rows:
                if r["label"] == tag and r["probe"] == probe_name:
                    out += [f"=== {tag}  probe: {probe_name} ===", f"$ {r['cmd']}",
                            f"[exit] {r['exit']}",
                            f"[verdict] {r['verdict']}" if r['verdict'] else "",
                            "", r["output"].rstrip("\n"), ""]
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
    versions["dxr-5290-release"] = version_of(DXR)
    for probe in PROBES:
        rows.append(measure("dxr-5290-release", DXR, probe))

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
