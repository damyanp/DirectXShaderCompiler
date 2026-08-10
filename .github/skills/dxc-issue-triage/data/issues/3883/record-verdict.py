"""Record the verdict for #3883 through triage.py.

Written as a script rather than typed into PowerShell because the prose fields contain
characters PowerShell rewrites silently in a double-quoted string -- `$` expands to nothing
and a backtick starts an escape -- and SKILL.md records both landing in committed artifacts.
Running the arguments through a Python list removes the shell from the path entirely.

Usage:  python record-verdict.py
"""

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
TRIAGE = HERE.parents[2] / "scripts" / "triage.py"

SUMMARY = (
    "Still reproduces on main (1.9.0.5433, 13730886e) and on all 20 stable release binaries "
    "from v1.4.1907 to v1.9.2607: an undefined cbuffer index reaches TranslateCBGepLegacy's "
    "dyn_cast<Constant> and getUniqueInteger() asserts on it (Debug, 0xE0000001) or a "
    "cast<StructType> under it fails (Release). The self-initialisation in the title is not "
    "required -- a plain uninitialised uint fails identically and prints nothing pointing at "
    "the variable -- and FXC rejects both spellings with error X4000."
)

EXPECTED = (
    "dxc fails internally on the repro rather than diagnosing it: a trapped or thrown assert "
    "in a Debug build, an access violation or a cast-of-incompatible-type E_FAIL in a "
    "Release build. An ordinary diagnosed error would be the fix, not the symptom."
)

ARGV = [
    sys.executable, str(TRIAGE), "verdict", "--issue", "3883",
    "--batch", "batch-011",
    "--status", "repros",
    "--repro-quality", "complete",
    "--history", "always-repro'd",
    "--confidence", "high",
    "--suggested-action", "still-valid-keep-open",
    "--summary", SUMMARY,
    "--expected-symptom", EXPECTED,
    "--notes-path", "issues/3883/notes.md",
    "--triaged-with-commit", "13730886e",
    "--triaged-by", "GitHub Copilot CLI (claude-opus-4.6)",
    "--labels-now", "bug,crash,incorrect-code",
    "--labels-add", "fxc-disagrees,diagnostic",
    "--godbolt-url", "https://godbolt.org/z/6c9h3r4a3",
]

if __name__ == "__main__":
    raise SystemExit(subprocess.run(ARGV).returncode)
