"""#4273 -- has any shipped DXC release ever removed a wholly unused `cbuffer`
block from rewriter output, or is the carve-out unchanged?

`triage.py bisect` cannot answer this, and refuses to try. The reported surface
is `IDxcRewriter2::RewriteWithOptions`, which `dxc.exe` never calls; bisect
resolves a release tag to that release's **dxc.exe** and would silently answer a
different question. `refuse_harness_bisect` in triage.py hard-errors for exactly
this reason.

What makes the history measurable anyway is that the whole rewriter lives inside
**dxcompiler.dll**, which every release ships (no release archive in the catalog
ships `dxr.exe`). The ground-truth `dxr.exe` is a thin driver -- it forwards its
own argv to `IDxcRewriter2::RewriteWithOptions` and prints the returned blob --
so running it beside a release DLL runs THAT RELEASE's rewriter. Same shape as
#3237 (release reflection DLLs) and #2923 (release PIX passes).

The substitution is done by copying `dxr.exe` next to the release
`dxcompiler.dll` in a scratch directory under `.cache`, NOT with
`-external <dll> -external-fn DxcCreateInstance`. Both work on current releases
and this script proves they agree (`--equiv`), but `-external` is unsafe here:
dxr forwards its ENTIRE argv to the DLL, so `-external` and `-external-fn`
become two more options the release's own option table has to recognise -- and
they only gained their `RewriteOption` flag on 2020-03-04 in #2730, the same
commit that introduced `-extract-entry-uniforms`. Under `-external`, v1.4.1907
fails in a way that cannot be told apart from failing on the repro's own
options. The scratch-directory form lets each release see exactly the reporter's
option list and nothing else.

FOUR probes run against every release, not one. The last two are the per-release
controls SKILL.md requires ("run the feature-presence control on every probed
release, not only on ground truth"), and they are what makes an `invalid-probe`
unambiguous instead of a silent `no-repro`:

  repro     repro.hlsl with the reporter's four options. cbA is used by vsMain;
            cbB is used only by the discarded psMain.
  control   control-loose-only.hlsl, same options. cbB's constant is a loose
            global instead of an explicit block, so the predicate MUST score
            no-repro on every release; if it ever matched, the predicate would
            be matching something other than what it claims.
  optcheck  `-unchanged repro.hlsl` -- the smallest possible rewriter option.
            Does this release's DLL accept the rewriter option surface at all?
  noopts    `repro.hlsl` with no options -- does this release's rewriter run at
            all? A release that fails `optcheck` but passes `noopts` predates
            the option set: the repro cannot be expressed there, and the row is
            an invalid probe rather than a clean result.

The per-release POSITIVE self-test is inside `match.json` as clause 4: the
unused loose global `gLooseUnused` must be absent from the same output. A
release whose rewriter did nothing, or that ignored `-remove-unused-globals`,
fails that clause and scores no-repro -- so a no-op can never be counted as a
reproduction.

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
SCRATCH = os.path.join(SKILL, ".cache", "rw4273")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import triage  # noqa: E402

ISSUE = 4273
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
DXR = os.path.join(BUILD_BIN, "dxr.exe")

REPRO_ARGS = ["-E", "vsMain", "-remove-unused-globals",
              "-remove-unused-functions", "-extract-entry-uniforms"]
PROBES = [
    ("repro", REPRO_ARGS, "repro.hlsl", True),
    ("control", REPRO_ARGS, "control-loose-only.hlsl", True),
    ("optcheck", ["-unchanged"], "repro.hlsl", False),
    ("noopts", [], "repro.hlsl", False),
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
    silently; #4273's text names none of them, so none opts in.
    """
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
    name, opts, shader, scored = probe
    argv = [exe, *extra, *opts, shader]
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    text = p.stdout + p.stderr
    verdict, reason = (triage.classify(ISSUE, text, p.returncode, False,
                                       "match.json", explain=True)
                       if scored else (None, None))
    # The command is echoed from the argv that actually ran, via list2cmdline,
    # then collapsed to placeholders -- it is not a transcription.
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


def report(rows, skipped, equiv, versions):
    out = [
        "#4273 release history -- does -remove-unused-globals ever remove a",
        "wholly unused `cbuffer` block?",
        "",
        "Produced by `python measure.py --history --equiv`. Each row drives THAT",
        "RELEASE's own rewriter: the ground-truth dxr.exe driver is copied next",
        "to that release's dxcompiler.dll in a scratch directory under .cache,",
        "so Windows loads the release rewriter and the release's own option",
        "table sees exactly the reporter's options and nothing else.",
        "",
        "dxr.exe (tools/clang/tools/dxr/dxr.cpp) forwards its argv verbatim to",
        "IDxcRewriter2::RewriteWithOptions -- the exact API the reporter used --",
        "and prints the returned blob. The rewriter itself lives in",
        "dxcompiler.dll, so the code under test is the release's, not the",
        "driver's. No release archive in the catalog ships dxr.exe, which is why",
        "the driver is held fixed and the DLL varied.",
        "",
        "triage.py bisect cannot produce this table and refuses to try: it would",
        "substitute each release's dxc.exe, which never enters the rewriter.",
        "",
        "SCORING for the `repro` and `control` columns is triage.classify with",
        "this issue's match.json, imported from scripts/triage.py -- the same",
        "code that scores out-*.txt.",
        "  repro    = unused `cbuffer cbB` survived, psMain was removed, vsMain",
        "             is present, AND the unused loose global gLooseUnused was",
        "             removed. That last clause is the per-release proof that",
        "             -remove-unused-globals was honoured by THIS release, so a",
        "             no-op rewriter cannot score repro.",
        "  no-repro = one of those clauses failed.",
        "",
        "PROBES (each is one dxr invocation against this release's rewriter)",
        "  repro     repro.hlsl " + " ".join(REPRO_ARGS),
        "  control   control-loose-only.hlsl, same options. No explicit",
        "            `cbuffer cbB` in the source, so it MUST score no-repro on",
        "            every release, or the repro column means nothing.",
        "  optcheck  `-unchanged repro.hlsl`: does this release accept the",
        "            rewriter option surface at all?",
        "  noopts    `repro.hlsl` alone: does this release's rewriter run at all?",
        "",
        "  optcheck failing while noopts succeeds is what separates 'this release",
        "  predates the options' from 'this release rewrote it clean'.",
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
            "#4273's text names no prerelease, so none opts in under",
            "release-policy.json.", ""]

    if equiv:
        out += ["", "EQUIVALENCE CONTROL -- scratch-directory substitution vs",
                "`-external <dll> -external-fn DxcCreateInstance`, same release,",
                "same repro probe. Equal SHA-256 over combined stdout+stderr",
                "means the two mechanisms drive the same rewriter, so the table",
                "above is not an artefact of how the DLL was selected. A",
                "DIFFERENT row is expected only where -external is itself",
                "unparseable by that release.", ""]
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
