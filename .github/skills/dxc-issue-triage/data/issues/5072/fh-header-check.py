#!/usr/bin/env python
"""Harness for #5072 -- "-Fh results in invalid default identifier for
library targets".

`-Fh <file>` writes dxc's header output *only to that file*; nothing about
the identifier it chose ever reaches stdout/stderr, so a plain `run` over
`cmd.txt` would score a clean-looking "no output" every time regardless of
what happened (SKILL.md step 3: "find where the mode writes its result").
This harness is the "command chain or harness that brings that artifact
into the scored capture": it runs the real dxc.exe with the exact requested
arguments, then reads back whatever `-Fh` target was named and reports
whether the header's declared variable name is a legal C/C++ identifier.

Registered with:
    triage.py compiler --id main-debug-fh --exe <abs path>\\fh-header-check.cmd \
        --commit <the wrapped dxc's commit>

`bisect` refuses a harness-as-compiler issue (SKILL.md), so history for this
issue is measured with the issue-local `release-matrix.py`, which imports
and calls the functions below directly against each release's `dxc.exe`
rather than going through this wrapper.

The real dxc.exe comes from DXC_FH_REAL_EXE, defaulting to this repo's own
Debug build, so the same harness logic can be pointed at any other binary.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# data/issues/5072/ -> repo root is six levels up.
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", ".."))
DEFAULT_DXC = os.path.join(REPO, "build", "Debug", "bin", "dxc.exe")

VALID_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VAR_DECL_RE = re.compile(r"const\s+unsigned\s+char\s+(\S+)\s*\[\]\s*=")


def find_fh_path(argv):
    """Locate the argument following -Fh / /Fh (dxc's header-output flag)."""
    for i, tok in enumerate(argv):
        low = tok.lower()
        if low in ("-fh", "/fh") and i + 1 < len(argv):
            return argv[i + 1]
        if low.startswith(("-fh:", "-fh=", "/fh:", "/fh=")):
            return tok.split(":", 1)[-1].split("=", 1)[-1]
    return None


def check_header(path):
    """Return ('valid'|'valid-noise'|'invalid'|'no-declaration', name_or_None).

    'no-declaration' is the self-test failure mode: the reader could not find
    the line it is looking for at all, which must not be silently scored
    either way (SKILL.md: "an absence predicate is satisfied for free by a
    compile that never got started" -- the mirror trap for a presence
    reader is a broken regex that finds nothing and says nothing).
    """
    if not os.path.isfile(path):
        return ("no-file", None)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = VAR_DECL_RE.search(text)
    if not m:
        return ("no-declaration", None)
    name = m.group(1)
    if VALID_IDENT_RE.match(name):
        return ("valid", name)
    return ("invalid", name)


def real_dxc():
    return os.environ.get("DXC_FH_REAL_EXE", DEFAULT_DXC)


def main(argv):
    exe = real_dxc()
    if argv == ["--version"]:
        # `triage.py compiler` probes the harness with --version to record
        # something in the registry. Answer with the wrapped compiler's own
        # version, prefixed so a stray capture is traceable to the harness.
        real = subprocess.run([exe, "--version"], capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        sys.stdout.write("fh-header-check harness wrapping: " + real.stdout)
        return real.returncode

    proc = subprocess.run([exe] + argv, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    fh_path = find_fh_path(argv)
    if fh_path is None:
        print("FH-HARNESS: no -Fh argument in this command; nothing to check")
        return proc.returncode

    status, name = check_header(fh_path)
    if status == "no-file":
        print(f"FH-HARNESS: -Fh target {fh_path!r} was not produced "
              f"(dxc exit {proc.returncode})")
    elif status == "no-declaration":
        print("FH-HARNESS: could not find a 'const unsigned char "
              "<name>[] =' declaration in the header -- reader self-test "
              "failed, this result must not be scored either way")
    elif status == "valid":
        print(f"FH-HARNESS: IDENTIFIER-VALID name={name!r}")
    else:
        print(f"FH-HARNESS: IDENTIFIER-INVALID name={name!r}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
