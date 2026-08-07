"""#2918 -- drive the PIX "numbering" passes over a /Od + debug-info shader.

The reported symptom is not reachable from a `dxc` command line, so it cannot be expressed in
`cmd.txt` (one dxc invocation, arguments only) and `triage.py run` / `bisect` cannot score it.
PIX runs its passes through `IDxcOptimizer::RunOptimizer` on an already-compiled module; the
command-line equivalent shipped in this repo is `dxopt.exe`, and the DXC test suite drives the
same two passes the same way (tools/clang/test/HLSLFileCheck/pix/*.hlsl,
tools/clang/unittests/HLSL/PixTestUtils.cpp: RunAnnotationPasses).

So the repro is a two-stage pipeline:

    stage 1   dxc   -T cs_6_0 -E main -Od -Zi -Qembed_debug repro.hlsl   > module.ll
    stage 2   dxopt module.ll -opt-mod-passes -dxil-dbg-value-to-dbg-declare
                                              -dxil-annotate-with-virtual-regs

`DxcOptimizer::RunOptimizer` appends `createVerifierPass()` to the module pipeline
(lib/HLSL/DxcOptimizer.cpp), and a verifier failure becomes report_fatal_error ->
hlsl::Exception (lib/Support/ErrorHandling.cpp), which is the `std::exception` the issue
reports. The symptom predicate applied here is therefore crash-shaped, per SKILL.md:

    SYMPTOM = stage 2 does not complete (dxopt exits non-zero / RunOptimizer fails),
              on a stage-1 module that is itself verifier-clean.

Two per-build controls decide whether a result means anything at all:

    baseline  dxopt module.ll -opt-mod-passes -S
              must SUCCEED. Proves the module dxc emitted is verifier-clean, so any stage-2
              failure was introduced by the passes rather than inherited.
    control   the same module with `inlinedAt:` deleted from one DILocation -- the exact shape
              the issue quotes (`!970 = !DILocation(line: 96, column: 1, scope: !965)` with no
              inlinedAt) -- run with NO passes. Must FAIL. Proves this build's verifier still
              performs the "!dbg attachment points at wrong subprogram" check and shows what
              that failure looks like here, since release builds print no message.

Release packages ship dxc.exe + dxcompiler.dll + dxil.dll and no dxopt.exe, so a release is
driven by placing *this repo's* dxopt.exe next to *that release's* dxcompiler.dll in a scratch
directory. dxopt only calls DxcCreateInstance + IDxcOptimizer, both stable COM surfaces; the
two controls above are what make the mixed pairing falsifiable rather than assumed.

Usage:
    python run-pix-passes.py                 ground truth only
    python run-pix-passes.py --history       every cached release, then ground truth
    python run-pix-passes.py --keep          leave the scratch tree for inspection

Compiler paths come from the DXC / DXOPT / DXC_TRIAGE_CACHE environment variables and fall
back to this repo's Debug build and the skill's release cache. Nothing is hardcoded to one
machine, and the scratch directory is created here rather than assumed -- git does not store
empty directories, and a repro that depends on one fails for an unrelated reason (see #2427).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[os.pardir] * 6))
SKILL = os.path.abspath(os.path.join(HERE, *[os.pardir] * 3))

BUILD_BIN = os.path.join(REPO, "build", "Debug", "bin")
DXC = os.environ.get("DXC") or os.path.join(BUILD_BIN, "dxc.exe")
DXOPT = os.environ.get("DXOPT") or os.path.join(BUILD_BIN, "dxopt.exe")
# Only ever this repo's opt.exe, never a release's -- releases ship none. It is used solely to
# print the verifier message that dxopt discards, and its output is labelled as such.
OPT = os.environ.get("OPT") or os.path.join(BUILD_BIN, "opt.exe")
CACHE = os.environ.get("DXC_TRIAGE_CACHE") or os.path.join(SKILL, ".cache")
RELEASES = os.path.join(CACHE, "compilers", "releases")

WORK = os.path.join(HERE, "work")

COMPILE_ARGS = ["-T", "cs_6_0", "-E", "main", "-Od", "-Zi", "-Qembed_debug"]
PIX_PASSES = ["-opt-mod-passes", "-dxil-dbg-value-to-dbg-declare",
              "-dxil-annotate-with-virtual-regs"]

# A release that predates the pass cannot answer the question; it is an invalid probe rather
# than a clean run. DxilDbgValueToDbgDeclare landed 2020-02-20 (#2706).
REQUIRED_PASSES = ("dxil-dbg-value-to-dbg-declare", "dxil-annotate-with-virtual-regs")


def run(argv, cwd=None, stdout_path=None):
    """Run a command, returning (exit code, combined text). Never raises on failure."""
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=300)
    except FileNotFoundError as e:
        return None, "%s\n" % e
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT\n"
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    if stdout_path:
        with open(stdout_path, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        return p.returncode, err
    return p.returncode, out + err


def hexcode(rc):
    if rc is None:
        return "n/a"
    return "%d (0x%08X)" % (rc, rc & 0xFFFFFFFF)


def first_line(text):
    for ln in text.splitlines():
        if ln.strip():
            return ln.strip()
    return ""


def break_inlined_at(src, dst):
    """Copy an .ll, deleting `inlinedAt:` from one DILocation an instruction actually uses.

    Reproduces the metadata shape the issue quotes: a !dbg attachment inside the entry point
    whose scope chain ends in a *different* function's DISubprogram, with nothing marking it
    as inlined. Returns the metadata id that was edited, or None if no suitable location
    exists (in which case the control cannot be built and says so).

    The scope has to be a DILexicalBlock, not the DISubprogram itself, and that is not a
    detail -- it is the difference between a control that works and one that silently passes.
    Verifier::visitDISubprogram (lib/IR/Verifier.cpp) walks each !dbg with a `Seen` set:

        DILocalScope *Scope = DL->getInlinedAtScope();
        if (Scope && !Seen.insert(Scope).second) continue;
        DISubprogram *SP = Scope ? Scope->getSubprogram() : nullptr;
        if (SP && !Seen.insert(SP).second) continue;
        Assert(SP->describes(F), "!dbg attachment points at wrong subprogram for function", ...)

    When the location's scope IS a DISubprogram, `Scope` and `SP` are the same node, the
    second insert fails, and the check is skipped -- a genuinely wrong !dbg is accepted. The
    issue's own dump has `scope: !965 = distinct !DILexicalBlock(...)`, so the two nodes
    differ there and the assert fires. Measured: breaking a subprogram-scoped location
    instead makes both `opt -verify` and dxopt accept the module.
    """
    with open(src, encoding="utf-8", errors="replace") as f:
        text = f.read()
    used = set(re.findall(r"!dbg !(\d+)", text))
    blocks = set(re.findall(r"^!(\d+) = distinct !DILexicalBlock", text, re.M))
    for m in re.finditer(r"^!(\d+) = !DILocation\((.*?)\)$", text, re.M):
        mdid, body = m.group(1), m.group(2)
        scope = re.search(r"scope: !(\d+)", body)
        if mdid not in used or "inlinedAt:" not in body:
            continue
        if not scope or scope.group(1) not in blocks:
            continue
        fixed = re.sub(r",\s*inlinedAt: !\d+", "", body)
        text = text[:m.start()] + "!%s = !DILocation(%s)" % (mdid, fixed) + text[m.end():]
        with open(dst, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return mdid
    return None


def probe(label, dxc_exe, dll_dir, keep):
    """Measure one build. Returns a dict of observations; interpretation is the caller's."""
    r = {"label": label, "dxc": dxc_exe, "dll_dir": dll_dir or "(dxopt's own)"}
    wd = os.path.join(WORK, label)
    if os.path.isdir(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)

    dxopt = DXOPT
    if dll_dir:
        # Release packages ship no dxopt.exe. Pair this repo's driver with that release's
        # dxcompiler.dll in a private directory so the DLL search order picks the old one.
        for name in ("dxcompiler.dll", "dxil.dll"):
            p = os.path.join(dll_dir, name)
            if os.path.isfile(p):
                shutil.copy2(p, wd)
        shutil.copy2(DXOPT, wd)
        dxopt = os.path.join(wd, "dxopt.exe")

    rc, text = run([dxopt, "-passes"])
    r["passes_listed"] = rc == 0
    r["missing_passes"] = [p for p in REQUIRED_PASSES if p not in text]

    module = os.path.join(wd, "module.ll")
    rc, err = run([dxc_exe] + COMPILE_ARGS + [os.path.join(HERE, "repro.hlsl")],
                  cwd=HERE, stdout_path=module)
    r["compile_rc"] = rc
    r["compile_err"] = first_line(err)
    ll = ""
    if os.path.isfile(module):
        with open(module, encoding="utf-8", errors="replace") as f:
            ll = f.read()
    r["compile_has_debug_info"] = "!DISubprogram" in ll and "llvm.dbg." in ll
    # The defect needs a variable whose scope belongs to the inlined callee: that is what the
    # pre-fix pass turned into a column-1, no-inlinedAt DILocation on a dbg.declare.
    r["has_inlined_locations"] = "inlinedAt:" in ll

    if not r["compile_has_debug_info"]:
        r["verdict"] = "invalid-probe"
        r["why"] = "stage 1 produced no debug info, so stage 2 cannot be reached"
        return r
    if r["missing_passes"]:
        r["verdict"] = "invalid-probe"
        r["why"] = "this build has no " + ", ".join(r["missing_passes"])
        return r

    rc, text = run([dxopt, module, "-opt-mod-passes", "-S"], cwd=wd)
    r["baseline_rc"] = rc
    r["baseline_msg"] = first_line(text) if rc else ""

    broken = os.path.join(wd, "module-broken.ll")
    r["control_md"] = break_inlined_at(module, broken)
    if r["control_md"]:
        rc, text = run([dxopt, broken, "-opt-mod-passes", "-S"], cwd=wd)
        r["control_rc"] = rc
        r["control_msg"] = first_line(text) if rc else ""
        # dxopt drops RunOptimizer's text blob when the call fails, and a Release
        # dxcompiler.dll prints nothing, so the message itself comes from this repo's
        # opt.exe running the same Verifier over the same module. Text only -- the pass/fail
        # decision above is the release's own.
        _, vtext = run([OPT, "-verify", "-S", broken, "-o",
                        os.path.join(wd, "verified.ll")], cwd=wd)
        r["control_verifier"] = [ln for ln in vtext.splitlines() if ln.strip()][:6]
    else:
        r["control_rc"] = None
        r["control_msg"] = "(no lexical-block-scoped DILocation -- control not built)"
        r["control_verifier"] = []

    rc, text = run([dxopt, module] + PIX_PASSES, cwd=wd)
    r["pix_rc"] = rc
    r["pix_msg"] = first_line(text)

    if r["baseline_rc"] != 0:
        r["verdict"] = "invalid-probe"
        r["why"] = "stage-1 module does not verify on this build, so stage 2 measures nothing"
    elif r["control_rc"] == 0:
        r["verdict"] = "invalid-probe"
        r["why"] = "control did not fail: this build does not reject a wrong-subprogram !dbg"
    else:
        r["verdict"] = "repro" if r["pix_rc"] != 0 else "no-repro"
        r["why"] = ""
    if not keep:
        shutil.rmtree(wd, ignore_errors=True)
    return r


