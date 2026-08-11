"""Records the two facts about the OPTIMISATION PIPELINE that issue 4701's notes rely on.

Both are claims about how the compiler was invoked, and a claim about an invocation that is
only asserted in prose is checked by nobody.  So both are captured here by running the
compiler and echoing the exact command line via subprocess.list2cmdline.

  1. What optimisation level the measurement was taken at.  The issue body gives no command
     line, and DXC's default is NOT -Od, so "it is not optimised" has to be qualified by the
     level.  `dxc --help` states the default.

  2. Which passes actually run.  `-Odump` prints the pass pipeline, which is what lets the
     write-up name -globalopt / -globaldce / -dse / -adce / -static-global-to-alloca as the
     transforms that had the opportunity and declined it, rather than guessing at pass names
     from the source tree.

Result is recorded in manual-case-pipeline.txt.  Nothing is written outside issues/4701/.

Run:  python pipeline-probe.py
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import triage  # noqa: E402

PASSES_OF_INTEREST = [
    "globalopt", "globaldce", "dse", "adce", "static-global-to-alloca",
    "sroa", "scalarrepl", "hlsl-dxil-tgsm", "simplifycfg",
]


def run(argv, log):
    log.append("$ " + triage.redact_paths(subprocess.list2cmdline(argv)))
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                       errors="replace", timeout=300)
    return p, triage.redact_paths((p.stdout or "") + (p.stderr or ""))


def main():
    c = triage.con()
    exe = c.execute(
        "SELECT exe_path FROM compilers WHERE id = 'main-debug'").fetchone()["exe_path"]

    log = ["Issue 4701 -- optimisation level in use, and the pass pipeline that runs.",
           "Compiler: main-debug (the ground-truth build).",
           ""]

    # ---- 1. default optimisation level, straight from the compiler's own help text --------
    log.append("=" * 74)
    log.append("1. Which optimisation level is the default?")
    log.append("=" * 74)
    p, out = run([exe, "--help"], log)
    lines = [ln.rstrip() for ln in out.splitlines()
             if re.match(r"\s*-(O[0-3d]|Od)\b", ln)]
    log.append("[exit] %d" % p.returncode)
    log.append("(lines mentioning an -O flag, verbatim)")
    log.extend("  " + ln.strip() for ln in lines)
    default_line = [ln for ln in lines if "Default" in ln]
    log.append("")
    log.append("VERDICT: " + (
        "default optimisation level is stated by the compiler as: "
        + default_line[0].strip() if default_line else
        "could not find a line marking a default -- do NOT claim one"))
    log.append("")

    # ---- 2. the pass pipeline ------------------------------------------------------------
    log.append("=" * 74)
    log.append("2. Which passes run for the reported command line?")
    log.append("=" * 74)
    p, out = run([exe, "-T", "cs_6_0", "-E", "main", "-Odump", "repro.hlsl"], log)
    log.append("[exit] %d" % p.returncode)
    log.append("--- full -Odump output ---")
    log.append(out.rstrip())
    log.append("--- end -Odump output ---")
    log.append("")

    lowered = out.lower()
    log.append("Passes the write-up names, and whether -Odump actually lists them:")
    missing = []
    for name in PASSES_OF_INTEREST:
        present = ("-" + name) in lowered
        log.append("  %-26s %s" % (name, "present" if present else "ABSENT"))
        if not present:
            missing.append(name)
    log.append("")
    log.append("Only the passes marked `present` may be named in the write-up as having had")
    log.append("the opportunity to delete the dead group-shared array.")
    if missing:
        log.append("ABSENT here means only 'not in this pipeline listing under this name'.")

    text = "\n".join(log) + "\n"
    dest = os.path.join(HERE, "manual-case-pipeline.txt")
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
