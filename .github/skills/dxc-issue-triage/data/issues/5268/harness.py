#!/usr/bin/env python
"""Harness for DXC issue #5268.

`dxr.exe` (the standalone HLSL rewriter) is not `dxc.exe`, so it cannot be
driven through `triage.py run`'s normal cmd.txt-over-dxc path. This wraps a
two-stage pipeline as a single "compiler" so the rest of the tool
(`run`, `audit`, `reindex`) can treat it like one, following the
"harness-as-compiler" pattern documented in SKILL.md for issues whose symptom
lives outside anything dxc.exe itself runs (e.g. #2918/#2922/#2923's PIX
passes).

Stage 1: run dxr.exe with the exact arguments the issue reports
         (`-E <entry> -remove-unused-globals <source>`), capturing the
         rewritten HLSL it emits on stdout.
Stage 2: feed that rewritten HLSL back into dxc.exe as a normal compile, to
         show whether the rewriter produced source that no longer compiles.

Both stages' outputs are printed, clearly separated, so a predicate can match
either the rewriter's own output (to check whether it kept/dropped a specific
declaration) or the recompile's diagnostics (to check whether the rewritten
source is broken).

The entry point in this issue (VSMain) is a vertex shader; -T is fixed to
vs_6_0 for the recompile stage rather than derived generically from -E, since
this harness only needs to answer this issue's question.

Executables are taken from DXR_EXE / DXC_EXE environment variables, falling
back to `<repo>/build/Release/bin/dxr.exe` and `<repo>/build/Debug/bin/dxc.exe`
(repo root found by walking up from this file to the `.git` directory, never
hardcoded), so the same harness could, in principle, be repointed at a
different release's tools without editing this file.
"""
import os
import subprocess
import sys


def find_repo_root(start):
    """Walk upward from this script to the checkout containing `.git`.

    Deliberately not a hardcoded machine path: a committed repro has to run
    from any clone of the repo (see SKILL.md's #2427 lesson about a harness
    hardcoding one contributor's exe path).
    """
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


_REPO_ROOT = find_repo_root(os.path.dirname(__file__))
_DEFAULT_DXR = (os.path.join(_REPO_ROOT, "build", "Release", "bin", "dxr.exe")
                if _REPO_ROOT else None)
_DEFAULT_DXC = (os.path.join(_REPO_ROOT, "build", "Debug", "bin", "dxc.exe")
                if _REPO_ROOT else None)

DXR_EXE = os.environ.get("DXR_EXE", _DEFAULT_DXR)
DXC_EXE = os.environ.get("DXC_EXE", _DEFAULT_DXC)

if not DXR_EXE or not DXC_EXE:
    sys.exit("harness-5268: could not locate dxr.exe/dxc.exe; set DXR_EXE "
              "and DXC_EXE, or run from inside a checkout of the repo.")

RECOMPILE_PROFILE = "vs_6_0"

# Mirrors triage.py's INTERNAL_STATUS/E_FAIL (scripts/triage.py). Duplicated
# rather than imported so this harness has no dependency on the triage tool's
# internals, per SKILL.md: "return a small documented wrapper status and print
# the real hexadecimal status and classification in the captured text" rather
# than relaying a raw HRESULT through sys.exit(), which silently truncates any
# value above 0x7FFFFFFF (measured here: exit(2147500037) produced 4294967295,
# not 0x80004005) and can turn a clean diagnosed error into a crash-looking
# unsigned wrapper status.
E_FAIL = 0x80004005
INTERNAL_STATUS = frozenset((
    0xC0000005, 0xC00000FD, 0x80000003, 0x80AA0018, 0x80AA001B,
    0x80AA001C, 0x80AA001D, 0xE0000001, 0xE0000002, 0xE0000003,
))


def classify(rc):
    """Return (label, is_internal_failure) for a dxc-style exit status."""
    if rc is None:
        return "timeout", True
    code = rc & 0xFFFFFFFF
    if code == 0:
        return "success", False
    if code in INTERNAL_STATUS:
        return "internal-failure", True
    if code != E_FAIL and (code >> 28) in (0xC, 0xE):
        return "internal-failure", True
    if code == 139 or code == 134:
        return "internal-failure", True
    if code == E_FAIL:
        return "diagnosed-error", False
    return "other:0x%08X" % code, False


def run(argv):
    proc = subprocess.run(argv, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main():
    args = sys.argv[1:]

    if args == ["--version"]:
        dxr_rc, dxr_out = run([DXR_EXE, "--version"])
        dxc_rc, dxc_out = run([DXC_EXE, "--version"])
        print("harness-5268 (dxr + dxc pipeline)")
        print("dxr: " + display_exe(DXR_EXE) + " -- " + dxr_out.strip())
        print("dxc: " + display_exe(DXC_EXE) + " -- " + dxc_out.strip())
        return 0

    # args is exactly cmd.txt's line, e.g. ["-E", "VSMain",
    # "-remove-unused-globals", "repro.hlsl"]
    source = args[-1]
    rewrite_argv = [DXR_EXE] + args
    print("$ " + subprocess.list2cmdline(rewrite_argv))
    rw_rc, rw_out = run(rewrite_argv)
    print("# dxr exit: " + str(rw_rc))
    print("---- dxr (rewriter) output ----")
    print(rw_out)

    rewritten_path = "harness-rewritten.hlsl"
    with open(rewritten_path, "w") as f:
        f.write(rw_out)

    entry = None
    for i, a in enumerate(args):
        if a == "-E" and i + 1 < len(args):
            entry = args[i + 1]
    if entry is None:
        entry = "main"

    recompile_argv = [DXC_EXE, "-T", RECOMPILE_PROFILE, "-E", entry,
                      rewritten_path]
    print("$ " + subprocess.list2cmdline(recompile_argv))
    rc_rc, rc_out = run(recompile_argv)
    label, is_internal = classify(rc_rc)
    print("# dxc (recompile) exit-hex: 0x%08X" % (rc_rc & 0xFFFFFFFF
                                                    if rc_rc is not None
                                                    else 0))
    print("# dxc (recompile) classification: " + label)
    print("---- dxc (recompile of rewritten output) output ----")
    print(rc_out)

    # The harness's own exit status is a small, fixed, documented code -- NOT
    # a relay of the recompile's raw HRESULT (which does not survive
    # sys.exit() intact; see the comment on classify()). match.json scores
    # the "# dxc (recompile) classification:" line printed above, not this
    # process exit code.
    #   0 = recompile succeeded (rewriter did not break the source)
    #   1 = recompile failed with an ordinary diagnosed error (this issue's
    #       reported symptom: rewriter removed something still referenced)
    #   2 = recompile crashed / timed out (unexpected; not this issue's claim)
    if label == "success":
        return 0
    if is_internal:
        return 2
    return 1


def display_exe(path):
    # Keep this machine-independent: anchor on the repo name rather than an
    # absolute path (see SKILL.md's path-redaction guidance).
    marker = "DirectXShaderCompiler"
    idx = path.find(marker)
    if idx == -1:
        return path
    return "<repo>" + path[idx + len(marker):]


if __name__ == "__main__":
    sys.exit(main())
