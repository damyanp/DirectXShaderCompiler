"""Fixed-reader cross-check for issue 4701's group-shared-memory byte count.

The ground-truth build's disassembly prints `; NumBytesGroupSharedMemory: 40` for repro.hlsl
and `0` for the static reference case, which is the missed optimisation in user-visible form:
the compiled artifact reserves 40 bytes of group shared memory that no instruction ever reads.

Before quoting that number as a release-history fact it has to be checked, because a PSV field
is an INSTRUMENT and instruments change.  This script holds the reader fixed (the ground-truth
`dxc -dumpbin`) and varies the producer, which is the only way to tell "this release did not
reserve the memory" from "this release's container cannot express the field".

Result is recorded in manual-case-tgsm-crosscheck.txt.  Temporary containers are deleted.

Run from anywhere:  python release-matrix.py's sibling, i.e. python tgsm-crosscheck.py
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import triage  # noqa: E402

RE_TGSM = re.compile(r"^; NumBytesGroupSharedMemory: (\d+)", re.M)
SHADERS = [("repro", "repro.hlsl"), ("static", "control-static.hlsl")]
PRODUCERS = ["v1.4.1907", "v1.7.2207", "v1.8.2502", "v1.9.2607"]


def run(argv, log):
    log.append("$ " + triage.redact_paths(subprocess.list2cmdline(argv)))
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                       errors="replace", timeout=300)
    return p, triage.redact_paths((p.stdout or "") + (p.stderr or ""))


def main():
    c = triage.con()
    reader = c.execute(
        "SELECT exe_path FROM compilers WHERE id = 'main-debug'").fetchone()["exe_path"]
    log = []
    log.append("Issue 4701 -- is the group-shared-memory byte count readable per release?")
    log.append("")
    log.append("Reader held FIXED at the ground-truth build; producer varied.")
    log.append("reader = " + triage.display_exe(reader))
    log.append("")

    rows = []
    producers = [(t, c.execute("SELECT cached_path FROM releases WHERE tag = ?",
                               (t,)).fetchone()["cached_path"]) for t in PRODUCERS]
    producers.append(("main-debug", reader))

    for tag, exe in producers:
        for arm, shader in SHADERS:
            obj = os.path.join(HERE, f"tgsm-{tag}-{arm}.dxil")
            p, _ = run([exe, "-T", "cs_6_0", "-E", "main", shader, "-Fo", obj], log)
            if p.returncode != 0 or not os.path.exists(obj):
                rows.append((tag, arm, "COMPILE-FAILED", f"rc={p.returncode}"))
                continue
            # the producer's own disassembly of its own output
            _, own = run([exe, "-T", "cs_6_0", "-E", "main", shader], log)
            m_own = RE_TGSM.search(own)
            # the fixed reader's view of the same container
            _, via = run([reader, "-dumpbin", obj], log)
            m_via = RE_TGSM.search(via)
            rows.append((tag, arm,
                         m_own.group(1) if m_own else "field-absent",
                         m_via.group(1) if m_via else "field-absent"))
            os.remove(obj)

    log.append("")
    hdr = f"{'producer':<14} {'arm':<8} {'own disassembly':<16} {'via fixed reader':<16}"
    log.append(hdr)
    log.append("-" * len(hdr))
    for tag, arm, own, via in rows:
        log.append(f"{tag:<14} {arm:<8} {own:<16} {via:<16}")

    log.append("")
    ok = [r for r in rows if r[3] not in ("field-absent", "COMPILE-FAILED")]
    if len(ok) == 2 and all(r[0] == "main-debug" for r in ok):
        log.append(
            "CONCLUSION: NumBytesGroupSharedMemory is a post-v1.9.2607 addition to the PSV0\n"
            "runtime-info part.  No catalogued release emits it, and the fixed reader cannot\n"
            "recover it from a release-produced container either -- the field is not in those\n"
            "containers to be read.  So the byte count is evidence about the GROUND-TRUTH\n"
            "build only, and must be quoted that way.  The release history rests instead on\n"
            "the surviving `addrspace(3) global [10 x float]` and its store, which are present\n"
            "in every release's DXIL (see manual-case-release-matrix.txt).")
    else:
        log.append("CONCLUSION: unexpected shape -- re-read the table above before quoting it. "
                   f"{len(ok)} row(s) produced a byte count via the fixed reader.")

    text = triage.redact_paths("\n".join(log) + "\n")
    with open(os.path.join(HERE, "manual-case-tgsm-crosscheck.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
