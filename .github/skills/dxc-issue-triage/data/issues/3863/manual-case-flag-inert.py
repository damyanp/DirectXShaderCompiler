"""Issue 3863: is `-H` inert with respect to what `-P` produces?

SKILL.md and #3044 both record that exit 0 proves nothing about whether an
option was honoured, and that the decisive instrument is a byte comparison of
the produced artifact with and without the option. This runs that comparison on
every stable release plus the ground-truth build is NOT its job -- see
manual-case-release-history.py for the release sweep. Here the question is
narrower and is asked only of `main-debug`:

  Does adding `-H` (or its alias `-Vi`) change one byte of the preprocessed
  output `-P` writes?

Each run happens in a fresh scratch directory holding copies of the repro and
its headers, so no committed evidence can be touched, and each command is
echoed exactly as executed via subprocess.list2cmdline.

SELF-TEST: the script asserts it actually produced a non-empty .i containing
both header bodies. A comparison of two files that do not exist would otherwise
report "identical" and mean nothing.

Usage (from the workspace root):
    python data/issues/3863/manual-case-flag-inert.py > \
           data/issues/3863/manual-case-flag-inert.txt
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

SOURCES = ("repro.hlsl", "inc-pp-a.h", "inc-pp-b.h")
BODY_MARKERS = ("ppmarker3863 = 1;", "ppnested3863 = 2;")

CASES = [
    ("no-flag", []),
    ("-H", ["-H"]),
    ("-Vi", ["-Vi"]),
]


def main():
    exe = triage.resolve_compiler("main-debug")
    ver = subprocess.run([exe, "--version"], capture_output=True, text=True)
    print("compiler: main-debug")
    print("exe:      %s" % triage.display_exe(exe))
    print("version:  %s" % ver.stdout.strip())
    print()

    work = os.path.join(HERE, "work-flag-inert")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    for s in SOURCES:
        shutil.copy(os.path.join(HERE, s), work)

    results = []
    selftest_ok = True
    for label, extra in CASES:
        out = "out-%s.i" % label.lstrip("-/").lower()
        argv = ["-P", "repro.hlsl", "-Fi", out] + extra
        print("$ dxc %s" % subprocess.list2cmdline(argv))
        p = subprocess.run([exe] + argv, cwd=work, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        stream = (p.stdout or "") + (p.stderr or "")
        print("  exit=%d  stdout+stderr=%d bytes%s"
              % (p.returncode, len(stream),
                 ("  " + stream.strip().splitlines()[0][:90])
                 if stream.strip() else "  (empty)"))
        path = os.path.join(work, out)
        data = open(path, "rb").read() if os.path.isfile(path) else b""
        digest = hashlib.sha256(data).hexdigest() if data else "-"
        text = data.decode("utf-8", "replace")
        bodies = all(m in text for m in BODY_MARKERS)
        traced = "Opening file [" in stream
        if not (data and bodies):
            selftest_ok = False
        print("  produced %d bytes  sha256=%s  header-bodies-present=%s"
              " include-trace-printed=%s"
              % (len(data), digest[:32], bodies, traced))
        results.append((label, digest, len(data), bodies, traced))
        print()

    print("summary")
    print("%-10s %-34s %8s %-14s %-14s"
          % ("flag", "sha256(preprocessed output)[:32]", "bytes",
             "header-bodies", "trace-printed"))
    for label, digest, size, bodies, traced in results:
        print("%-10s %-34s %8d %-14s %-14s"
              % (label, digest[:32], size, bodies, traced))

    base = results[0][1]
    print()
    print("SELF-TEST: every run produced a .i carrying both header bodies: %s"
          % ("PASS" if selftest_ok else "FAIL -- comparison means nothing"))
    print("all outputs byte-identical to the no-flag run: %s"
          % all(r[1] == base for r in results))
    print("any run printed an include trace: %s"
          % any(r[4] for r in results))
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
