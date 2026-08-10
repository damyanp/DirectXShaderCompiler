"""Generate the manual-case captures for issue #3906.

Four things `triage.py run` cannot capture on its own:

  stack    the Debug assert stack out of `cdb`, including the `gh` continuation
           that emulates NDEBUG and walks on to the *second* assert -- the SROA
           infinite-loop guard. This is what ties the Debug signature (assert)
           and the Release signature (hang) to one defect.
  asserts  which assert each shader in this directory trips. `dxc` prints only
           "Internal compiler error: LLVM Assert" to stderr, so the captured
           probes cannot tell two different asserts apart; the debugger can.
  hang     proof that the Release hang is unbounded rather than merely slow.
           triage.py bounds every probe at 60s, and a 60s timeout on its own
           does not distinguish an infinite loop from a slow compile.
  matrix   each shader against release binaries as well as ground truth.
           Catalogued releases are not registered compiler ids, so `triage.py
           run --shader` can only retarget the ground-truth build; testing the
           reporter's three conditions against a *Release* build needs this.

Every command is echoed with subprocess.list2cmdline(argv), so each capture says
exactly what ran rather than asking a reader to trust a transcription. Paths are
tokenised the way triage.py's display_exe does (<repo>, <cache>, <triage>) so the
committed captures are not one machine's directory layout.

  python make-manual-cases.py stack
  python make-manual-cases.py asserts
  python make-manual-cases.py hang [--tag v1.9.2607] [--seconds 600]
  python make-manual-cases.py matrix [--seconds 60]
"""
import argparse
import os
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRIAGE_ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL_DIR = os.path.dirname(TRIAGE_ROOT)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))
CACHE_ROOT = os.path.join(SKILL_DIR, ".cache")

DEBUG_DXC = os.path.join(REPO_ROOT, "build", "Debug", "bin", "dxc.exe")
CDB = r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"
ARGS = ["-T", "cs_6_0", "-E", "main"]

# The repro, the three controls derived from the reporter's own "any one of
# these missing and it will not loop", then the reduction ladder.
SHADERS = [
    ("repro.hlsl", "as filed"),
    ("control-no-member-fn.hlsl", "reporter condition 1 removed"),
    ("control-no-buffer-access.hlsl", "reporter condition 2 removed"),
    ("control-scalar-return.hlsl", "reporter condition 3 removed"),
    ("reduce-nested-struct-member.hlsl", "no buffer at all, no readIndex()"),
    ("reduce-scalar-member.hlsl", "nested struct flattened to a uint"),
    ("reduce-member-array-return.hlsl", "no member data at all"),
    ("reduce-free-array-return.hlsl", "free function, not a member"),
    ("workaround-struct-return.hlsl", "the reporter's stated workaround"),
]

MATRIX_TAGS = ["v1.6.2106", "v1.9.2607"]

NOISE = ("ModLoad:", "NatVis script", ">>>>>>>>>>>>>", "*** WARNING",
         "   ----> ", "   Extension", "   Use", "   Allow", "   Non",
         "   Enable", "   -- Config", "************", "Microsoft (R)",
         "Copyright (c)", "Response ", "Deferred ", "Symbol search",
         "Executable search", "+---", "| ", "CommandLine:", "|")


def tokenise(text):
    """Replace this machine's roots with the workspace's path tokens."""
    for base, token in ((CACHE_ROOT, "<cache>"), (TRIAGE_ROOT, "<triage>"),
                        (REPO_ROOT, "<repo>")):
        for spelling in (base, base.replace("\\", "/"),
                         base.replace("\\", "\\\\")):
            text = text.replace(spelling, token)
    return text


def release_exe(tag):
    """Resolve a release's dxc.exe from the catalog, not from a guessed layout.

    The two physical release roots have different internal shapes -- downloaded
    assets are `<tag>/bin/x64/dxc.exe`, test-seeded trees are
    `<tag>/dxc_<date>/bin/x64/dxc.exe` -- so walking one root silently misses the
    other. `releases.cached_path` is the reconciliation layer. Opened read-only:
    this script must never write shared state.
    """
    db = os.path.join(CACHE_ROOT, "triage.db")
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    try:
        row = con.execute(
            "SELECT cached_path FROM releases WHERE tag = ?", (tag,)).fetchone()
    finally:
        con.close()
    if not row or not row[0]:
        raise SystemExit("no cached dxc for %s; run triage.py catalog" % tag)
    return row[0]


def echo(argv):
    return "$ " + subprocess.list2cmdline(argv) + "\n"


