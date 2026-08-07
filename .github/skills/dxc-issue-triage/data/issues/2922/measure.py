"""#2922 -- does the PIX value-to-declare pass still drop pointer-typed dbg.values at -O1?

The reported repro is not a `dxc` command line: it is "compile PixTest.cpp's shaders at -O1
instead of -Od and run PixTest::PixStructAnnotation_*". The symptom lives in a pass that
`dxc.exe` cannot run (`-dxil-dbg-value-to-dbg-declare`, exposed only through
`IDxcOptimizer`), so `cmd.txt` can only cover the compile half. This script runs the other
half, for every cached release as well as the local build.

Per (compiler, optimisation level):

  1. <dxc.exe>   -T as_6_5 -E main /Zi /Qembed_debug <-Od|-O1> -HV 2018 -enable-16bit-types
                 repro.hlsl                                     -> the module the pass reads
  2. <dxopt.exe> -external <that release's dxcompiler.dll> -external-fn DxcCreateInstance
                 -o=<bc> <ll> -opt-mod-passes -dxil-dbg-value-to-dbg-declare
                 -dxil-annotate-with-virtual-regs               -> that release's PIX passes
  3. <opt.exe>   -S <bc>                                        -> disassemble the result

Step 2 is the point: `dxopt -external` makes the *release's own* `dxcompiler.dll` provide
`IDxcOptimizer`, so each row measures that release's pass, not the local one. dxopt.exe and
opt.exe are only plumbing (blob marshalling and disassembly).

The observable is the number of `call void @llvm.dbg.declare` in the pass output. That is the
pass's entire product: it converts `llvm.dbg.value` into `llvm.dbg.declare` plus stores into
synthetic allocas, and PixTest walks exactly those `DbgDeclareInst`s to build the
`AllocaWrites` it asserts on. Zero of them at -O1, on a module that *does* contain a
pointer-typed `dbg.value`, is the reported defect.

Do NOT use the presence of `!pix-alloca-reg-write` for this. That metadata is present in the
broken output too: pre-fix -O1 output carries 2 tags, on the stores into the shader's own
`%p1` alloca, and so does the healthy -Od control. Post-fix -O1 output carries 4 -- the same
2 plus one per store into a synthesised debug register. "Has the metadata" therefore scores
the defect as healthy; only the count separates them, and the count is 2 for both the broken
case and the control. Verified in artifacts/pass-v1.6.2112-O1.ll vs pass-main-debug-O1.ll.

Usage:
    python measure.py            # local Debug build only
    python measure.py --history  # every cached release, then the local build

Paths come from the triage database and the DXC_BUILD_BIN environment variable, falling back
to the repo's Debug build. The scratch directory is created here rather than assumed -- git
does not store empty directories.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
ART = os.path.join(HERE, "artifacts")
DB = os.path.join(SKILL, ".cache", "triage.db")

BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
DXOPT = os.path.join(BUILD_BIN, "dxopt.exe")
OPT = os.path.join(BUILD_BIN, "opt.exe")
LOCAL_DXC = os.path.join(BUILD_BIN, "dxc.exe")

# PixTest.cpp: TestStructAnnotationCase() compiles at as_6_5 with -HV 2018 and
# -enable-16bit-types, and Compile() prepends /Zi /Qembed_debug.
COMPILE_ARGS = ["-T", "as_6_5", "-E", "main", "/Zi", "/Qembed_debug",
                "-HV", "2018", "-enable-16bit-types"]
# PixTestUtils.cpp: RunAnnotationPasses().
PASSES = ["-opt-mod-passes", "-dxil-dbg-value-to-dbg-declare",
          "-dxil-annotate-with-virtual-regs"]

DBG_DECLARE = re.compile(r"call void @llvm\.dbg\.declare\(")
DBG_VALUE = re.compile(r"call void @llvm\.dbg\.value\(metadata ([^,]+),")
REG_WRITE = re.compile(r"!pix-alloca-reg-write")
PIX_ALLOCA = re.compile(r"= alloca \[\d+ x ")


def is_pointer_operand(operand):
    """True when a dbg.value's first operand has pointer type.

    The operand reads `<type> <value>`, and the type may itself contain spaces
    (`<4 x float> %x`), so take everything but the last token. Testing the whole
    string for a trailing `*` finds nothing -- the value name is last.
    """
    parts = operand.rsplit(None, 1)
    return len(parts) == 2 and parts[0].rstrip().endswith("*")


def run(cmd, out_path=None):
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(p.stdout)
    return p


def releases():
    """(tag, build_date, dxc.exe) for every bisectable release, oldest first."""
    if not os.path.isfile(DB):
        sys.exit(f"no triage database at {DB}; run `triage.py catalog` first")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT tag, build_date, cached_path FROM releases"
        " WHERE bisectable=1 AND cached_path IS NOT NULL"
        " ORDER BY build_date").fetchall()
    con.close()
    return [r for r in rows if os.path.isfile(r[2])]


def measure(label, dxc_exe, opt_level):
    """Compile at opt_level, run that build's PIX passes, report what came out."""
    stem = f"{label}-{opt_level.lstrip('-/')}"
    ll_in = os.path.join(ART, f"in-{stem}.ll")
    bc = os.path.join(ART, f"pass-{stem}.bc")
    ll_out = os.path.join(ART, f"pass-{stem}.ll")
    dll = os.path.join(os.path.dirname(dxc_exe), "dxcompiler.dll")

    r = {"label": label, "opt": opt_level, "dxc": dxc_exe}

    c = run([dxc_exe] + COMPILE_ARGS + [opt_level, "repro.hlsl"], ll_in)
    r["compile_exit"] = c.returncode
    if c.returncode != 0:
        r["verdict"] = "invalid-probe"
        r["why"] = (c.stderr.strip().splitlines() or ["(no stderr)"])[0]
        return r

    text = open(ll_in, encoding="utf-8", errors="replace").read()
    ptr_dbg_values = [m for m in DBG_VALUE.findall(text)
                      if is_pointer_operand(m)]
    r["dbg_value_total"] = len(DBG_VALUE.findall(text))
    r["dbg_value_pointer"] = len(ptr_dbg_values)
    r["dbg_declare_in"] = len(DBG_DECLARE.findall(text))

    # -external without -external-fn fails E_INVALIDARG (dxopt.cpp passes a null
    # entry-point name straight through), and -o= must precede the input file or
    # it is swallowed as an optimizer argument. Both look like a pass failure.
    o = run([DXOPT, "-external", dll, "-external-fn", "DxcCreateInstance",
             f"-o={bc}", ll_in] + PASSES)
    r["dxopt_exit"] = o.returncode
    with open(os.path.join(ART, f"pass-{stem}.log"), "w",
              encoding="utf-8") as f:
        f.write(o.stdout + o.stderr)
    if o.returncode != 0 or not os.path.isfile(bc):
        r["verdict"] = "pass-failed"
        r["why"] = (o.stdout.strip().splitlines() or ["(no output)"])[0]
        return r

    d = run([OPT, "-S", bc], ll_out)
    r["disasm_exit"] = d.returncode
    if d.returncode != 0:
        r["verdict"] = "disasm-failed"
        r["why"] = (d.stderr.strip().splitlines() or ["(no stderr)"])[0]
        return r

    after = open(ll_out, encoding="utf-8", errors="replace").read()
    r["dbg_declare_out"] = len(DBG_DECLARE.findall(after))
    r["pix_alloca_out"] = len(PIX_ALLOCA.findall(after))
    r["reg_writes_out"] = len(REG_WRITE.findall(after))

    if r["dbg_value_total"] == 0 and r["dbg_declare_in"] == 0:
        # No local-variable debug records at all, so the pass has nothing to
        # convert and this build cannot show the symptom either way. v1.5.2010
        # is here: it emits a line table and a DISubprogram but no
        # DILocalVariable. The -Od row is the feature-presence control that
        # tells this apart from "the repro was rejected".
        r["verdict"] = "invalid-probe"
        r["why"] = "no llvm.dbg.declare/value records emitted for the local"
    elif opt_level == "-Od":
        # Control. At -Od dxc emits dbg.declare directly, so the pass has no
        # pointer case to meet; this row only shows the harness reached the pass.
        r["verdict"] = "control"
    elif r["dbg_value_pointer"] == 0:
        r["verdict"] = "no-pointer-case"
    elif r["dbg_declare_out"] == 0:
        r["verdict"] = "repro"          # pass dropped the variable
    else:
        r["verdict"] = "no-repro"       # pass converted it
    return r


