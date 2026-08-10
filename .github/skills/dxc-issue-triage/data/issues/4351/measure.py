"""#4351 -- has any shipped DXC release ever kept `struct Child` when
`-remove-unused-globals` is used, or has the rewriter always deleted it?

`triage.py bisect` cannot answer this and refuses to try. The reported surface
is the rewriter, which `dxc.exe` never reaches -- measured, not assumed:
`dxc -E InitArgs -remove-unused-globals repro.hlsl` answers `dxc failed :
Unknown argument: '-remove-unused-globals'` (exit 1), captured in
`variant-dxc-rejects-rewriter-flag-main-debug.txt`. `bisect` resolves a release
tag to that release's `dxc.exe`, so it would run a different program and
produce a confident, meaningless table; `refuse_harness_bisect` in triage.py
hard-errors for exactly this reason.

The history is measurable anyway because the whole rewriter lives inside
**dxcompiler.dll**, which every release ships, while no release archive in the
catalog ships `dxr.exe`. So the driver is held FIXED (the ground-truth
dxr.exe, which merely forwards its argv to `IDxcRewriter2::RewriteWithOptions`
and prints the returned blob) and the DLL is VARIED. Same shape as #3237's
release reflection DLLs and #2923's release PIX passes.

The substitution is done by copying `dxr.exe` next to the release
`dxcompiler.dll` in a scratch directory under `.cache` -- Windows searches the
executable's own directory first -- and NOT with `-external <dll> -external-fn
DxcCreateInstance`. Both work on current releases and `--equiv` proves they
agree, but `-external` is unsafe on the oldest ones: dxr forwards its ENTIRE
argv to the DLL, so `-external`/`-external-fn` become two more options the
release's own option table has to recognise, and they only gained their
`RewriteOption` flag in 2020. Directory staging lets each release see exactly
the reporter's option list and nothing else.

FIVE probes run against every release. The last two are the per-release
controls SKILL.md requires ("run the feature-presence control on every probed
release, not only on ground truth"), and they are what makes an `invalid-probe`
unambiguous instead of a silent `no-repro`:

  repro     repro.hlsl, `-E InitArgs -remove-unused-globals`, scored by
            match.json. This is the reporter's exact command line.
  control   control-single-child.hlsl, same options, same predicate. The only
            difference from the repro is that the `Child` member is not an
            array. It MUST score no-repro on every release: that is the
            per-release proof that this release's rewriter CAN emit `struct
            Child` and that the predicate is not simply matching everything.
            A release where both match is a release where the instrument
            broke, not one where the array is the cause.
  fnparam   case-fn-param.hlsl, same options, scored by match-fn-param.json --
            the 2022-08-15 comment's separate claim about unused function
            parameter types. Its own positive self-test is inside that
            predicate (the READ parameter's type must survive).
  optcheck  `-unchanged repro.hlsl` -- the smallest possible rewriter option.
            Does this release's DLL accept the rewriter option surface at all?
  noopts    `repro.hlsl` with no options -- does this release's rewriter run at
            all? A release that fails optcheck but passes noopts predates the
            option set: the repro cannot be expressed there, so the row is an
            invalid probe rather than a clean result. v1.4.1907 is that case
            (`git show v1.4.1907:include/dxc/Support/HLSLOptions.td` has no
            `RewriteOption` at all).

Scoring is `triage.classify`, imported rather than reimplemented, so these rows
are scored by the identical predicate code that scores `out-*.txt`.

Usage:
    python measure.py                    # ground truth only
    python measure.py --history          # every stable cached release, then ground truth
    python measure.py --history --equiv  # ...and cross-check against -external
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
SCRATCH = os.path.join(SKILL, ".cache", "rw4351")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import triage  # noqa: E402

ISSUE = 4351
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
DXR = os.path.join(BUILD_BIN, "dxr.exe")

REPRO_ARGS = ["-E", "InitArgs", "-remove-unused-globals"]
# (probe name, options, shader, predicate or None when the probe is not scored)
PROBES = [
    ("repro", REPRO_ARGS, "repro.hlsl", "match.json"),
    ("control", REPRO_ARGS, "control-single-child.hlsl", "match.json"),
    ("fnparam", REPRO_ARGS, "case-fn-param.hlsl", "match-fn-param.json"),
    ("optcheck", ["-unchanged"], "repro.hlsl", None),
    ("noopts", [], "repro.hlsl", None),
]


def redact(path):
    """Absolute path -> the placeholders triage.py writes in capture headers.

    These files are committed; an absolute path ships one machine's directory
    layout to everyone. Same tokens and same most-specific-first order as
    scripts/triage.py.
    """
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
    """(tag, build_date, release_bin_dir) for every STABLE cached release.

    Oldest first, by the build date encoded in the asset name. Prereleases are
    excluded by SKILL.md policy and named in the report rather than dropped
    silently; #4351's text names none of them, so none opts in.
    """
    if not os.path.isfile(DB):
        sys.exit(f"no triage database at {redact(DB)}; run `triage.py catalog`")
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
    """Copy dxr.exe beside a release's dxcompiler.dll; return the staged exe.

    Windows searches the executable's own directory first, so this makes dxr
    load the release rewriter without adding any option to what the DLL parses.
    """
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
    name, opts, shader, match_file = probe
    argv = [exe, *extra, *opts, shader]
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    text = p.stdout + p.stderr
    verdict, reason = (triage.classify(ISSUE, text, p.returncode, False,
                                       match_file, explain=True)
                       if match_file else (None, None))
    # The command is echoed from the argv that actually ran, via list2cmdline,
    # then collapsed to placeholders -- it is not a transcription.
    return {"label": label, "probe": name, "shader": shader,
            "match": match_file,
            "cmd": redact(argv[0]) + " " + subprocess.list2cmdline(
                [redact(x) if os.path.isabs(x) else x for x in argv[1:]]),
            "exit": p.returncode, "verdict": verdict, "why": reason,
            "sha256": hashlib.sha256(
                text.encode("utf-8", "replace")).hexdigest(),
            "output": text}


def reading(rows, tag):
    """Per-release one-word reading of the five probes."""
    by = {r["probe"]: r for r in rows if r["label"] == tag}
    if by["optcheck"]["exit"] != 0 and by["noopts"]["exit"] == 0:
        return ("invalid-probe",
                "rewriter runs, but this release's option table carries no "
                "rewriter options at all, so the repro cannot be expressed "
                "here")
    if by["optcheck"]["exit"] != 0:
        return ("invalid-probe", "this release's rewriter did not run")
    if by["control"]["verdict"] == "repro":
        return ("instrument-broken",
                "the non-array control ALSO scored repro, so this row says "
                "nothing about the array being the cause")
    return (by["repro"]["verdict"], "")


def report(rows, skipped, equiv, versions):
    out = [
        "#4351 release history -- does -remove-unused-globals ever keep the",
        "definition of a struct used only as the element type of a member",
        "array?",
        "",
        "Produced by `python measure.py --history --equiv`. Each row drives",
        "THAT RELEASE's own rewriter: the ground-truth dxr.exe driver is copied",
        "next to that release's dxcompiler.dll in a scratch directory under",
        ".cache, so Windows loads the release rewriter and the release's own",
        "option table sees exactly the reporter's options and nothing else.",
        "",
        "dxr.exe (tools/clang/tools/dxr/dxr.cpp) forwards its argv verbatim to",
        "IDxcRewriter2::RewriteWithOptions -- the API behind the reporter's",
        "command line -- and prints the returned blob. The rewriter itself",
        "lives in dxcompiler.dll, so the code under test is the release's, not",
        "the driver's. No release archive in the catalog ships dxr.exe, which",
        "is why the driver is held fixed and the DLL varied.",
        "",
        "triage.py bisect cannot produce this table and refuses to try: it",
        "would substitute each release's dxc.exe, and dxc.exe rejects",
        "-remove-unused-globals outright (measured -- see",
        "variant-dxc-rejects-rewriter-flag-main-debug.txt).",
        "",
        "SCORING is triage.classify with this issue's predicates, imported from",
        "scripts/triage.py -- the same code that scores out-*.txt.",
        "  repro    = match.json: the output still declares a member of type",
        "             Child, still contains the InitArgs entry point, does NOT",
        "             define struct Child, and did NOT print the",
        "             `// Rewrite unchanged result:` banner (so a rewriter",
        "             option was honoured by THIS release).",
        "  control  = the same predicate over control-single-child.hlsl, whose",
        "             Child member is not an array. MUST be no-repro on every",
        "             release.",
        "  fnparam  = match-fn-param.json over case-fn-param.hlsl: the unused",
        "             parameter's type is removed while the read parameter's",
        "             type survives.",
        "",
        "PROBES (each is one dxr invocation against this release's rewriter)",
        "  repro     repro.hlsl " + " ".join(REPRO_ARGS),
        "  control   control-single-child.hlsl, same options",
        "  fnparam   case-fn-param.hlsl, same options",
        "  optcheck  `-unchanged repro.hlsl`: does this release accept the",
        "            rewriter option surface at all?",
        "  noopts    `repro.hlsl` alone: does this release's rewriter run?",
        "",
        "  optcheck failing while noopts succeeds is what separates 'this",
        "  release predates the options' from 'this release rewrote it clean'.",
        "",
    ]
    tags = []
    for r in rows:
        if r["label"] not in tags:
            tags.append(r["label"])

    out += [f"{'release':>16} {'repro':>12} {'control':>12} {'fnparam':>12}"
            f" {'optcheck':>9} {'noopts':>7}  reading",
            f"{'-' * 16} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 9} {'-' * 7}"
            f"  {'-' * 7}"]
    for tag in tags:
        by = {r["probe"]: r for r in rows if r["label"] == tag}
        verdict, why = reading(rows, tag)
        out.append(
            f"{tag:>16} {by['repro']['verdict']:>12} "
            f"{by['control']['verdict']:>12} "
            f"{by['fnparam']['verdict']:>12} "
            f"{('ok' if by['optcheck']['exit'] == 0 else 'exit ' + str(by['optcheck']['exit'])):>9} "
            f"{('ok' if by['noopts']['exit'] == 0 else 'exit ' + str(by['noopts']['exit'])):>7}"
            f"  {verdict}" + (f"  [{why}]" if why else ""))
    out.append("")

    out += ["VERSION reported by each staged driver (`dxr.exe --version`),",
            "which is the DLL's own version string. A row whose string does",
            "not name that release would mean the staging failed and the",
            "ground-truth DLL answered instead:", ""]
    for tag in tags:
        out.append(f"  {tag:<16} {versions.get(tag, '(not recorded)')}")
    out.append("")

    out += ["SKIPPED (not in the stable-release population)", ""]
    for tag, date, why in skipped:
        out.append(f"  {tag:<32} {date or '(no build date)':<12} {why}")
    out += ["",
            "#4351's text names no prerelease, so none opts in under",
            "release-policy.json.", ""]

    if equiv:
        out += ["", "EQUIVALENCE CONTROL -- scratch-directory substitution vs",
                "`-external <dll> -external-fn DxcCreateInstance`, same",
                "release, same repro probe. Equal SHA-256 over combined",
                "stdout+stderr means the two mechanisms drive the same",
                "rewriter, so the table above is not an artefact of how the DLL",
                "was selected. A DIFFERENT row is expected only where",
                "-external is itself unparseable by that release.", ""]
        for e in equiv:
            out += [f"  {e['tag']:<16} "
                    f"{'IDENTICAL' if e['same'] else 'DIFFERENT'}",
                    f"    staged   {e['staged_sha']}",
                    f"    external {e['external_sha']}"]
        out.append("")

    out += ["", "VERBATIM. The oldest release in the population, the first that",
            "can express the repro, the newest release, and ground truth.", ""]
    want = [tags[0], tags[1], tags[-2], tags[-1]] if len(tags) > 3 else tags
    seen = set()
    for tag in want:
        if tag in seen:
            continue
        seen.add(tag)
        for probe in ("repro", "control", "fnparam", "optcheck", "noopts"):
            for r in rows:
                if r["label"] == tag and r["probe"] == probe:
                    out += [f"=== {tag}  probe: {probe} ===", f"$ {r['cmd']}",
                            f"[exit] {r['exit']}"]
                    if r["verdict"]:
                        out.append(f"[verdict] {r['verdict']}")
                    out += ["", r["output"].rstrip("\n"), ""]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history", action="store_true",
                    help="probe every stable cached release as well")
    ap.add_argument("--equiv", action="store_true",
                    help="cross-check scratch-dir substitution against -external")
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
    versions["main-debug"] = version_of(DXR)
    for probe in PROBES:
        rows.append(measure("main-debug", DXR, probe))

    equiv = []
    if a.equiv:
        for tag, _date, release_bin in targets:
            dll = os.path.join(release_bin, "dxcompiler.dll")
            staged = measure(tag, os.path.join(SCRATCH, tag, "dxr.exe"),
                             PROBES[0])
            ext = measure(tag, DXR, PROBES[0],
                          extra=["-external", dll,
                                 "-external-fn", "DxcCreateInstance"])
            equiv.append({"tag": tag, "staged_sha": staged["sha256"],
                          "external_sha": ext["sha256"],
                          "same": staged["sha256"] == ext["sha256"]})

    for r in rows:
        print(f"{r['probe']:>9} {r['label']:>16} exit={r['exit']:<11}"
              f" {r['verdict'] or '-'}")
    for e in equiv:
        print(f"    equiv {e['tag']:>16} "
              f"{'identical' if e['same'] else 'DIFFERENT'}")

    with open(os.path.join(HERE, "measure.json"), "w") as f:
        json.dump({"versions": versions, "rows": rows, "equiv": equiv},
                  f, indent=2)
    path = os.path.join(HERE, "manual-case-release-history.txt")
    with open(path, "w", newline="\n") as f:
        f.write(report(rows, skipped, equiv, versions))
    print("wrote", redact(path))


if __name__ == "__main__":
    main()
