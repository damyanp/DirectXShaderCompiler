"""#4206 release matrix: when did reflection start reporting the wrong field?

`triage.py bisect` is deliberately NOT usable here and must not be run: this
issue is registered against a harness compiler (`run-refl4206.cmd`), and bisect
substitutes each release's *dxc.exe* for the registered executable.  It would
therefore run `dxc.exe -T cs_6_0 ... ` with no reflection step at all, score
every release `no-repro`, and report a confident `never-repro'd-in-releases` --
the exact inversion SKILL.md records for #2918/#2922/#2923/#3237.  This script
is the sanctioned replacement: an explicit release matrix that holds the
harness fixed while varying each release's executable and DLL.

Two columns, because the two ask different questions:

  A  fixed reader   : release N's dxc.exe compiles; the GROUND-TRUTH dxa.exe +
                      dxcompiler.dll read the container back.  Single variable
                      = the compiler.  This is the right instrument for the
                      defect, because the used/unused bit is decided at compile
                      time in DxilLowerCreateHandleForLib::UpdateCBufferUsage
                      and stored in DXIL metadata; the reader only reports it.

  B  matched pair   : release N's dxc.exe compiles AND release N's
                      dxcompiler.dll reflects (ground-truth dxa.exe is only the
                      front end).  This is what an application shipping release
                      N actually sees, and it is the only column that can speak
                      for releases whose validator version is below 1.5 --
                      there `m_bUsageInMetadata` is false and reflection
                      recomputes usage itself in
                      DxilContainerReflection.cpp's SetCBufferUsage(), a
                      different code path from the one the issue blames.

Column B is not free of hazards: `dxa.exe` dynamically LoadLibrary()s the
dxcompiler.dll beside it, so the pairing is real (proved below by the fact that
the two columns disagree on releases where they must), but an old reflection
implementation reading its own container is still a different instrument per
row.  Every row therefore carries the predicate's INSTRUMENT SELF-TEST clause
(ProbeCoordToWorldPos must be reported used) and the per-release control
(control-noneg.hlsl, the same shader with the `- 1` removed).  A row whose
self-test fails is unmeasurable, not clean.

Scoring reuses triage.py's own predicate code -- `predicate_clause_signature`
and `classify` -- rather than a second regex implementation, so this matrix
cannot drift from `match.json` / `match-falsenegative.json`.

The uFlags extractor has a self-consistency line (SKILL.md #2923: "a harness
that can return 'nothing here' and 'nothing matched' through the same channel
will eventually be believed"): it prints REFL4206-PARSE-WARNING and a count
whenever it does not find all three expected $Globals variables.

Usage:  python measure-history.py [--tag v1.6.2112 ...]
Writes: manual-case-release-history.txt
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import triage  # noqa: E402

ISSUE = 4206
HARNESS = os.path.join(HERE, "run-refl4206.cmd")
GT_BIN = os.path.join(REPO, "build", "Debug", "bin")
SCRATCH = os.path.join(HERE, "scratch")
VARS = ("WorldPosToProbeCoord", "ProbeCoordToWorldPos", "SkyLightColor")
PREDICATES = ("match.json", "match-falsenegative.json")


def display(path):
    p = os.path.abspath(path)
    marker = os.sep + "DirectXShaderCompiler" + os.sep
    i = p.find(marker)
    return "<repo>" + p[i + len(marker) - 1:] if i >= 0 else p


def stable_releases():
    db = triage.DB
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    rows = c.execute(
        "SELECT tag, build_date, cached_path, prerelease, bisectable"
        " FROM releases WHERE tag <> '' AND asset_name IS NOT NULL"
        " ORDER BY build_date").fetchall()
    c.close()
    return rows


def uflags(text):
    """Pull the three $Globals variables' uFlags out of a reflection dump."""
    found = {}
    for name in VARS:
        m = re.search(
            r"D3D12_SHADER_VARIABLE_DESC: Name: " + name
            + r"\n(?:[^\n]*\n){0,6}?[^\n]*uFlags: ([^\n]*)", text)
        if m:
            found[name] = m.group(1).strip()
    if len(found) != len(VARS):
        print(f"REFL4206-PARSE-WARNING: {len(found)}/{len(VARS)} $Globals "
              f"variables parsed from this dump", flush=True)
    return found


