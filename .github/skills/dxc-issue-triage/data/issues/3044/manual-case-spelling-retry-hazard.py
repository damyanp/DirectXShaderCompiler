"""Proof that the automatic `-`/`_`/`/` spelling re-probe is DESTRUCTIVE here.

`triage.py run` re-probes other spellings when a run answers `Unknown
argument`, so that a demotion for spelling is not misread as "the feature did
not exist". For issue 3044 that safety net is itself the hazard, and this is
the measurement that says so.

dxc <= v1.7.2207 has `P : Separate<["-","/"],"P">`, i.e. `-P <name>` names the
OUTPUT file and the input is positional; `-Fi` does not exist yet, so the
repro command answers `Unknown argument: '-Fi'`. The `/` retry of that command
is

    -P repro.hlsl /Fi preprocessed.i

Unknown `/`-flags are not diagnosed by dxc -- they fall through to the input
list -- so this parses as "preprocess preprocessed.i into repro.hlsl". The
repro source is overwritten by preprocessed text, and dxc exits 0.

This runs that exact command against every stable release in a scratch copy
and reports whether repro.hlsl survived. `preprocessed.i` is pre-seeded,
because after a first successful probe in a shared directory it would exist --
which is what makes the clobber silent rather than a missing-file error.

Usage (from the workspace root):
    python data/issues/3044/manual-case-spelling-retry-hazard.py > \
           data/issues/3044/manual-case-spelling-retry-hazard.txt
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

RETRY = ["-P", "repro.hlsl", "/Fi", "preprocessed.i"]


def probe(tag, exe):
    work = os.path.join(HERE, f"retry-{tag}")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    shutil.copy(os.path.join(HERE, "repro.hlsl"), work)
    with open(os.path.join(work, "preprocessed.i"), "w",
              encoding="utf-8") as f:
        f.write("// left behind by an earlier probe in the same directory\n")

    src = os.path.join(work, "repro.hlsl")
    before = open(src, encoding="utf-8").read()
    p = subprocess.run([exe] + RETRY, cwd=work, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    after = open(src, encoding="utf-8").read()
    clobbered = before != after

    print(f"--- {tag}   {triage.display_exe(exe)}")
    print(f"    $ dxc {subprocess.list2cmdline(RETRY)}")
    print(f"      exit={p.returncode}  "
          f"stderr={(p.stderr or '').strip()[:120]!r}")
    print(f"      REPRO CLOBBERED = {clobbered}")
    if clobbered:
        print("      repro.hlsl now begins "
              + repr(after.splitlines()[:2]))
    shutil.rmtree(work, ignore_errors=True)
    return clobbered


def main():
    tags = [r["tag"] for r in triage.con().execute(
        "SELECT tag FROM releases WHERE prerelease = 0 AND asset_name IS NOT"
        " NULL ORDER BY build_date")]
    bad = []
    for tag in tags:
        if probe(tag, triage.ensure_release(tag)):
            bad.append(tag)
    if probe("main-debug", triage.resolve_compiler("main-debug")):
        bad.append("main-debug")

    print("\n=== summary")
    print(f"builds probed: {len(tags) + 1}")
    print(f"builds where the retry OVERWRITES repro.hlsl: {bad}")
    print("\nConclusion: `triage.py bisect` must never be run on issue 3044.")


if __name__ == "__main__":
    main()