def run_cdb(shader, frames):
    """Run dxc under cdb, continuing past each C++-exception assert.

    `sxe -c "kb N; gh" e0000001` breaks on the assert, prints frames, then goes
    *handled* -- which emulates NDEBUG, so the run walks on exactly as a release
    build would walk on into the loop. A DXASSERT arrives instead as a 0x80000003
    trap, and its message has already been printed by then.

    cdb must be driven through cmd.exe: from PowerShell it produces no output at
    all, which reads as "the debugger found nothing" (SKILL.md, measured on
    #3377).
    """
    cmd = 'sxe -c "kb %d; gh" e0000001; g; q' % frames
    argv = [CDB, "-c", cmd, DEBUG_DXC] + ARGS + [shader]
    # `cmd /s /c "<line>"` strips exactly the outer pair of quotes and passes the
    # rest through verbatim. Without /s -- or with subprocess re-quoting a list --
    # cmd mangles the quoted cdb.exe path and answers "is not recognized as an
    # internal or external command", which looks like a missing debugger.
    line = '%s /s /c "%s"' % (os.environ.get("COMSPEC", "cmd.exe"),
                              subprocess.list2cmdline(argv))
    p = subprocess.run(line, cwd=HERE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return argv, (p.stdout or "") + (p.stderr or "")


def denoise(text):
    out, started = [], False
    for line in text.splitlines():
        if any(line.startswith(n) for n in NOISE) or not line.strip():
            continue
        if line.startswith("Error:"):
            started = True
        if started:
            out.append(line.rstrip())
    return out


def case_stack(out):
    argv, text = run_cdb("repro.hlsl", 12)
    out.write(tokenise(
        "# manual case: Debug assert stack for #3906\n"
        "# generated by: python make-manual-cases.py stack\n"
        "# cwd: <triage>/issues/3906\n"
        "# Trimmed to the assert text and the frames; module loads, the debugger\n"
        "# banner and blank lines are dropped as noise. Nothing else is altered.\n"
        "#\n"
        "# The FIRST assert is what a Debug build stops on. `gh` continues past it,\n"
        "# which is what a Release build does with the assert compiled out -- and\n"
        "# the run then reaches the SECOND assert, whose message is the reported\n"
        "# symptom. In a real Release build that guard is compiled out too\n"
        "# (DXASSERT_LOCALVAR -> `do { (void)(local); } while (0)` under NDEBUG,\n"
        "# include/dxc/Support/Global.h), so nothing stops the loop.\n"
        "\n" + echo(argv) + "\n" + "\n".join(denoise(text)) + "\n"))


def case_asserts(out):
    out.write(tokenise(
        "# manual case: which assert does each shader trip? -- #3906\n"
        "# generated by: python make-manual-cases.py asserts\n"
        "# cwd: <triage>/issues/3906\n"
        "# dxc prints only 'Internal compiler error: LLVM Assert' to stderr, so the\n"
        "# captured probes cannot tell two different asserts apart. Each shader is\n"
        "# run under cdb and only the assert identity lines are kept.\n"
        "#   0xE0000001 = C++-exception assert (LLVM/CRT assert)\n"
        "#   0x80000003 = __debugbreak() trap (DXASSERT)\n"))
    for shader, why in SHADERS:
        argv, text = run_cdb(shader, 1)
        keep = [ln for ln in denoise(text)
                if ln.startswith(("Error:", "File:", "Func:", "\t"))
                or ln.lstrip().startswith(("C:", "<repo>", "/"))
                or "exception - code" in ln
                or "Assertion" in ln]
        out.write(tokenise(
            "\n\n=== %s  (%s) ===\n%s%s\n"
            % (shader, why, echo(argv),
               "\n".join(keep) if keep else "(no assert; ran to completion)")))


def case_hang(out, tag, seconds):
    exe = release_exe(tag)
    argv = [exe] + ARGS + ["repro.hlsl"]
    out.write(tokenise(
        "# manual case: is the release hang unbounded, or merely slow? -- #3906\n"
        "# generated by: python make-manual-cases.py hang --tag %s --seconds %d\n"
        "# cwd: <triage>/issues/3906\n"
        "# triage.py bounds every probe at 60s, and a 60s timeout alone cannot\n"
        "# tell an infinite loop from a slow compile. This runs the same command\n"
        "# for %ds. A slow compile finishes; an infinite loop does not.\n"
        "\n" % (tag, seconds, seconds) + echo(argv)))
    rc, out_s, err_s, timed_out, elapsed = timed_run(argv, seconds)
    out.write(tokenise(
        "[compiler] %s\n"
        "[exit] %s\n"
        "[elapsed] %.1fs\n"
        "--- stdout ---\n%s\n--- stderr ---\n%s\n"
        % (tag,
           "STILL RUNNING AFTER %.0fs -- killed by the harness" % elapsed
           if timed_out else rc,
           elapsed, out_s, err_s)))


def timed_run(argv, seconds):
    start = time.time()
    try:
        p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=seconds)
        return p.returncode, p.stdout, p.stderr, False, time.time() - start
    except subprocess.TimeoutExpired as e:
        dec = lambda b: b.decode("utf-8", "replace") if isinstance(b, bytes) \
            else (b or "")
        return None, dec(e.stdout), dec(e.stderr), True, time.time() - start