def report(rows):
    """Write the committed, human-readable form of measure.json.

    artifacts/ is regenerable scratch and is gitignored, so the evidence a
    reader can check has to be a text file: the exact commands, the table, and
    the verbatim IR lines the verdict turns on.
    """
    out = [
        "#2922 release history -- does the PIX value-to-declare pass drop the",
        "pointer-typed dbg.value that -O1 produces?",
        "",
        "Produced by `python measure.py --history`. Each row runs THAT BUILD's own",
        "PIX pass, by pointing dxopt at that build's dxcompiler.dll:",
        "",
        "  <dxc.exe>   " + " ".join(COMPILE_ARGS) + " <-Od|-O1> repro.hlsl",
        "  <dxopt.exe> -external <that build's dxcompiler.dll> -external-fn "
        "DxcCreateInstance \\",
        "              -o=<bc> <ll> " + " ".join(PASSES),
        "  <opt.exe>   -S <bc>",
        "",
        "dxopt.exe and opt.exe come from the local Debug build and are only",
        "plumbing (blob marshalling and disassembly). The pass under test is the",
        "release's.",
        "",
        "OBSERVABLE: number of `call void @llvm.dbg.declare` INSTRUCTIONS in the",
        "pass output. That is the pass's whole product, and PixTest builds its",
        "AllocaWrites by walking exactly those DbgDeclareInsts. 0 at -O1, on a",
        "module that does contain a pointer-typed dbg.value, is the reported bug.",
        "",
        "  ptr    = pointer-typed `llvm.dbg.value` instructions dxc emitted (input)",
        "  decl   = `llvm.dbg.declare` instructions in the pass OUTPUT",
        "  dbgreg = `alloca [N x ...]` debug registers the pass synthesised",
        "",
        f"{'release':>14} {'opt':>4} {'ptr':>4} {'decl':>5} {'dbgreg':>7}  verdict",
        f"{'-'*14} {'-'*4} {'-'*4} {'-'*5} {'-'*7}  {'-'*7}",
    ]
    for r in rows:
        out.append(
            f"{r['label']:>14} {r['opt']:>4} "
            f"{str(r.get('dbg_value_pointer', '-')):>4} "
            f"{str(r.get('dbg_declare_out', '-')):>5} "
            f"{str(r.get('pix_alloca_out', '-')):>7}  {r['verdict']}"
            + (f"  [{r['why']}]" if r.get("why") else ""))

    out += ["", "",
            "VERBATIM. The whole of @main after the pass ran, for the last",
            "release with the bug and for ground truth. Pre-fix, the variable",
            "\"p\" has no debug record of any kind left: the pass early-returned",
            "on the pointer and its cleanup removed the llvm.dbg.value it did",
            "not convert. Post-fix, two llvm.dbg.declares appear, one per",
            "component of the float2, each on a synthesised [1 x float] debug",
            "register -- which is what PixTest counts.", ""]
    for stem, what in (("v1.6.2112-O1", "last release with the bug"),
                       ("main-debug-O1", "ground truth, main @ ab5400907")):
        path = os.path.join(ART, f"pass-{stem}.ll")
        if not os.path.isfile(path):
            continue
        out += [f"--- pass output, {stem}  ({what}) ---"]
        body, emit = [], False
        for ln in open(path, encoding="utf-8", errors="replace"):
            if ln.startswith("define void @main()"):
                emit = True
            if emit:
                body.append("  " + ln.rstrip())
            if emit and ln.startswith("}"):
                break
        n = sum(1 for b in body
                if b.lstrip().startswith("call void @llvm.dbg.declare("))
        out += body
        out += [f"  => llvm.dbg.declare instructions in @main: {n}", ""]

    with open(os.path.join(HERE, "manual-case-release-history.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true",
                    help="measure every cached release as well as the local build")
    a = ap.parse_args()

    os.makedirs(ART, exist_ok=True)
    for exe in (DXOPT, OPT):
        if not os.path.isfile(exe):
            sys.exit(f"missing {exe}; set DXC_BUILD_BIN to a DXC build's bin dir")

    targets = []
    if a.history:
        targets += [(tag, path) for tag, _date, path in releases()]
    targets.append(("main-debug", LOCAL_DXC))

    rows = []
    for label, dxc_exe in targets:
        for opt_level in ("-Od", "-O1"):
            r = measure(label, dxc_exe, opt_level)
            rows.append(r)
            print(f"{label:>14} {opt_level:>4}  "
                  f"dbg.value(ptr)={r.get('dbg_value_pointer', '-'):>2}  "
                  f"dbg.declare out={r.get('dbg_declare_out', '-'):>2}  "
                  f"pix allocas={r.get('pix_alloca_out', '-'):>2}  "
                  f"{r['verdict']}"
                  + (f"  [{r['why']}]" if r.get("why") else ""))
    with open(os.path.join(ART, "measure.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    if a.history:
        report(rows)


if __name__ == "__main__":
    main()
