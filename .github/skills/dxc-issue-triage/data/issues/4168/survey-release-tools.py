#!/usr/bin/env python
"""#4168: what does each cached release archive actually ship?

The repro is a three-tool chain (dxc -> dxl -> dxa). `bisect` cannot run it --
it substitutes each release's `dxc.exe` for the registered compiler, and the
registered compiler here is the harness, so it would measure the wrong thing
(SKILL.md: "`bisect` now hard-errors on a harness-as-compiler issue"). The
sanctioned replacement is a release matrix that holds the harness fixed and
varies the tool directory, which is what DXC_LINK4168_BIN exists for.

That is only possible for releases that ship all three executables. This script
answers which do, straight from the release table, and writes the answer where a
reader can check it. It also prints the command it used, so the file is
re-derivable rather than transcribed.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TRIAGE = os.path.join(SKILL, "scripts", "triage.py")

QUERY = ("SELECT tag, build_date, prerelease, cached_path FROM releases"
         " ORDER BY build_date IS NULL, build_date")

TOOLS = ("dxc.exe", "dxl.exe", "dxa.exe", "dxcompiler.dll")


def main():
    argv = [sys.executable, TRIAGE, "sql", QUERY]
    print("$ " + subprocess.list2cmdline(["python", "triage.py", "sql", QUERY]))
    rows = json.loads(subprocess.run(argv, capture_output=True, text=True,
                                     check=True).stdout)
    print()
    header = f"{'tag':<18} {'build':<12} {'pre':<4} " + " ".join(
        f"{t:<16}" for t in TOOLS)
    print(header)
    print("-" * len(header))
    usable = []
    for r in rows:
        path = r["cached_path"]
        if not path:
            print(f"{r['tag']:<18} {str(r['build_date'] or ''):<12} "
                  f"{r['prerelease']:<4} (not cached locally)")
            continue
        d = os.path.dirname(path)
        have = {t: os.path.isfile(os.path.join(d, t)) for t in TOOLS}
        print(f"{r['tag']:<18} {str(r['build_date'] or ''):<12} "
              f"{r['prerelease']:<4} "
              + " ".join(f"{str(have[t]):<16}" for t in TOOLS))
        if have["dxc.exe"] and have["dxl.exe"] and have["dxa.exe"]:
            usable.append(r["tag"])
    print()
    print(f"releases able to run the whole dxc->dxl->dxa chain: "
          f"{len(usable)}  {usable}")
    # Self-test: this scan is an absence claim about release packaging, so make
    # it prove it can see a present file. The repo's own Debug build has all
    # three; if the detector reports otherwise it is broken, not the releases.
    local = os.path.join(os.path.abspath(os.path.join(HERE, *[".."] * 6)),
                         "build", "Debug", "bin")
    ok = all(os.path.isfile(os.path.join(local, t)) for t in TOOLS)
    print(f"detector self-test on the local Debug build ({'<repo>/build/Debug/bin'}): "
          f"{'pass -- all four found' if ok else 'FAIL -- detector is broken'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
