"""Measure issue 7300's repro at a candidate fix commit and its parent.

The stable-release sweep dates the fix to a release window; it cannot name the
commit that closed it. This harness builds nothing: it takes one already-built
dxc.exe per commit, runs the issue's exact cmd.txt line against each, and writes
one capture recording the executed command line, the commit, the self-reported
version, the native exit status and the full output.

Usage:
  python measure-fix-commit.py --case <label>=<sha>=<path-to-dxc.exe> [...] \
      [--out manual-case-fix-commit.txt]

Every path in the output is rewritten to a placeholder derived from the case
label, so the capture is machine-independent (see check_paths.py).
"""

import argparse
import datetime
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def read_cmd() -> list[str]:
    lines = [l.strip() for l in (HERE / "cmd.txt").read_text().splitlines()]
    lines = [l for l in lines if l and not l.startswith("#")]
    if len(lines) != 1:
        raise SystemExit(f"expected exactly one command in cmd.txt, found {len(lines)}")
    return lines[0].split()


def run(argv: list[str]) -> tuple[str, int]:
    proc = subprocess.run(argv, cwd=HERE, capture_output=True, text=True, errors="replace")
    return proc.stdout + proc.stderr, proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", required=True,
                    help="<label>=<commit-sha>=<path to dxc.exe>")
    ap.add_argument("--variant", action="append", default=[],
                    help="<label>=<full argv after the exe>; run every case with these "
                         "arguments as well, as a control")
    ap.add_argument("--out", default="manual-case-fix-commit.txt")
    args = ap.parse_args()

    cmd = read_cmd()
    redactions: list[tuple[str, str]] = []
    cases = []
    for spec in args.case:
        label, sha, exe = spec.split("=", 2)
        exe_path = pathlib.Path(exe).resolve()
        cases.append((label, sha, exe_path))
        # the build tree root is the grandparent of bin/<config>/dxc.exe
        for ancestor in exe_path.parents:
            if (ancestor / "CMakeCache.txt").exists():
                redactions.append((str(ancestor.parent), f"<{label}-worktree>"))
                break
    redactions.append((str(HERE), "<issue-dir>"))

    def scrub(text: str) -> str:
        for real, placeholder in redactions:
            text = text.replace(real, placeholder)
            text = text.replace(real.replace("\\", "/"), placeholder)
            text = text.replace(real.replace("\\", "\\\\"), placeholder)
        return text

    out = [
        "# issue: 7300",
        "# purpose: direct before/after measurement at a candidate fix commit",
        "# generated-by: measure-fix-commit.py",
        f"# ran: {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}",
        f"# repro-cmd: {' '.join(cmd)}",
        "",
    ]

    for label, sha, exe_path in cases:
        version_argv = [str(exe_path), "--version"]
        version_text, version_status = run(version_argv)
        repro_argv = [str(exe_path)] + cmd
        repro_text, repro_status = run(repro_argv)
        out += [
            f"=== case: {label} ===",
            f"[commit] {sha}",
            f"$ {subprocess.list2cmdline(version_argv)}",
            f"[exit] {version_status}",
            version_text.rstrip("\n"),
            "",
            f"$ {subprocess.list2cmdline(repro_argv)}",
            f"[exit] {repro_status} (0x{repro_status & 0xFFFFFFFF:08X})",
            "--- output ---",
            repro_text.rstrip("\n"),
            "",
        ]
        print(f"{label} {sha[:9]} repro exit {repro_status} "
              f"(0x{repro_status & 0xFFFFFFFF:08X})")

        for spec in args.variant:
            vlabel, vargs = spec.split("=", 1)
            vargv = [str(exe_path)] + vargs.split()
            vtext, vstatus = run(vargv)
            out += [
                f"--- control: {vlabel} ---",
                f"$ {subprocess.list2cmdline(vargv)}",
                f"[exit] {vstatus} (0x{vstatus & 0xFFFFFFFF:08X})",
                vtext.rstrip("\n")[:2000],
                "",
            ]
            print(f"{label} {sha[:9]} control {vlabel} exit {vstatus} "
                  f"(0x{vstatus & 0xFFFFFFFF:08X})")

    (HERE / args.out).write_text(scrub("\n".join(out)) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