def release_builds():
    if not os.path.isdir(RELEASES):
        return []
    out = []
    for tag in sorted(os.listdir(RELEASES)):
        for sub in (os.path.join("bin", "x64"), "bin", ""):
            d = os.path.join(RELEASES, tag, sub) if sub else os.path.join(RELEASES, tag)
            if os.path.isfile(os.path.join(d, "dxc.exe")):
                out.append((tag, os.path.join(d, "dxc.exe"), d))
                break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--history", action="store_true",
                    help="probe every cached release as well as ground truth")
    ap.add_argument("--keep", action="store_true", help="leave the scratch tree in place")
    a = ap.parse_args()

    os.makedirs(WORK, exist_ok=True)
    builds = release_builds() if a.history else []
    builds.append(("main-debug", DXC, None))

    print("stage 1: dxc %s repro.hlsl" % " ".join(COMPILE_ARGS))
    print("stage 2: dxopt module.ll %s" % " ".join(PIX_PASSES))
    print("driver : %s" % DXOPT)
    print()
    hdr = "%-14s %-9s %-9s %-9s %-11s %s" % (
        "build", "compile", "baseline", "control", "PIX passes", "verdict")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for label, dxc_exe, dll_dir in builds:
        r = probe(label, dxc_exe, dll_dir, a.keep)
        rows.append(r)
        print("%-14s %-9s %-9s %-9s %-11s %s%s" % (
            label,
            hexcode(r.get("compile_rc")).split(" ")[0],
            hexcode(r.get("baseline_rc")).split(" ")[0],
            hexcode(r.get("control_rc")).split(" ")[0],
            hexcode(r.get("pix_rc")).split(" ")[0],
            r["verdict"],
            (" -- " + r["why"]) if r.get("why") else ""))
    print()
    for r in rows:
        print("%s" % r["label"])
        dll = r["dll_dir"]
        if dll.startswith(RELEASES):
            dll = "<releases>" + dll[len(RELEASES):]
        print("  dxcompiler.dll : %s" % dll)
        if r.get("missing_passes"):
            print("  missing passes : %s" % ", ".join(r["missing_passes"]))
        print("  compile        : exit %s%s" % (
            hexcode(r.get("compile_rc")),
            ", debug info present" if r.get("compile_has_debug_info") else
            ", NO debug info"))
        if "baseline_rc" in r:
            print("  baseline       : exit %s  %s" % (hexcode(r["baseline_rc"]),
                                                      r.get("baseline_msg", "")))
            print("  control (!%s)  : exit %s  %s" % (
                r.get("control_md"), hexcode(r.get("control_rc")),
                r.get("control_msg", "")))
            print("  PIX passes     : exit %s  %s" % (hexcode(r["pix_rc"]),
                                                      r.get("pix_msg", "")))
            if r.get("control_verifier"):
                print("  control rejected by the verifier as (text via this repo's opt.exe):")
                for ln in r["control_verifier"]:
                    print("    %s" % ln)
        print()
    if not a.keep:
        shutil.rmtree(WORK, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
