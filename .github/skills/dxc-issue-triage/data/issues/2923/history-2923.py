"""Release history probe for microsoft/DirectXShaderCompiler#2923.

`triage.py bisect` cannot drive this issue: it resolves a release tag to that
release's `dxc.exe` and runs `cmd.txt` against it, but the symptom only appears
after `dxa` + `dxopt` + the PIX passes have run. So the release scan is done
here and written out by hand as `manual-case-history.txt`, per SKILL.md's rule
for a hand-run matrix ("every attempt's command and exit status").

For each release it runs the same pipeline as run-2923.cmd, but with

  * the shader compiled by THAT release's dxc.exe          (PIX_DXC)
  * the PIX passes run out of THAT release's dxcompiler.dll (PIX_DLL, via
    `dxopt -external <dll> -external-fn DxcCreateInstance`)

and only the container-surgery/disassembly steps (`dxa`, `opt -S`) taken from
the local build, since those are format operations, not the code under test.

Two signatures are recorded per probe, because they do not have the same
history:

  predicate  match.json -- a source variable is given PIX virtual registers
             that then receive no writes at all. This is the strong signature:
             those are the registers PIX reads for that variable.
  test       whether the assertions PixStructAnnotation_SequentialFloatN makes
             would all hold. This is the issue's own reproduction instruction
             ("run the unit test"), but it is a weaker signal -- a shader whose
             numbering is self-consistent can still fail it -- so it is
             recorded rather than matched on.

The verbatim unit-test shader is run at every release too, so a release where
the control also trips the predicate would show up as a predicate failure
rather than being misread as history.

Usage:  python history-2923.py            (writes manual-case-history.txt)
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import triage  # noqa: E402

DRIVER = os.path.join(HERE, "run-2923.cmd")
CASES = [("repro.hlsl", "-Od"), ("repro.hlsl", "-O1"),
         ("control-no-subroutine.hlsl", "-Od"),
         ("control-no-subroutine.hlsl", "-O1")]


def probe(dxc, dll, shader, opt):
    env = dict(os.environ)
    env["PIX_DXC"] = dxc
    env["PIX_DLL"] = dll
    p = subprocess.run([DRIVER, shader, opt], cwd=HERE, env=env,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def verdict(out, rc):
    if "PIX-2923: PARSE-WARNING" in out:
        return "parse-warning", "?"
    test = "test-FAILS" if "FAIL" in out else "test-passes"
    if "PIX-2923: DECLARED-BUT-UNWRITTEN" in out:
        return "match", test
    if "PIX-2923: ALL-DECLARED-REGISTERS-WRITTEN" in out:
        return "no-match", test
    for marker in ("invalid profile", "Unknown command line argument",
                   "unrecognized", "## dxc failed", "## dxa failed",
                   "## dxopt failed", "## opt failed"):
        if marker in out:
            return f"invalid-probe(rc={rc})", "-"
    return f"unknown(rc={rc})", "-"


def main():
    rows, log = [], []
    # v1.5.2003 (2020-03-25) is flagged `bisectable = 0` because GitHub marks
    # it a prerelease, which leaves a 19-month hole between v1.4.1907 and
    # v1.5.2010 -- and this issue was filed 2020-05-27, inside that hole. It
    # is the only shipped binary from the era the report describes, so it is
    # probed explicitly even though it is not part of the linear sequence.
    rels = [(r["tag"], r["build_date"], r["cached_path"])
            for r in triage.con().execute(
                "SELECT tag, build_date, cached_path FROM releases"
                " WHERE bisectable = 1 OR tag = 'v1.5.2003'"
                " ORDER BY build_date")]
    rels.append(("main-debug(ab5400907)", "2026-08-06",
                 os.path.join(ROOT, "..", "..", "..", "build", "Debug", "bin",
                              "dxc.exe")))
    for tag, date, dxc in rels:
        if not dxc:
            dxc = triage.ensure_release(tag)
        dxc = os.path.abspath(dxc)
        dll = os.path.join(os.path.dirname(dxc), "dxcompiler.dll")
        if not (os.path.isfile(dxc) and os.path.isfile(dll)):
            rows.append([tag, date] + ["no-binaries"] * len(CASES))
            continue
        cells = []
        for shader, opt in CASES:
            rc, out = probe(dxc, dll, shader, opt)
            v, t = verdict(out, rc)
            cells.append(f"{v}/{t}")
            log.append(f"### {tag} ({date})  {shader} {opt}\n"
                       f"# PIX_DXC={dxc}\n# PIX_DLL={dll}\n"
                       f"$ run-2923.cmd {shader} {opt}\n"
                       f"{out.rstrip()}\n"
                       f"# exit: {rc}   predicate: {v}   "
                       f"PixTest emulation: {t}\n")
        rows.append([tag, date] + cells)
        print(f"{tag:<22}{date}  " + "  ".join(f"{c:<24}" for c in cells))

    hdr = ["release", "built"] + [f"{s.split('.')[0]}{o}" for s, o in CASES]
    with open(os.path.join(HERE, "manual-case-history.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("# issue: 2923\n")
        f.write("# what: release history for the PIX virtual-register\n"
                "#       numbering symptom. triage.py bisect cannot drive\n"
                "#       this repro (it is not a dxc invocation), so this is\n"
                "#       a hand-run matrix, produced by history-2923.py.\n")
        f.write("# driver: run-2923.cmd <shader> <opt>, with PIX_DXC and\n"
                "#         PIX_DLL pointed at each release's dxc.exe and\n"
                "#         dxcompiler.dll\n")
        f.write("# cells: <match.json predicate>/<PixTest assertions>\n")
        f.write("#        the control columns must read no-match. `test-FAILS`\n"
                "#        on a control column is NOT the symptom -- see notes.md.\n")
        f.write("#\n# summary\n")
        f.write("# " + "".join(f"{h:<26}" for h in hdr) + "\n")
        for r in rows:
            f.write("# " + "".join(f"{str(c):<26}" for c in r) + "\n")
        f.write("\n" + "\n".join(log))
    print("\nwrote manual-case-history.txt")


if __name__ == "__main__":
    main()
