#!/usr/bin/env python3
"""Evidence-gathering harness driver for DXC issue #5173
("IDxcCursor misses semantics").

Builds (if needed, using the same isense_probe.cpp committed beside this
script) and runs the standalone isense_probe harness against a given
dxcompiler.dll, capturing the exact command line and full output to
manual-case-<label>.txt (or variant-<label>.txt with --prefix variant) next
to this script. Every manual-case-*.txt/variant-*.txt in this directory was
produced by an invocation of this script; none were hand-typed. Every
capture is stamped with `# variant: <label> (<source file>)`, the same
header key `triage.py`'s own labelled `run --shader` uses, so
`triage.py audit` recognises every `.hlsl` in this directory as backed by a
tool-made capture rather than one that exists only in a hand-run harness.

The harness only loads the target dxcompiler.dll at runtime via
dxcapi.use.h's SpecificDllLoader (LoadLibrary + GetProcAddress) and drives
the public IDxcIntelliSense/IDxcIndex/IDxcTranslationUnit/IDxcCursor COM
interfaces. No DXC source is modified or rebuilt by this script; it only
compiles the small standalone harness, which is not part of the DXC build.

Usage:
    python measure.py --dxcompiler <path\\to\\dxcompiler.dll> --label <label>
"""
import argparse
import subprocess
import sys
from pathlib import Path

ISSUE_DIR = Path(__file__).resolve().parent
SKILL_ROOT = ISSUE_DIR.parents[2]  # .../.github/skills/dxc-issue-triage
REPO_ROOT = ISSUE_DIR.parents[5]  # repository root
SCRATCH_DIR = SKILL_ROOT / ".cache" / "scratch" / "5173"
PROBE_SRC = ISSUE_DIR / "isense_probe.cpp"
PROBE_EXE = SCRATCH_DIR / "isense_probe.exe"
REPRO = ISSUE_DIR / "repro.hlsl"
VCVARS = (
    r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\VC\Auxiliary"
    r"\Build\vcvars64.bat"
)
INCLUDE_DIR = REPO_ROOT / "include"


def redact(text):
    """Replace this checkout's absolute repo root with '<repo>' so captured
    output is portable across machines (matches the workspace convention used
    elsewhere in this skill, e.g. triage.py's display_exe)."""
    return text.replace(str(REPO_ROOT), "<repo>").replace(
        str(REPO_ROOT).replace("\\", "\\\\"), "<repo>"
    )


def ensure_built():
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    if PROBE_EXE.exists() and PROBE_EXE.stat().st_mtime >= PROBE_SRC.stat().st_mtime:
        return
    build_cmd = (
        f'call "{VCVARS}" >nul && cl /nologo /EHsc /std:c++17 '
        f'/I "{INCLUDE_DIR}" "{PROBE_SRC}" /link ole32.lib oleaut32.lib '
        f'/out:"{PROBE_EXE}"'
    )
    print(f"# build: {build_cmd}")
    result = subprocess.run(
        ["cmd.exe", "/c", build_cmd],
        cwd=str(SCRATCH_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not PROBE_EXE.exists():
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit("build failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dxcompiler", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument(
        "--source",
        default=str(REPRO),
        help="Source file to probe (default: repro.hlsl next to this script)",
    )
    ap.add_argument(
        "--prefix",
        default="manual-case",
        choices=["manual-case", "variant"],
        help="Use 'variant' for a control input, 'manual-case' (default) for "
        "a primary-repro probe against a given compiler/release.",
    )
    ap.add_argument(
        "--expect",
        default=None,
        help="Free-text description of the result this label is expected to "
        "show, stamped verbatim into the capture as `# expect:` for a human "
        "reader. This harness has no `match.json` predicate for "
        "`triage.py reindex` to re-check it against (see notes.md); the "
        "field is documentary, matching the already-measured/published "
        "result rather than an unverified prediction.",
    )
    args = ap.parse_args()

    ensure_built()

    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = ISSUE_DIR / source_path

    argv = [str(PROBE_EXE), args.dxcompiler, str(source_path)]
    cmdline = subprocess.list2cmdline(argv)
    print("# command:", cmdline)
    result = subprocess.run(argv, capture_output=True, text=True)

    out_path = ISSUE_DIR / f"{args.prefix}-{args.label}.txt"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            redact(
                f"# generator: measure.py --dxcompiler {args.dxcompiler} "
                f"--label {args.label} --source {args.source} "
                f"--prefix {args.prefix}\n"
            )
        )
        f.write(redact(f"# command: {cmdline}\n"))
        f.write(f"# process-exit-code: {result.returncode}\n")
        # `triage.py`'s own labelled runs always stamp `# variant: <label>
        # (<subject>)`, which is what `triage.py audit` scans every
        # `variant-*.txt` for to tell a tool-made capture from a shader
        # nobody ran through this generator. Every invocation of this script
        # is labelled (`--label` is required), so stamp the same header key
        # here too -- on both prefixes, since the marker identifies the
        # subject file, not the manual-case/variant distinction.
        f.write(f"# variant: {args.label} ({source_path.name})\n")
        if args.expect:
            f.write(f"# expect: {args.expect}\n")
        f.write("# stdout:\n")
        f.write(redact(result.stdout))
        if result.stderr:
            f.write("# stderr:\n")
            f.write(redact(result.stderr))
    print(f"wrote {out_path} (exit {result.returncode})")


if __name__ == "__main__":
    main()
