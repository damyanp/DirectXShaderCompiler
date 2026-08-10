"""Auxiliary evidence generator for issue #3872.

Writes three committed captures next to this script:

  manual-case-clause-matrix.txt  -- every clause of match.json and of
                                    match-portable.json scored on its own
                                    against every capture in this directory.
                                    An all_of with ten clauses otherwise hides
                                    WHICH clause moved, and for this issue that
                                    matters: the first `bisect --linear` run
                                    reported v1.4.1907 as no-repro, and the
                                    matrix is what shows the clause that failed
                                    there was the disassembler-spelling clause,
                                    not the acceptance clause.
  manual-case-dxv.txt            -- the standalone DXIL validator, dxv.exe, run
                                    over containers built from the repro with
                                    validation disabled at compile time (-Vd).
                                    `dxc` links the same validator, so this is a
                                    cross-check against a harness artefact
                                    rather than an independent witness; it is
                                    here because the issue is labelled
                                    `validation` and "the validator does not
                                    catch it either" should be measured, not
                                    inferred from a shared code path. A positive
                                    control (control-valfail.hlsl, whose root
                                    signature does not cover its SRV) is run
                                    through the identical steps, so dxv's
                                    silence on the repro is readable.
  manual-case-ce-local.txt       -- the five Compiler Explorer panes' exact
                                    command lines, replayed against the local
                                    build. CE runs Linux Release builds of
                                    other commits; this is what ties the
                                    published link back to the compiler this
                                    triage actually measured.

Every command is echoed with subprocess.list2cmdline(argv), i.e. exactly what
was executed, with this machine's layout rewritten to <repo> so the capture
carries no absolute path.

Compiler location: set DXC_BIN to the directory holding dxc.exe / dxv.exe.
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
DXV = BIN / "dxv.exe"
SCRATCH = HERE / "dxv-out"


def flatten(pred, path="root"):
    """Yield (label, clause) for every leaf clause of a predicate file."""
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


CAPTURES = [
    ("out-main-debug.txt", "main", "the repro, ground truth",
     "expect ALL match"),
    ("variant-ce-main-debug.txt", "ce",
     "the source published to Compiler Explorer",
     "the link is not an untested variant: expect ALL match"),
    ("variant-nosr-main-debug.txt", "nosr",
     "same pipeline, arbitrary RATE semantic",
     "control: the disputed semantic is absent"),
    ("variant-diagnosed-main-debug.txt", "diag",
     "same semantic in NA cells of the same stages",
     "control: DXC does diagnose this, these command lines reach it"),
    ("variant-gsvin-main-debug--match-gsvin.txt", "gsvin",
     "the separate gs_6_4 open-question probe",
     "control: the repro predicate is scoped to its own five compiles"),
    ("out-v1.4.1907.txt", "1.4", "the repro, oldest release",
     "scored no-repro by match.json; this says which clause"),
    ("out-v1.5.2010.txt", "1.5", "the repro, next release", "scored repro"),
    ("out-v1.6.2104.txt", "1.6", "the repro, release nearest the report",
     "scored repro"),
    ("out-v1.9.2607.txt", "1.9", "the repro, newest release", "scored repro"),
]


def clause_matrix(out):
    out.write("Per-clause scoring of the two repro predicates for issue #3872\n")
    out.write("against every capture that uses the repro command list.\n")
    out.write("A '.' means the clause did not match; 'X' means it did.\n\n")
    out.write("captures, in column order:\n")
    for name, col, what, why in CAPTURES:
        out.write(f"  {col:<6} {name:<32} {what} -- {why}\n")
    out.write("\n")
    texts = []
    for name, _, _, _ in CAPTURES:
        p = HERE / name
        texts.append(body(p) if p.exists() else "")
        if not p.exists():
            out.write(f"  MISSING: {name} (scored as empty)\n")
    for pred_name in ("match.json", "match-portable.json"):
        pred = json.loads((HERE / pred_name).read_text(encoding="utf-8"))
        clauses = list(flatten(pred))
        out.write(f"\n=== {pred_name} ({len(clauses)} clauses) ===\n\n")
        out.write(f"{'clause':<10}"
                  + "".join(f"{c:>7}" for _, c, _, _ in CAPTURES)
                  + "   note\n")
        for label, clause in clauses:
            cells = "".join(f"{('X' if score(clause, t) else '.'):>7}"
                            for t in texts)
            out.write(f"{label:<10}{cells}   {clause.get('note', '')}\n")
    out.write("\nA control is only meaningful if at least one clause flips; "
              "the columns above are that proof.\n")
    out.write("Read the 1.4 column against the 1.5 column: the acceptance "
              "clauses hold in both.\n")


def display(argv):
    """Echo the command with this machine's layout replaced by <repo>."""
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


