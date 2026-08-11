"""Where does DXC issue 4710's diagnostic come from, and what runs before it?

This answers *why* the compiler rejects the reporter's shader, at the level a
maintainer can act on: which guard fires, in which pass, and what has and has
not run by then.

    lib/HLSL/HLModule.cpp  GetBindingForResourceInCB:
        if (!CbPtr->hasAllConstantIndices()) {  <-- the guard
          EmitErrorOnInstruction(CbPtr,
            "Index for resource array inside cbuffer must be a literal expression");

Three measurements, in increasing strength:

  step 1  dxc's own `-Odump` pass list: `-dxilgen` (which contains the guard)
          runs BEFORE `-dxil-loop-unroll` (which implements `[unroll]`).
  step 2  `-fcgl` shows the front end alone does not reject this shader, so the
          diagnostic is not a Sema rule.
  step 3  the shipped pass list replayed over the high-level IR with `dxopt`,
          under `cdb`, so the actual call stack that reaches the guard is
          captured rather than inferred from the message's file:line:col shape
          (a DXIL pass can format a diagnostic exactly like Sema).

Step 4 is a NEGATIVE RESULT that is recorded deliberately. Hoisting
`-dxil-loop-unroll` above `-dxilgen` does silence the diagnostic -- but the
module it produces contains only one of the loop's four iterations, so the
hoist changed more than the ordering and it is NOT evidence that reordering
would fix anything. The self-check that establishes this is a count of the
lowered ops, printed below; without it the run would read as a clean fix.

Usage:  python probe-pass-order.py > manual-case-pass-order.txt
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))

import triage  # noqa: E402

ISSUE = 4710
BIN = os.path.join(triage.REPO_ROOT, "build", "Debug", "bin")
DXC = os.path.join(BIN, "dxc.exe")
DXOPT = os.path.join(BIN, "dxopt.exe")
CDB = r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"
DIAG = "Index for resource array inside cbuffer must be a literal expression"
GUARD = "GetBindingForResourceInCB"

UNROLL = "-dxil-loop-unroll"
DXILGEN = "-dxilgen"
PROFILE = ["-T", "ps_6_0", "-E", "psMain"]


def show(argv):
    line = subprocess.list2cmdline(argv)
    for tool, name in ((DXC, "dxc"), (DXOPT, "dxopt"), (CDB, "cdb")):
        line = line.replace(tool, name)
    return triage.redact_paths(line)


def run(argv, cwd, shell_cmd=None):
    if shell_cmd:
        p = subprocess.run(shell_cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=600, shell=True)
    else:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=600)
    return triage.redact_paths(p.stdout + p.stderr), p.returncode


def find(seq, name):
    for i, p in enumerate(seq):
        if p == name or p.startswith(name + ","):
            return i
    return -1


def main():
    d = triage.issue_dir(ISSUE)

    print("# issue 4710 -- which guard emits the diagnostic, and what has run by then")
    print("# generator: probe-pass-order.py (committed beside this file)")
    print(f"# diagnostic: {DIAG}")
    print()

    print("== step 1: dxc's own pass ordering ==")
    argv = [DXC] + PROFILE + ["-Odump", "repro.hlsl"]
    out, rc = run(argv, d)
    print(f"$ {show(argv)}")
    print(f"  exit=0x{rc & 0xFFFFFFFF:08X}")
    passes = [l.strip() for l in out.splitlines()
              if l.strip().startswith("-")]

    ig, iu = find(passes, DXILGEN), find(passes, UNROLL)
    for i in range(max(0, ig - 3), min(len(passes), iu + 3)):
        mark = "  <<<" if i in (ig, iu) else ""
        print(f"    [{i:3}] {passes[i]}{mark}")
    print(f"  {DXILGEN} is at {ig}; {UNROLL} is at {iu}")
    print(f"  -> the pass holding the guard runs "
          f"{'BEFORE' if ig < iu else 'AFTER'} the pass that implements [unroll]")
    print("  Same fact in source: lib/Transforms/IPO/PassManagerBuilder.cpp,")
    print("  addHLSLPasses() adds createDxilGenerationPass(...) and only afterwards")
    print("  createDxilLoopUnrollPass(...), under the comment '// Passes to handle [unroll]'.")
    print()

    print("== step 2: does the front end reject it? ==")
    argv = [DXC] + PROFILE + ["-fcgl", "repro.hlsl", "-Fc", "scratch-fcgl.ll"]
    out, rc = run(argv, d)
    print(f"$ {show(argv)}")
    print(f"  exit=0x{rc & 0xFFFFFFFF:08X}   diagnostic present: {DIAG in out}")
    print("  -> No. -fcgl stops before the DXIL passes and the shader is accepted,")
    print("     so this is not a Sema/language rule despite the file:line:col shape.")
    print()

    print("== step 3: replay the SHIPPED pass list and capture the call stack ==")
    upto = passes[:ig + 1]
    inner = subprocess.list2cmdline([DXOPT, "-o=scratch-order-shipped.bc",
                                     "scratch-fcgl.ll"] + upto)
    cdbcmd = (f'"{CDB}" -c "sxe -c \\"kn 18; gh\\" e0000001; g; q" ' + inner)
    out, rc = run(None, d, shell_cmd=cdbcmd)
    print(f"$ cdb -c \"sxe -c \\\"kn 18; gh\\\" e0000001; g; q\" "
          f"dxopt -o=scratch-order-shipped.bc scratch-fcgl.ll <{len(upto)} passes>")
    print(f"  exit=0x{rc & 0xFFFFFFFF:08X}")
    print(f"  guard '{GUARD}' on the stack: {GUARD in out}")
    print("  frames (trimmed to the relevant chain):")
    keep = ("llvm_assert", "EmitError", "EmitWarningOrError", "GetBindingForResourceInCB",
            "CreateResourceForCbPtr", "GetOrCreateResourceForCbPtr",
            "TranslateResourceInCB", "TranslateCBAddressUserLegacy",
            "TranslateCBGepLegacy", "TranslateCBOperationsLegacy",
            "TranslateHLSubscript", "TranslateSubscriptOperation",
            "TranslateHLBuiltinOperation", "TranslateBuiltinOperations",
            "GenerateDxilOperations", "DxilGenerationPass::runOnModule")
    for line in out.splitlines():
        if any(k in line for k in keep):
            print("    " + re.sub(r"^[0-9a-f]{2} [0-9a-f`]+ [0-9a-f`]+\s+", "", line.strip()))
    print("  NOTE: dxopt has no thread file system, so llvm::errs() asserts while")
    print("  printing the message -- the assert is the diagnostic being emitted, not a")
    print("  separate failure. dxc.exe prints the same message and exits 0x80004005.")
    print()

    print("== step 4: hoist [unroll] above -dxilgen -- NEGATIVE RESULT, read the self-check ==")
    moved = list(passes)
    moved.insert(find(moved, DXILGEN), moved.pop(find(moved, UNROLL)))
    for f in ("scratch-order-hoisted.bc",):
        p = os.path.join(d, f)
        if os.path.exists(p):
            os.remove(p)
    argv = [DXOPT, "-o=scratch-order-hoisted.bc", "scratch-fcgl.ll"] + moved
    out, rc = run(argv, d)
    print(f"$ dxopt -o=scratch-order-hoisted.bc scratch-fcgl.ll <{len(moved)} passes, "
          f"{UNROLL} moved to index {find(moved, UNROLL)}>")
    print(f"  exit=0x{rc & 0xFFFFFFFF:08X}   diagnostic present: {DIAG in out}")
    made = os.path.exists(os.path.join(d, "scratch-order-hoisted.bc"))
    print(f"  produced a module: {made}")
    if made:
        dump, _ = run([DXC, "-dumpbin", "scratch-order-hoisted.bc"], d)
        n_tex = len(re.findall(r"call .*@dx\.op\.textureLoad", dump))
        n_srv = len(re.findall(r"call .*@dx\.op\.createHandle\(i32 57, i8 0", dump))
        print(f"  SELF-CHECK: textureLoad calls = {n_tex}, SRV createHandle calls = {n_srv}")
        print("              the source loop has 4 iterations, so a faithful unroll owes 4 of each")
        for line in dump.splitlines():
            if "texture     f32" in line:
                print("    " + line.strip())
        if n_tex != 4:
            print("  -> The hoist did NOT faithfully unroll the loop: iterations are missing.")
            print("     It therefore says NOTHING about whether reordering would be a fix,")
            print("     and is recorded here only so the absence of the diagnostic in this")
            print("     arm is not mistaken for one.")
        else:
            print("  -> A faithful 4-iteration unroll lowered without the diagnostic.")
    print()
    print("== what this file establishes ==")
    print("  1. The diagnostic comes from DxilGenerationPass (a DXIL-lowering pass),")
    print("     not from Sema, and the guard is !CbPtr->hasAllConstantIndices().")
    print("  2. By the time that guard runs, [unroll] has not been applied, so the loop")
    print("     induction variable is still a non-constant SSA value.")
    print("  It does NOT establish what the right fix is, or whether the restriction is")
    print("  intended. That is a design decision, not a measurement.")


if __name__ == "__main__":
    main()
