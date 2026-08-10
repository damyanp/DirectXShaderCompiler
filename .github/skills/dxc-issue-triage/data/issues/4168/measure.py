#!/usr/bin/env python
"""#4168 release matrix: when did the linked shader's cbuffer variables come back?

`bisect` cannot answer this. It substitutes each release's `dxc.exe` for the
registered compiler, and the registered compiler here is `run-link4168.cmd`, so
it would run the harness's argv against a bare `dxc.exe` and report the inverse
history. SKILL.md's sanctioned replacement is "an explicit release matrix that
holds the harness fixed while varying each release's executable".

Two arms per release, both driven through `triage.py run` so every result is a
tool-made capture that `reindex` re-scores -- there is no second scoring
implementation here that could disagree with the tool:

  rel-<tag>     the repro: the release compiles the library and links it, the
                local build's `dxa` reads the result.
  relctl-<tag>  the per-release control: the SAME release compiles the same
                source straight to ps_6_0 with no library and no link, read by
                the same fixed `dxa`. It must reflect the two variables, i.e.
                score no-match. SKILL.md: "Run the feature-presence control on
                every probed release, not only on ground truth" -- without it, a
                release that cannot express `lib_6_x`, cannot link, or produces
                a container this reader cannot parse would score a confident
                `no-repro` while measuring nothing.

Both arms carry `--expect`, so `reindex` re-checks the whole history and not
just the controls. Note the ordering, because it is the difference between an
assertion and a circular one: the repro arm's expectations in EXPECT below were
**written down after the first run**, transcribed from captures already on disk
(manual-case-release-matrix.txt), and their only job is to freeze the measured
history so a later predicate change that silently moves a release boundary is
reported instead of absorbed. They were not guessed beforehand and tuned until
they passed.

Stable releases only. SKILL.md: history boundaries are stable-release boundaries
by policy, and this issue's text names no prerelease, so v1.5.2003 and the other
prereleases stay outside the sequence and are listed as skipped.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
TRIAGE = os.path.join(SKILL, "scripts", "triage.py")
ISSUE = "4168"

REPRO_ARM = ("--release {tag} dxc -T lib_6_x -Fo m4168-lib.dxo repro.hlsl"
             " ; dxl -T ps_6_0 -E main -Fo m4168-linked.dxo m4168-lib.dxo"
             " ; dxa -dumpreflection m4168-linked.dxo")
CTRL_ARM = ("--release {tag} dxc -T ps_6_0 -E main -Fo m4168-direct.dxo"
            " repro.hlsl ; dxa -dumpreflection m4168-direct.dxo")

# The measured history, transcribed from the first run's captures. Releases
# older than v1.6.2106 answer `Unknown argument: '-link'` -- dxc.exe had no
# linker yet -- so they are invalid probes, not clean results: they cannot
# express the configuration at all.
EXPECT = {
    "v1.4.1907": "invalid-probe",
    "v1.5.2010": "invalid-probe",
    "v1.6.2104": "invalid-probe",
    "v1.6.2106": "match",
    "v1.6.2112": "match",
    "v1.7.2207": "match",
    "v1.7.2212": "match",
    "v1.7.2212.1": "match",
}
EXPECT_DEFAULT = "no-match"


def sql(query):
    p = subprocess.run([sys.executable, TRIAGE, "sql", query],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


def expectation_violated(expect, verdict):
    """Same rule triage.py applies, so the summary agrees with the runner."""
    if expect == "invalid-probe" or verdict == "invalid-probe":
        return verdict != expect
    return (verdict == "repro") != (expect == "match")


def probe(label, args, expect=None):
    argv = [sys.executable, TRIAGE, "run", "--issue", ISSUE,
            "--compiler", "main-debug-link4168", "--label", label,
            "--args", args]
    if expect:
        argv += ["--expect", expect]
    print("$ " + subprocess.list2cmdline(
        ["python", "triage.py"] + argv[2:]))
    p = subprocess.run(argv, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    # `run` reports where it filed the capture as an absolute path. This
    # transcript is committed, so fold the workspace root back to <repo> --
    # scripts/check_paths.py is the gate that catches it otherwise.
    print(out.replace(REPO, "<repo>").replace(REPO.replace("\\", "/"),
                                              "<repo>").rstrip())
    verdict = "?"
    for tok in out.split():
        if tok in ("repro", "no-repro", "invalid-probe"):
            verdict = tok
    return verdict, out


def num_variables(label, match=None):
    name = f"variant-{label}-main-debug-link4168"
    if match:
        name += f"--{match}"
    path = os.path.join(HERE, name + ".txt")
    if not os.path.isfile(path):
        return "no capture"
    counts = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "Num Variables:" in line:
                counts.append(line.split("Num Variables:")[1].strip())
    return ",".join(counts) if counts else "none printed"


def main():
    rows = [r for r in sql(
        "SELECT tag, build_date, prerelease, cached_path FROM releases"
        " ORDER BY build_date IS NULL, build_date")]
    stable = [r for r in rows if not r["prerelease"] and r["cached_path"]]
    skipped = [r["tag"] for r in rows if r["prerelease"]]
    uncached = [r["tag"] for r in rows
                if not r["prerelease"] and not r["cached_path"]]

    print(f"stable releases in the sequence: {len(stable)}")
    print(f"prereleases skipped by policy:   {skipped}")
    print(f"stable but not cached locally:   {uncached}")
    print()

    results = []
    for r in stable:
        tag = r["tag"]
        print(f"===== {tag}  ({r['build_date']}) " + "=" * 30)
        rv, _ = probe(f"rel-{tag}", REPRO_ARM.format(tag=tag),
                      expect=EXPECT.get(tag, EXPECT_DEFAULT))
        cv, _ = probe(f"relctl-{tag}", CTRL_ARM.format(tag=tag),
                      expect="no-match")
        results.append((tag, r["build_date"], rv, cv))
        print()

    print()
    print("=" * 78)
    print("SUMMARY -- repro arm is lib_6_x -> ps_6_0 -> reflect;")
    print("           control arm is the same release compiling straight to "
          "ps_6_0.")
    print("=" * 78)
    head = (f"{'release':<16} {'built':<12} {'repro arm':<14} "
            f"{'Num Variables':<16} {'control arm':<14} {'Num Variables'}")
    print(head)
    print("-" * len(head))
    for tag, date, rv, cv in results:
        print(f"{tag:<16} {str(date):<12} {rv:<14} "
              f"{num_variables('rel-' + tag):<16} {cv:<14} "
              f"{num_variables('relctl-' + tag)}")
    print()
    bad = [t for t, _, rv, _ in results if rv == "repro"]
    good = [t for t, _, rv, _ in results if rv == "no-repro"]
    broken_ctl = [t for t, _, _, cv in results if cv != "no-repro"]
    print(f"reproduces in {len(bad)} stable release(s): {bad}")
    print(f"clean in       {len(good)} stable release(s): {good}")
    print(f"releases whose control arm did NOT behave: {broken_ctl or 'none'}")
    violated = [t for t, _, rv, _ in results
                if expectation_violated(EXPECT.get(t, EXPECT_DEFAULT), rv)]
    print(f"repro-arm rows that moved since the pinned history: "
          f"{violated or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