CASES = [
    ("repro", "repro.hlsl", "vs_6_4", "VSMain"),
    ("repro", "repro.hlsl", "hs_6_4", "HSCPInMain"),
    ("repro", "repro.hlsl", "hs_6_4", "HSCPOutMain"),
    ("repro", "repro.hlsl", "ds_6_4", "DSCPInMain"),
    ("repro", "repro.hlsl", "ds_6_4", "DSOutMain"),
    ("control", "control-valfail.hlsl", "vs_6_4", "VSMain"),
    ("control", "control-valfail.hlsl", "hs_6_4", "HSCPInMain"),
    ("control", "control-valfail.hlsl", "ds_6_4", "DSOutMain"),
]


def dxv_cases(out):
    out.write("Does the DXIL validator reject SV_ShadingRate in the four\n")
    out.write("disputed signature positions when it is asked on its own?\n\n")
    out.write("Each case compiles with -Vd (validation disabled at compile\n")
    out.write("time, so a container is produced either way) and then hands the\n")
    out.write("container to dxv.exe.  dxv prints nothing and exits 0 when the\n")
    out.write("module validates.  Silence is only readable next to a control\n")
    out.write("that shows dxv would speak: control-valfail.hlsl is the same\n")
    out.write("pipeline with a root signature that does not cover its SRV, and\n")
    out.write("it goes through the identical two steps.\n\n")
    out.write("dxv links the same lib/DxilValidation that dxc calls inline, so\n")
    out.write("this is a cross-check against a harness artefact, NOT a second\n")
    out.write("independent implementation.\n")
    out.write(f"# dxc: <repo>/{DXC.relative_to(ROOT).as_posix()}\n")
    out.write(f"# dxv: <repo>/{DXV.relative_to(ROOT).as_posix()}\n")
    SCRATCH.mkdir(exist_ok=True)
    summary = []
    for group, src, profile, entry in CASES:
        obj = SCRATCH / f"{Path(src).stem}-{entry}.dxbc"
        out.write(f"\n--- {group}: {profile} {entry} ({src}) ---\n")
        c = run(out, [DXC, "-T", profile, "-E", entry, "-Vd", "-Fo", obj, src])
        if c.returncode != 0:
            summary.append((group, profile, entry, "compile failed", ""))
            continue
        v = run(out, [DXV, obj])
        verdict = "dxv accepted" if v.returncode == 0 else "dxv rejected"
        summary.append((group, profile, entry, verdict,
                        (v.stdout + v.stderr).strip().splitlines()[:1]))
    out.write("\n\nsummary\n")
    for group, profile, entry, verdict, first in summary:
        head = first[0] if first else ""
        out.write(f"  {group:<8} {profile:<8} {entry:<14} {verdict:<14} {head}\n")
    out.write("\nRead the control rows first: if they do not say 'dxv "
              "rejected', the repro rows say nothing.\n")


CE_PANES = [
    ("accepted", "ds_6_4", "DSOutMain"),
    ("control ", "ds_6_4", "DSInBad"),
    ("accepted", "hs_6_4", "HSCPInMain"),
    ("control ", "hs_6_4", "HSPCOutBad"),
]


def ce_local(out):
    out.write("The published Compiler Explorer link compiles "
              "godbolt-source.hlsl in five panes.\n")
    out.write("CE runs Linux Release builds of dxc_trunk and dxc_1_6_2112; "
              "this replays the same\n")
    out.write("command lines against the local build, so the link and this "
              "triage measure the same\n")
    out.write("thing. The fifth pane is an old release and has no local "
              "counterpart -- the release\n")
    out.write("history is covered by `triage.py bisect` instead.\n")
    out.write("Read the 'control' rows first: they are the same compiler and "
              "the same stage as the\n")
    out.write("row above them, with the semantic moved into a cell the table "
              "already marks NA.\n")
    out.write(f"# dxc: <repo>/{DXC.relative_to(ROOT).as_posix()}\n")
    summary = []
    for role, profile, entry in CE_PANES:
        out.write(f"\n--- {role}: {profile} {entry} ---\n")
        p = run(out, [DXC, "-T", profile, "-E", entry, "godbolt-source.hlsl"])
        if p.returncode == 0:
            said = "accepted, no diagnostic"
        else:
            said = next((ln for ln in (p.stdout + p.stderr).splitlines()
                         if "error" in ln), "failed")
        summary.append((role, profile, entry, said))
    out.write("\n\nsummary\n")
    for role, profile, entry, said in summary:
        out.write(f"  {role} {profile:<8} {entry:<14} {said}\n")


def main():
    for tool in (DXC, DXV):
        if not tool.exists():
            sys.exit(f"{tool} not found; set DXC_BIN to the directory holding it")
    with open(HERE / "manual-case-clause-matrix.txt", "w", encoding="utf-8",
              newline="\n") as out:
        clause_matrix(out)
    with open(HERE / "manual-case-dxv.txt", "w", encoding="utf-8",
              newline="\n") as out:
        dxv_cases(out)
    with open(HERE / "manual-case-ce-local.txt", "w", encoding="utf-8",
              newline="\n") as out:
        ce_local(out)
    print("wrote manual-case-clause-matrix.txt, manual-case-dxv.txt and "
          "manual-case-ce-local.txt")


if __name__ == "__main__":
    main()
