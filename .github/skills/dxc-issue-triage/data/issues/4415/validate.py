"""#4415 harness: hand a DXIL module to the validator and say what was in it.

Registered with `triage.py compiler --id main-debug-dxv4415`, so `run`,
`--expect`, variants and `audit` all apply to it unchanged (SKILL.md, "When the
symptom is in a pass dxc.exe cannot run, register the harness as a compiler").

Why a harness rather than `dxv.exe` directly: `dxv` prints "Validation
succeeded." and nothing whatsoever about the module it validated. A predicate
reading that line alone is satisfied by a module with no `annotateHandle` in it,
by a module it failed to read, and by a run that never happened -- the vacuity
trap SKILL.md records for absence findings. The self-test lines below put the
anti-vacuity evidence into the same capture the predicate scores:

  module-annotatehandle-calls      how many dx.op.annotateHandle calls exist
  annotatehandle-res-operands      the `res` operand of each one, verbatim
  annotatehandle-invalid-res-operand
                                   whether any of them is undef/zeroinitializer

If the module cannot be read, holds no `dx.op` call, or holds no
`annotateHandle` call, the harness prints PARSE-WARNING and exits non-zero
rather than reporting a clean acceptance.

Usage:  validate.py --version
        validate.py <module.ll>          validate that module
        validate.py --dxv <path> <mod>   validate with a specific dxv.exe
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4415/ -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
BIN = os.environ.get("DXC_BIN", os.path.join(REPO, "build", "Debug", "bin"))
DXC = os.path.join(BIN, "dxc.exe")
DXV = os.path.join(BIN, "dxv.exe")

# Normalise machine paths with triage.py's own rule rather than reimplementing
# it here; it tokenises the checkout, triage and release-cache roots, matching
# either separator, repeated separators and any case.
sys.path.insert(0, os.path.join(REPO, ".github", "skills", "dxc-issue-triage",
                                "scripts"))
import triage  # noqa: E402

HARNESS_VERSION = "annotatehandle-4415 harness v1"

# call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle <res>, ...
ANNOT_RE = re.compile(
    r"@dx\.op\.annotateHandle\(i32 216, %dx\.types\.Handle ([^,]+),")
INVALID_OPERANDS = ("undef", "zeroinitializer", "null")


def display(path):
    """Machine-independent spelling, via triage.py's own redact_paths().

    Captures are committed, so an absolute path would bake one contributor's
    layout into the repo -- and `scripts/check_paths.py` rejects it. Reusing
    triage.py's rule rather than reimplementing it keeps this harness's output
    tokenised the same way as every capture triage.py writes.
    """
    return triage.redact_paths(os.path.abspath(path)).replace(os.sep, "/")


def dxc_version():
    p = subprocess.run([DXC, "--version"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout.strip().replace("\n", " ")


def run(argv, cwd):
    print("$ " + subprocess.list2cmdline(
        [display(a) if os.path.isabs(a) else a for a in argv]), flush=True)
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("--- stdout ---")
    print(triage.redact_paths(p.stdout.rstrip()))
    print("--- stderr ---")
    print(triage.redact_paths(p.stderr.rstrip()))
    print("[exit] 0x%08X" % (p.returncode & 0xFFFFFFFF), flush=True)
    return p.returncode


def report(module_path):
    """Print what is in the module. False means nothing below is meaningful."""
    with open(module_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    print("[module] %s (%d bytes)" % (os.path.basename(module_path), len(text)))

    if "dx.op." not in text:
        print("[PARSE-WARNING] no dx.op call in this file at all -- it is not "
              "a DXIL module and nothing below means anything")
        return False

    operands = [op.strip() for op in ANNOT_RE.findall(text)]
    print("[selftest] module-annotatehandle-calls=%d" % len(operands))
    if not operands:
        print("[PARSE-WARNING] this module makes no dx.op.annotateHandle call, "
              "so it cannot demonstrate anything about #4415")
        return False

    print("[selftest] annotatehandle-res-operands=%s" % operands)
    invalid = [op for op in operands if op in INVALID_OPERANDS]
    print("[selftest] annotatehandle-invalid-res-operand=%s"
          % ("yes" if invalid else "no"))

    m = re.search(r"^!dx\.valver = !\{!(\d+)\}\s*$", text, re.MULTILINE)
    if m:
        node = re.search(r"^!%s = !\{i32 (\d+), i32 (\d+)\}\s*$" % m.group(1),
                         text, re.MULTILINE)
        valver = "%s.%s" % node.groups() if node else "<unreadable>"
    else:
        valver = "<absent>"
    print("[selftest] module-requests-validator-version=%s" % valver)
    return True


def main(argv):
    if not argv or argv[0] in ("--version", "-version", "/?", "--help"):
        print("%s\nunderlying: %s" % (HARNESS_VERSION, dxc_version()))
        return 0

    dxv = DXV
    if argv[0] == "--dxv":
        dxv = argv[1]
        argv = argv[2:]

    path = os.path.join(HERE, argv[0]) if not os.path.isabs(argv[0]) else argv[0]
    cwd = os.path.dirname(path) or "."
    print(HARNESS_VERSION)
    print("[validator] %s" % display(dxv))
    # dxv loads the INTERNAL validator out of dxcompiler.dll unless
    # DXC_DXIL_DLL_PATH names an absolute path to dxil.dll
    # (lib/DxcSupport/dxcapi.extval.cpp, DxcDllExtValidationLoader::
    # InitializeForDll). A dxil.dll merely sitting beside dxv.exe is NOT used.
    print("[external-validator] DXC_DXIL_DLL_PATH=%s"
          % (os.environ.get("DXC_DXIL_DLL_PATH") or "<unset> (internal "
             "validator from dxcompiler.dll)"))

    if not os.path.isfile(path):
        print("[PARSE-WARNING] module file not found: %s"
              % os.path.basename(path))
        print("[result] HARNESS-ERROR")
        return 2

    if not report(path):
        print("[result] HARNESS-ERROR")
        return 2

    rc = run([dxv, os.path.basename(path)], cwd)
    print("[result] %s" % ("VALIDATION-SUCCEEDED" if rc == 0
                           else "VALIDATION-FAILED"))
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
