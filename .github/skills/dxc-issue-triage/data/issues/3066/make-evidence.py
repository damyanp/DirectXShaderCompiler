"""Auxiliary evidence generator for issue #3066.

Writes two committed captures next to this script:

  manual-case-clause-matrix.txt  -- every clause of match.json scored on its own
                                    against every capture in this directory, so
                                    the discriminating power of each control is
                                    auditable rather than asserted.
  manual-case-other-views.txt    -- the two disassembly views the issue could
                                    plausibly mean besides `dxc <src>`:
                                    `dxc -dumpbin` over a compiled container and
                                    `dxa -dumpreflection`.

Every command is echoed with subprocess.list2cmdline(argv), i.e. exactly what
was executed, with this machine's layout rewritten to <repo> so the capture
carries no absolute path.

Compiler location: set DXC_BIN to the directory holding dxc.exe / dxa.exe.
Defaults to <repo>/build/Debug/bin, located by walking up to the repository
root rather than by any absolute path.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def repo_root():
    for parent in HERE.parents:
        if (parent / ".git").exists():
            return parent
    sys.exit("could not locate the repository root from this script's location")


ROOT = repo_root()
BIN = Path(os.environ.get("DXC_BIN", ROOT / "build" / "Debug" / "bin"))
DXC = BIN / "dxc.exe"
DXA = BIN / "dxa.exe"


def flatten(pred, path="root"):
    """Yield (label, clause) for every leaf clause of match.json."""
    if pred.get("kind") in ("all_of", "any_of"):
        for i, sub in enumerate(pred["value"]):
            yield from flatten(sub, f"{path}[{i}]")
    else:
        yield path, pred


def score(clause, text):
    kind = clause["kind"]
    if kind == "contains":
        return clause["value"] in text
    if kind == "not_contains":
        return clause["value"] not in text
    if kind == "regex":
        return re.search(clause["value"], text, re.MULTILINE) is not None
    if kind == "not_regex":
        return re.search(clause["value"], text, re.MULTILINE) is None
    sys.exit(f"clause matrix does not handle kind {kind!r}")


def body(path):
    """A capture file starts with '# ' headers; score only what dxc emitted."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    i = 0
    while i < len(lines) and lines[i].startswith("#"):
        i += 1
    return "".join(lines[i:])


def clause_matrix(out):
    pred = json.loads((HERE / "match.json").read_text(encoding="utf-8"))
    clauses = list(flatten(pred))
    captures = [
        ("out-main-debug.txt", "repro", "the repro, ground truth", "expect ALL match"),
        ("variant-zi-main-debug.txt", "zi", "same repro + -Zi -Qembed_debug",
         "control: names/locations ARE printed"),
        ("variant-plain-main-debug.txt", "plain", "trivial valid shader",
         "control: constructs absent"),
        ("variant-broken-main-debug.txt", "broken", "shader that does not compile",
         "control: no disassembly emitted"),
        ("out-v1.4.1907.txt", "1.4", "the repro, oldest release",
         "scored no-repro by the scan; this says which clause"),
        ("out-v1.5.2010.txt", "1.5", "the repro, next release", "scored repro"),
        ("out-v1.9.2607.txt", "1.9", "the repro, newest release", "scored repro"),
    ]
    out.write("Per-clause scoring of match.json against every capture.\n")
    out.write("A '.' means the clause did not match; 'X' means it did.\n\n")
    out.write("captures, in column order:\n")
    for name, col, what, why in captures:
        out.write(f"  {col:<8} {name:<30} {what} -- {why}\n")
    out.write("\n")
    out.write(f"{'clause':<10}" + "".join(f"{c:>9}" for _, c, _, _ in captures)
              + "   note\n")
    texts = []
    for name, _, _, _ in captures:
        p = HERE / name
        texts.append(body(p) if p.exists() else "")
    for label, clause in clauses:
        cells = "".join(f"{('X' if score(clause, t) else '.'):>9}" for t in texts)
        note = clause.get("note", "")
        out.write(f"{label:<10}{cells}   {note}\n")
    out.write("\nA control is only meaningful if at least one clause flips; "
              "the columns above are that proof.\n")


def display(argv):
    """Echo the command with this machine's layout replaced by <repo>.

    Only rewrites arguments that name an existing file or directory, so flags
    such as -T or values such as ps_6_0 are left alone.
    """
    parts = []
    for a in argv:
        s = str(a)
        p = Path(s)
        if os.path.sep in s or (p.exists() and p.is_absolute()):
            try:
                s = "<repo>/" + p.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                pass
        parts.append(s)
    return subprocess.list2cmdline(parts)


def run(out, argv, cwd=None):
    out.write("\n$ " + display(argv) + "\n")
    proc = subprocess.run([str(a) for a in argv], cwd=str(cwd or HERE),
                          capture_output=True, text=True, errors="replace")
    out.write(f"# exit: {proc.returncode} (0x{proc.returncode & 0xFFFFFFFF:08X})\n")
    out.write(proc.stdout)
    if proc.stderr:
        out.write("--- stderr ---\n" + proc.stderr)
    return proc


def other_views(out):
    out.write("dxc -dumpbin and dxa -dumpreflection over the #3066 repro.\n")
    out.write(f"# dxc: <repo>/{DXC.relative_to(ROOT).as_posix()}\n")
    run(out, [DXC, "-T", "ps_6_0", "-E", "main", "-Fo", "repro.dxbc", "repro.hlsl"])
    run(out, [DXC, "-dumpbin", "repro.dxbc"])
    run(out, [DXA, "-dumpreflection", "repro.dxbc"])
    try:
        (HERE / "repro.dxbc").unlink()
    except OSError:
        pass


def main():
    with (HERE / "manual-case-clause-matrix.txt").open("w", encoding="utf-8",
                                                       newline="\n") as f:
        clause_matrix(f)
    with (HERE / "manual-case-other-views.txt").open("w", encoding="utf-8",
                                                     newline="\n") as f:
        other_views(f)
    print("wrote manual-case-clause-matrix.txt and manual-case-other-views.txt")


if __name__ == "__main__":
    main()
