#!/usr/bin/env python
"""Generate manual-case-cl-compile.txt for #5072.

The reported symptom is a C/C++ *compile failure*: the header dxc emits for
a library target under -Fh (no -Vn) declares its variable under an invalid
identifier, so #including it in a real project does not compile. This
script is the direct instrument for that literal claim -- it feeds the
headers already produced by `triage.py run` (out-header.h, the repro; and
out-header-vn.h, the -Vn control) to the real MSVC compiler (cl.exe) as
both C and C++, and records whether each one compiles.

Every command actually run is echoed via subprocess.list2cmdline(argv)
before its output, so nothing here has to be trusted -- it can be re-run
verbatim (SKILL.md: "a transcribed command line is an assertion ... commit
the generator next to its output").
"""
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# data/issues/5072/ -> repo root is six levels up. Derived from this file's
# own location rather than hardcoded, so the path this script redacts is
# always *this* checkout's, not whichever machine first ran it (SKILL.md:
# "never a token baked into an executable file").
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", ".."))
_REPO_PREFIX_RE = re.compile(
    r"(?i)" + re.escape(REPO_ROOT).replace(r"\\", r"[\\\\]+"))


def redact(text):
    """Replace this checkout's absolute root with <repo> in committed text.

    cl.exe's diagnostics quote the header's full path verbatim, and the
    command line this script echoes does too -- both bake in the
    contributor's checkout directory, which `check_paths.py` rejects. Only
    the prefix is redacted; the path *within* the tree (which header, which
    line) is the informative part and stays.
    """
    return _REPO_PREFIX_RE.sub("<repo>", text)


def find_cl():
    env_cl = os.environ.get("FH5072_CL_EXE")
    if env_cl and os.path.isfile(env_cl):
        return env_cl
    candidates = []
    for root in (r"C:\Program Files\Microsoft Visual Studio",
                 r"C:\Program Files (x86)\Microsoft Visual Studio"):
        candidates += glob.glob(os.path.join(
            root, "*", "*", "VC", "Tools", "MSVC", "*", "bin", "HostX64",
            "x64", "cl.exe"))
    return candidates[0] if candidates else None


def run_cl(cl_exe, header_path, mode_flag):
    # /Fo sends the .obj into bin/ (gitignored) instead of littering the
    # committed issue directory with build output that carries no evidence
    # of its own -- the compile's exit status and diagnostics are the
    # evidence, not the object file.
    bin_dir = os.path.join(HERE, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    argv = [cl_exe, "/nologo", "/c", mode_flag,
            f"/Fo{bin_dir}\\", header_path]
    proc = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = [f"$ {subprocess.list2cmdline(argv)}",
           f"[exit] {proc.returncode}",
           "--- stdout ---", proc.stdout,
           "--- stderr ---", proc.stderr]
    return proc.returncode, redact("\n".join(out))


def main():
    cl_exe = find_cl()
    lines = []
    if not cl_exe:
        lines.append("cl.exe not found under the usual Visual Studio "
                      "install roots; set FH5072_CL_EXE to an absolute "
                      "path and re-run this script.")
        print("\n".join(lines))
        return 1
    lines.append(f"# cl.exe: {cl_exe}")

    cases = [
        ("repro (no -Vn, from out-header.h)", "out-header.h"),
        ("-Vn workaround control (from out-header-vn.h)", "out-header-vn.h"),
    ]
    for label, header in cases:
        path = os.path.join(HERE, header)
        lines.append(f"\n## {label}: {header}")
        if not os.path.isfile(path):
            lines.append(f"MISSING: {header} not present -- run "
                          f"`triage.py run --issue 5072 --compiler "
                          f"main-debug-fh` (and the vn-control variant) "
                          f"first.")
            continue
        for mode_flag, mode_name in (("/TC", "C"), ("/TP", "C++")):
            rc, text = run_cl(cl_exe, path, mode_flag)
            lines.append(f"\n### as {mode_name} ({mode_flag})")
            lines.append(text)
            lines.append(f"[{mode_name} result] "
                         f"{'COMPILES' if rc == 0 else 'FAILS: exit ' + str(rc)}")

    out_path = os.path.join(HERE, "manual-case-cl-compile.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
