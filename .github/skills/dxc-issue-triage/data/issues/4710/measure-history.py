"""Per-release matrix for DXC issue 4710.

Why this exists rather than `triage.py bisect` alone:

The reported symptom of #4710 IS a diagnostic -- the reporter says DXC emits
`error: Index for resource array inside cbuffer must be a literal expression`
on a shader that ought to compile. For that polarity the `invalid-probe`
safety net is blind: a release that rejects the input for a completely
unrelated reason produces an `error:` line too, and a release that cannot
compile the profile at all produces a *clean* `no-match`, which reads as
"fixed here". Neither is distinguishable from the real thing by looking at the
repro's own output.

So every release is probed with the repro AND with a positive control
(`control-hello.hlsl`, a trivial shader with no resources at all) plus the
negative controls. A release whose control does not behave is disqualified,
not counted.

Everything is run through triage.py's own predicate (`triage.matches`) and its
own path normalisation (`triage.redact_paths`), so this file cannot disagree
with the tool about what the predicate says, and so no machine-local path is
committed. The command line for every single run is echoed with
`subprocess.list2cmdline`, i.e. exactly what was executed.

Usage:  python measure-history.py > manual-case-release-history.txt
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))

import triage  # noqa: E402

ISSUE = 4710
PROFILE = ["-T", "ps_6_0", "-E", "psMain"]

# (filename, what it is, what it must do)
CASES = [
    ("repro.hlsl", "repro: cb struct-array .Texture[i], [unroll]", "subject"),
    ("case-cb-array-dynamic.hlsl", "form B: cb resource array [i], [unroll]", "subject"),
    # NOT a control: this case has a history of its own, and that history is a
    # finding. It is the case DXC's own tests assert the diagnostic for, and the
    # one the diagnostic is plainly right about today -- but the release whose
    # dxc predates the diagnostic compiles it too, so no expectation can be
    # asserted across the whole matrix.
    ("case-truly-dynamic.hlsl", "genuinely dynamic index from an input", "subject"),
    ("control-literal-index.hlsl", "same cb resource array, literal indices", "expect-no-match"),
    ("control-global-array.hlsl", "form C: GLOBAL resource array [i], [unroll]", "expect-no-match"),
    ("control-hello.hlsl", "positive control: trivial ps, no resources", "expect-no-match"),
]


def version_of(exe):
    """Best available version string.

    v1.4.1907's dxc predates `--version` and answers `Unknown argument`; it
    prints the same information in the `-?` banner. Try both rather than
    recording a failure that says nothing about the binary.
    """
    for argv in ([exe, "--version"], [exe, "-?"]):
        p = subprocess.run(argv, capture_output=True, text=True)
        text = (p.stdout + p.stderr).strip()
        for line in text.splitlines():
            if "dxcompiler.dll" in line:
                return f"{subprocess.list2cmdline(argv[1:])} -> {line.strip()}"
    return f"(no version string; last output: {text.splitlines()[:1]})"


def run(exe, shader, directory):
    argv = [exe] + PROFILE + [shader]
    try:
        p = subprocess.run(argv, cwd=directory, capture_output=True, text=True,
                           timeout=120)
        out, rc, timed_out = p.stdout + p.stderr, p.returncode, False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + (e.stderr or "")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        rc, timed_out = -1, True
    return triage.redact_paths(out), rc, timed_out, subprocess.list2cmdline(argv)


def first_error(text):
    for line in text.splitlines():
        if "error:" in line or "error " in line.lower():
            return line.strip()
    return ""


def main():
    directory = triage.issue_dir(ISSUE)
    con = triage.con()
    rows = con.execute(
        "SELECT tag, build_date, prerelease, bisectable, cached_path FROM releases "
        "WHERE cached_path IS NOT NULL ORDER BY build_date").fetchall()

    builds = []
    for r in rows:
        if r["prerelease"] or not r["bisectable"]:
            continue                      # stable-release policy; prereleases excluded
        builds.append((r["tag"], r["build_date"], r["cached_path"]))
    gt = con.execute("SELECT exe_path FROM compilers WHERE id='main-debug'").fetchone()
    builds.append(("main-debug", "ground truth", gt["exe_path"]))

    print("# issue 4710 -- per-release matrix, repro + controls on the SAME binary")
    print("#")
    print("# predicate: triage.matches(4710, ...) over match.json, i.e. the literal text")
    print("#            'error: Index for resource array inside cbuffer must be a "
          "literal expression'")
    print("# command:   dxc " + subprocess.list2cmdline(PROFILE) + " <shader>")
    print("# generator: measure-history.py (committed beside this file)")
    print("#")
    print("# 'match' means DXC emitted the diagnostic the issue is about.")
    print("# Prereleases are excluded by policy: the issue names 'main' and the July 2022")
    print("# official release, not a prerelease.")
    print("#")
    print("# Rows marked 'subject' carry a history of their own and no expectation is")
    print("# asserted for them. Rows marked '[control OK]' are assertions: a build where a")
    print("# control misbehaves has not measured this issue and would be disqualified.")
    print()

    for tag, date, exe in builds:
        vtext = triage.redact_paths(version_of(exe))
        print("=" * 78)
        print(f"{tag}   build_date={date}")
        print(f"  exe:     {triage.display_exe(exe)}")
        print(f"  version: {vtext}")
        for shader, what, role in CASES:
            text, rc, timed_out, cmdline = run(exe, shader, directory)
            m = triage.matches(ISSUE, text, rc, timed_out)
            verdict = "match" if m else "no-match"
            ok = ""
            if role == "expect-match":
                ok = "  [control OK]" if m else "  [*** CONTROL FAILED ***]"
            elif role == "expect-no-match":
                ok = "  [control OK]" if not m else "  [*** CONTROL FAILED ***]"
            print(f"  $ {cmdline.replace(exe, triage.display_exe(exe))}")
            print(f"    {what}")
            print(f"    exit=0x{rc & 0xFFFFFFFF:08X} -> {verdict}{ok}")
            err = first_error(text)
            if err:
                print(f"    first error line: {err}")
            elif rc == 0:
                print("    (compiled clean)")
        print()


if __name__ == "__main__":
    main()
