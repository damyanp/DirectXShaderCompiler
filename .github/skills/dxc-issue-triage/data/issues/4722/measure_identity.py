"""Byte-identity measurement for issue 4722.

The decisive evidence for a silent wrong-code report is not a reading of one
output. It is that two sources asking for *opposite* matrix layouts produce the
*same* compiled shader: whichever layout is correct, one of the two requests was
ignored. This script measures that, and measures the same pair without the
template so the result cannot be read as "matrix orientation never works here".

It echoes every command it runs with subprocess.list2cmdline, so the capture is
re-derivable rather than transcribed, and it routes all output through
triage.redact_paths so no machine-local path is committed.

  python measure_identity.py > manual-case-identity.txt

The compiler comes from $DXC_EXE, or from the triage database's `main-debug`
row when that is unset (read-only SELECT; no table is written).
"""

import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, os.pardir, "scripts"))
import triage                                                    # noqa: E402


def compiler():
    exe = os.environ.get("DXC_EXE")
    if exe:
        return exe
    row = triage.con().execute(
        "SELECT exe_path FROM compilers WHERE id='main-debug'").fetchone()
    if not row:
        sys.exit("no DXC_EXE and no main-debug compiler registered")
    return row["exe_path"]


ARGS = ["-T", "ps_6_0", "-E", "main", "-HV", "2021"]

# (label, source, what the source asks for)
CASES = [
    ("template row_major   ", "repro.hlsl", "row-major"),
    ("template column_major", "control-template-column-major.hlsl", "column-major"),
    ("template (no request)", "control-template-default.hlsl", "default"),
    ("concrete row_major   ", "control-nontemplate-row-major.hlsl", "row-major"),
    ("concrete column_major", "control-nontemplate-column-major.hlsl", "column-major"),
    ("concrete (no request)", "control-nontemplate-default.hlsl", "default"),
]


def orientation(text):
    """Read the emitted layout out of the disassembly's cbuffer block."""
    hits = set()
    for line in text.splitlines():
        stripped = line.strip().lstrip(";").strip()
        for word in ("row_major", "column_major"):
            if stripped.startswith(word + " float4x4 M;"):
                hits.add(word)
    if len(hits) == 1:
        return hits.pop()
    # A self-test, not a convenience: if the reader stops working, say so
    # loudly rather than returning something that reads like a measurement.
    return "PARSE-WARNING: no unique orientation line found"


def run(exe, source, out):
    argv = [exe] + ARGS + ["-Fo", out, source]
    print("$ " + subprocess.list2cmdline(["dxc"] + ARGS + ["-Fo", out, source]))
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
    disasm = subprocess.run([exe] + ARGS + [source], cwd=HERE,
                            capture_output=True, text=True)
    return p.returncode, disasm.stdout + disasm.stderr


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    exe = compiler()
    ver = subprocess.run([exe, "--version"], capture_output=True, text=True)
    print("# issue 4722 -- byte-identity measurement")
    print("# compiler: " + triage.display_exe(exe))
    print("# version:  " + ver.stdout.strip().replace("\n", " | "))
    print()

    results = {}
    for label, source, asked in CASES:
        out = "identity-%s.dxo" % source.replace(".hlsl", "")
        abs_out = os.path.join(HERE, out)
        code, text = run(exe, source, out)
        digest = sha(abs_out) if os.path.exists(abs_out) else "(no container emitted)"
        results[source] = (label, asked, code, orientation(text), digest)
        if os.path.exists(abs_out):
            os.remove(abs_out)
    print()

    print("%-22s  %-12s  %-12s  %s" % ("case", "asked for", "emitted", "sha256 of the DXIL container"))
    print("-" * 22 + "  " + "-" * 12 + "  " + "-" * 12 + "  " + "-" * 64)
    for _, source, _ in CASES:
        label, asked, code, got, digest = results[source]
        assert code == 0, "%s exited %s" % (source, code)
        print("%-22s  %-12s  %-12s  %s" % (label, asked, got, digest))
    print()

    def same(a, b):
        return results[a][4] == results[b][4]

    tmpl_row, tmpl_col = "repro.hlsl", "control-template-column-major.hlsl"
    conc_row, conc_col = ("control-nontemplate-row-major.hlsl",
                          "control-nontemplate-column-major.hlsl")
    tmpl_def, conc_def = ("control-template-default.hlsl",
                          "control-nontemplate-default.hlsl")

    print("SYMPTOM     template row_major == template column_major : %s"
          % ("IDENTICAL -- one of the two requests was ignored" if same(tmpl_row, tmpl_col)
             else "different"))
    print("            template row_major == template default      : %s"
          % ("IDENTICAL -- the request had no effect at all" if same(tmpl_row, tmpl_def)
             else "different"))
    print("CONTROL     concrete row_major == concrete column_major : %s"
          % ("IDENTICAL -- INSTRUMENT BROKEN, this must differ" if same(conc_row, conc_col)
             else "different -- orientation does work outside templates"))
    print("CONTROL     concrete column_major == concrete default   : %s"
          % ("IDENTICAL -- the default here is column-major" if same(conc_col, conc_def)
             else "different -- the default is NOT column-major, re-read the analysis"))


if __name__ == "__main__":
    buf = []
    _print = print

    class Tee:
        def write(self, s):
            buf.append(s)
        def flush(self):
            pass

    real = sys.stdout
    sys.stdout = Tee()
    try:
        main()
    finally:
        sys.stdout = real
    real.write(triage.redact_paths("".join(buf)))
