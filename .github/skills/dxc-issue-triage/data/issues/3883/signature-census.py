"""Tabulate how the SAME defect signs itself across the release history, for issue #3883.

Reads every `out-*.txt` in this directory -- the captures `triage.py run`/`bisect` wrote --
and prints one row per compiler: the exit status in hex, whether `is_internal_failure` scored
it a reproduction, and the first non-empty line of stderr. The point of the table is the
method claim in notes.md: five distinct signatures across one never-fixed bug, so a predicate
keyed to the crash *text* and a predicate keyed to the exit *code alone* each score part of
the history clean.

Nothing here re-runs the compiler; it only reformats committed captures, so the counts a
reader sees can be re-derived from the same files.

Usage:  python signature-census.py > manual-case-signature-census.txt
"""

import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
# Build order comes from the database (build date encoded in the asset name), not from the
# tag string: servicing patches ship long after the snapshot they were built from.
ORDER_SQL = "SELECT tag FROM releases WHERE build_date IS NOT NULL ORDER BY build_date, tag"


def release_order() -> list:
    triage = HERE.parents[2] / "scripts" / "triage.py"
    argv = [sys.executable, str(triage), "sql", ORDER_SQL]
    # Echo what is about to run, but anchored on the repository name rather than on one
    # machine's absolute layout: a committed capture must not carry a local path.
    shown = subprocess.list2cmdline(["python", str(triage), "sql", ORDER_SQL])
    print("# $ " + re.sub(r"^.*?DirectXShaderCompiler[\\/]", "<repo>/", shown))
    out = subprocess.run(argv, capture_output=True, text=True, check=True).stdout
    return re.findall(r'"tag":\s*"([^"]+)"', out)


def field(text: str, name: str) -> str:
    m = re.search(rf"^# {name}: (.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def first_stderr_line(text: str) -> str:
    tail = text.split("--- stderr ---", 1)
    if len(tail) < 2:
        return ""
    for line in tail[1].splitlines():
        if line.strip():
            return line.strip()
    return "(stderr completely empty)"


def main() -> int:
    order = release_order() + ["main-debug"]
    rows = []
    for path in sorted(HERE.glob("out-*.txt")):
        text = path.read_text(errors="replace")
        cid = path.stem[len("out-") :]
        code = int(field(text, "exit") or 0)
        rows.append((cid, f"0x{code & 0xFFFFFFFF:08X}", field(text, "verdict"),
                     first_stderr_line(text)))
    rows.sort(key=lambda r: order.index(r[0]) if r[0] in order else 999)

    print(f"# {len(rows)} captures of the repro, in release build-date order, main-debug last.")
    print(f"# {sum(1 for r in rows if r[2] == 'repro')} of {len(rows)} scored `repro`.")
    print()
    print(f"{'compiler':<16} {'exit':<12} {'scored':<8} first stderr line")
    print(f"{'-' * 16} {'-' * 12} {'-' * 8} {'-' * 60}")
    for cid, code, verdict, line in rows:
        print(f"{cid:<16} {code:<12} {verdict:<8} {line[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