def run_case(dxc_exe, reader_dir, shader, args):
    env = dict(os.environ)
    env["DXC_EXE"] = dxc_exe
    env["DXC_READER"] = os.path.join(reader_dir, "dxa.exe")
    argv = [HARNESS] + args
    printed = subprocess.list2cmdline(
        [display(HARNESS)] + args)
    header = (f"$ set DXC_EXE={display(dxc_exe)}\n"
              f"$ set DXC_READER={display(env['DXC_READER'])}\n"
              f"$ {printed}\n")
    p = subprocess.run(argv, cwd=SCRATCH, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    text = (p.stdout or "") + (p.stderr or "")
    return p.returncode, header + text, text


def reader_dir_for(tag, release_dxc):
    """Ground-truth dxa.exe beside a chosen dxcompiler.dll.

    dxa.exe LoadLibrary()s "dxcompiler.dll", and Windows searches the
    executable's own directory first, so copying the front end next to a
    release DLL pairs them.  That this actually takes effect is not assumed:
    the run's own output differs from the fixed-reader column wherever the two
    implementations differ (v1.4.1907's DLL reports `Creator: <nullptr>` and
    `InstructionCount: 0` on a container the ground-truth reader reads fully).
    """
    d = os.path.join(SCRATCH, "reader-" + tag)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(os.path.join(GT_BIN, "dxa.exe"), d)
    shutil.copy2(os.path.join(os.path.dirname(release_dxc), "dxcompiler.dll"),
                 d)
    return d


def score(text, rc):
    out = {}
    for mf in PREDICATES:
        clauses, _ = triage.predicate_clause_signature(
            ISSUE, text, rc, False, mf)
        verdict = triage.classify(ISSUE, text, rc, False, mf)
        out[mf] = {"clauses": ["1" if c else "0" for c in clauses],
                   "verdict": verdict}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", action="append", default=None)
    ap.add_argument("--out", default=os.path.join(
        HERE, "manual-case-release-history.txt"))
    a = ap.parse_args()

    os.makedirs(SCRATCH, exist_ok=True)
    for name in ("repro.hlsl", "control-noneg.hlsl"):
        shutil.copy2(os.path.join(HERE, name), SCRATCH)

    rows = stable_releases()
    skipped = [f"{r['tag']} (prerelease)" for r in rows
               if r["prerelease"] and not r["bisectable"]]
    rows = [r for r in rows if r["bisectable"]]
    if a.tag:
        rows = [r for r in rows if r["tag"] in a.tag]

    log = []
    table = []

    def emit(s=""):
        print(s, flush=True)
        log.append(s)

    emit("# #4206 release matrix -- generated by measure-history.py")
    emit("# Every command below was printed with subprocess.list2cmdline"
         " immediately before it ran.")
    emit(f"# ground-truth reader: {display(GT_BIN)}"
         " (dxa.exe + dxcompiler.dll)")
    emit(f"# stable releases probed: {len(rows)}")
    emit(f"# excluded by prerelease policy: "
         f"{', '.join(skipped) if skipped else 'none'}")
    emit("# NOTE: triage.py bisect is not applicable to this issue and was not"
         " run; see this file's generator docstring.")
    emit()

    subjects = [("repro", "repro.hlsl",
                 ["-T", "cs_6_0", "-E", "ResampleCS", "repro.hlsl"]),
                ("control-noneg", "control-noneg.hlsl",
                 ["-T", "cs_6_0", "-E", "ResampleCS", "control-noneg.hlsl"])]

    cases = [("main-debug", None, GT_BIN, os.path.join(GT_BIN, "dxc.exe"))]
    for r in rows:
        cases.append((r["tag"], r["build_date"], None, r["cached_path"]))

    for tag, date, fixed_reader_dir, dxc_exe in cases:
        if not dxc_exe or not os.path.exists(dxc_exe):
            emit(f"## {tag}: no cached dxc.exe; skipped")
            continue
        for col, reader in (("A-fixed-reader", GT_BIN),
                            ("B-matched-pair",
                             GT_BIN if tag == "main-debug"
                             else reader_dir_for(tag, dxc_exe))):
            for label, shader, args in subjects:
                emit(f"## {tag} ({date or 'ground truth'})"
                     f" | column {col} | {label}")
                rc, block, text = run_case(dxc_exe, reader, shader, args)
                emit(block.rstrip("\n"))
                emit(f"# harness exit: 0x{rc & 0xFFFFFFFF:08X}")
                flags = uflags(text)
                for name in VARS:
                    emit(f"# uFlags[{name}] = {flags.get(name, '<absent>')}")
                s = score(text, rc)
                for mf in PREDICATES:
                    emit(f"# {mf}: clauses={''.join(s[mf]['clauses'])}"
                         f" verdict={s[mf]['verdict']}")
                emit()
                table.append({"tag": tag, "date": date, "column": col,
                              "subject": label, "exit": rc, "uflags": flags,
                              "scores": {mf: s[mf] for mf in PREDICATES}})

    emit("# ==================== SUMMARY ====================")
    emit("# uFlags columns: U = D3D_SVF_USED, 0 = not used, ? = absent")
    emit("# WPTC = WorldPosToProbeCoord (READ by the shader)")
    emit("# PCTW = ProbeCoordToWorldPos (READ by the shader; instrument"
         " self-test)")
    emit("# SLC  = SkyLightColor        (NEVER read by the shader)")
    emit()
    emit(f"{'release':16} {'date':11} {'col':15} {'subject':14}"
         f" {'WPTC':5} {'PCTW':5} {'SLC':5} {'match':10} {'falseneg':10}")
    for t in table:
        def f(n):
            v = t["uflags"].get(n)
            if v is None:
                return "?"
            return "U" if "D3D_SVF_USED" in v else ("0" if v == "0" else v)
        emit(f"{t['tag']:16} {(t['date'] or 'main'):11} {t['column']:15}"
             f" {t['subject']:14} {f(VARS[0]):5} {f(VARS[1]):5}"
             f" {f(VARS[2]):5} {t['scores']['match.json']['verdict']:10}"
             f" {t['scores']['match-falsenegative.json']['verdict']:10}")

    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    with open(os.path.splitext(a.out)[0] + ".json", "w",
              encoding="utf-8") as fh:
        json.dump(table, fh, indent=2)
    print("\nwrote " + display(a.out))


if __name__ == "__main__":
    main()
