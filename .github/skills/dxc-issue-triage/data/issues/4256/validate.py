"""#4256 harness: validate a DXIL module and report what was in it.

Registered with `triage.py compiler --id main-debug-dxv`, so `run`, `--expect`,
variants, `audit` and `reindex` all apply to it unchanged (SKILL.md, "When the
symptom is in a pass dxc.exe cannot run, register the harness as a compiler").

Why a harness rather than `dxv.exe` directly: `dxv` prints only
"Validation succeeded." and nothing about the module it validated. A predicate
reading that alone is vacuously satisfied by any module -- including one that
never mentions ViewID -- which is the trap SKILL.md records for absence
findings. The self-test lines below put the anti-vacuity evidence into the same
capture the predicate scores:

  module-calls-viewid-op          the module really does use SV_ViewID
  module-viewid-state             the serialized state, verbatim, or <absent>
  module-viewid-state-declares-dependencies
                                  whether that state claims ANY dependency

If the module cannot be read, or contains no `dx.op` calls at all, the harness
prints PARSE-WARNING and exits non-zero rather than reporting a clean absence.

Usage:  validate.py --version
        validate.py <module.ll>     assemble (via dxv) and validate
        validate.py <shader.hlsl>   compile with dxc first, then the above
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4256/ -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
BIN = os.environ.get("DXC_BIN", os.path.join(REPO, "build", "Debug", "bin"))
DXC = os.path.join(BIN, "dxc.exe")
DXV = os.path.join(BIN, "dxv.exe")

HARNESS_VERSION = "viewid-4256 harness v1"
STATE_RE = re.compile(r"^!dx\.viewIdState = !\{!([0-9]+)\}\s*$", re.MULTILINE)


def display(path):
    """Machine-independent spelling, matching triage.py's `display_exe`.

    Captures are committed, so an absolute path would bake one contributor's
    layout into the repo -- and `scripts/check_paths.py` rejects it.
    """
    p = os.path.abspath(path)
    rel = os.path.relpath(p, REPO)
    if not rel.startswith(os.pardir):
        return "<repo>/" + rel.replace(os.sep, "/")
    return os.path.basename(p)


def dxc_version():
    p = subprocess.run([DXC, "--version"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout.strip().replace("\n", " ")


def echo(argv):
    print("$ " + subprocess.list2cmdline([display(argv[0])] + argv[1:]),
          flush=True)


def run(argv, cwd):
    echo(argv)
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("--- stdout ---")
    print(p.stdout.rstrip())
    print("--- stderr ---")
    print(p.stderr.rstrip())
    print("[exit] 0x%08X" % (p.returncode & 0xFFFFFFFF), flush=True)
    return p.returncode


def find_state(text):
    """Return the serialized ViewID state as a list, or None if absent."""
    hit = STATE_RE.search(text)
    if not hit:
        return None
    node = hit.group(1)
    body = re.search(r"^!%s = !\{\[\d+ x i32\] \[([^\]]*)\]\}\s*$" % node,
                     text, re.MULTILINE)
    if not body:
        print("[PARSE-WARNING] dx.viewIdState names !%s but no i32 array node "
              "of that name was found" % node)
        return None
    return [int(v) for v in re.findall(r"i32 (-?\d+)", body.group(1))]


def report(module_path):
    with open(module_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    print("[module] %s (%d bytes)" % (os.path.basename(module_path), len(text)))

    if "dx.op." not in text:
        print("[PARSE-WARNING] no dx.op call in this file at all -- it is not "
              "a DXIL module and nothing below means anything")
        return False

    uses_viewid = bool(re.search(r"@dx\.op\.viewID\.i32\(i32 138\)", text))
    print("[selftest] module-calls-viewid-op=%s" % ("yes" if uses_viewid else "no"))
    if not uses_viewid:
        print("[PARSE-WARNING] this module does not call the ViewID op, so it "
              "cannot demonstrate anything about ViewID state")

    state = find_state(text)
    if state is None:
        print("[selftest] module-viewid-state=<absent>")
        print("[selftest] module-viewid-state-declares-dependencies=no")
    else:
        print("[selftest] module-viewid-state=%s" % state)
        # Element 0 is the input-scalar count and element 1 the output-scalar
        # count for stream 0; everything after them is dependency bitmasks.
        deps = any(v != 0 for v in state[2:])
        print("[selftest] module-viewid-state-declares-dependencies=%s"
              % ("yes" if deps else "no"))
    return True


def main(argv):
    if not argv or argv[0] in ("--version", "-version", "/?", "--help"):
        print("%s\nunderlying: %s" % (HARNESS_VERSION, dxc_version()))
        return 0

    path = argv[0]
    cwd = os.path.dirname(os.path.abspath(path)) or "."
    print(HARNESS_VERSION)
    print("[validator] internal (dxcompiler.dll from the same build); "
          "DXC_DXIL_DLL_PATH=%s"
          % (os.environ.get("DXC_DXIL_DLL_PATH") or "<unset>"))

    if path.lower().endswith(".hlsl"):
        stem = os.path.splitext(os.path.basename(path))[0]
        emitted = stem + "-emitted.ll"
        rc = run([DXC, "-T", "vs_6_1", "-E", "main",
                  os.path.basename(path), "-Fc", emitted], cwd)
        if rc != 0:
            print("[result] COMPILE-FAILED")
            return rc
        path = os.path.join(cwd, emitted)

    if not os.path.isfile(path):
        print("[PARSE-WARNING] module file not found: %s" % path)
        print("[result] HARNESS-ERROR")
        return 2

    if not report(path):
        print("[result] HARNESS-ERROR")
        return 2

    rc = run([DXV, os.path.basename(path)], cwd)
    print("[result] %s" % ("VALIDATION-SUCCEEDED" if rc == 0
                           else "VALIDATION-FAILED"))
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