def case_matrix(out, seconds):
    out.write(tokenise(
        "# manual case: the reporter's three conditions against RELEASE builds -- #3906\n"
        "# generated by: python make-manual-cases.py matrix --seconds %d\n"
        "# cwd: <triage>/issues/3906\n"
        "# Catalogued releases are not registered compiler ids, so triage.py run\n"
        "# --shader can only retarget ground truth. Release builds are where the\n"
        "# reported symptom is a hang, so the reporter's claim that removing any\n"
        "# one condition avoids the loop has to be tested on them too.\n"
        "# v1.6.2106 (2021-07-01) is the release nearest the 2021-08-13 report.\n"
        "# Bound: %ds per run. HANG means still running when the bound expired.\n"
        % (seconds, seconds)))
    for shader, why in SHADERS:
        out.write("\n\n=== %s  (%s) ===\n" % (shader, why))
        for tag in MATRIX_TAGS:
            argv = [release_exe(tag)] + ARGS + [shader]
            out.write(tokenise(echo(argv)))
            rc, out_s, err_s, to, elapsed = timed_run(argv, seconds)
            first = ""
            for line in ((err_s or "") + (out_s or "")).splitlines():
                if line.strip():
                    first = "  | " + line.strip()
                    break
            out.write("[%s] %s  (%.1fs)%s\n"
                      % (tag, "HANG" if to else "exit %s" % rc, elapsed,
                         "\n" + first if first else ""))


def case_cpu(out, tag, seconds):
    """Is the hang a spin or a blocked wait?

    A timeout says only that the process did not finish. Sampling the child's
    kernel+user CPU time separates a busy loop (CPU tracks wall clock) from a
    deadlock or an I/O wait (CPU flat near zero) -- two quite different bugs
    that a timeout alone cannot tell apart.
    """
    exe = release_exe(tag)
    argv = [exe] + ARGS + ["repro.hlsl"]
    out.write(tokenise(
        "# manual case: is the hang a spin or a blocked wait? -- #3906\n"
        "# generated by: python make-manual-cases.py cpu --tag %s --seconds %d\n"
        "# cwd: <triage>/issues/3906\n"
        "# A timeout only says the process did not finish. Sampling the child's\n"
        "# CPU time tells a busy loop from a deadlock or an I/O wait: a spinning\n"
        "# process accrues CPU at ~1s per elapsed second, a blocked one does not.\n"
        "# Sampled with Win32 GetProcessTimes through ctypes -- no extra deps.\n"
        "\n" % (tag, seconds) + echo(argv)))
    p = subprocess.Popen(argv, cwd=HERE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    start = time.time()
    out.write("  elapsed     cpu    cpu/elapsed\n")
    try:
        while time.time() - start < seconds:
            time.sleep(seconds / 6.0)
            if p.poll() is not None:
                break
            el = time.time() - start
            cpu = process_cpu_seconds(p.pid)
            out.write("  %6.1fs  %6.1fs   %5.2f\n"
                      % (el, cpu, cpu / el if el else 0.0))
    finally:
        alive = p.poll() is None
        if alive:
            p.kill()
        p.communicate()
    out.write("\n[compiler] %s\n[result] %s\n"
              % (tag, "STILL RUNNING AFTER %ds -- killed by the harness" % seconds
                 if alive else "exited %s" % p.returncode))


def process_cpu_seconds(pid):
    """Kernel+user CPU seconds for a live pid, via Win32 GetProcessTimes."""
    import ctypes
    from ctypes import wintypes
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return float("nan")
    try:
        creation = wintypes.FILETIME()
        exit_ = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not k32.GetProcessTimes(h, ctypes.byref(creation), ctypes.byref(exit_),
                                   ctypes.byref(kernel), ctypes.byref(user)):
            return float("nan")
        to_s = lambda ft: ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 1e7
        return to_s(kernel) + to_s(user)
    finally:
        k32.CloseHandle(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=["stack", "asserts", "hang", "matrix", "cpu"])
    ap.add_argument("--tag", default="v1.9.2607")
    ap.add_argument("--seconds", type=int)
    a = ap.parse_args()
    names = {"stack": "manual-case-assert-stack.txt",
             "asserts": "manual-case-assert-identity.txt",
             "hang": "manual-case-long-timeout.txt",
             "matrix": "manual-case-condition-matrix.txt",
             "cpu": "manual-case-cpu-sample.txt"}
    path = os.path.join(HERE, names[a.case])
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        if a.case == "stack":
            case_stack(f)
        elif a.case == "asserts":
            case_asserts(f)
        elif a.case == "hang":
            case_hang(f, a.tag, a.seconds or 600)
        elif a.case == "cpu":
            case_cpu(f, a.tag, a.seconds or 90)
        else:
            case_matrix(f, a.seconds or 60)
    print("wrote", os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
