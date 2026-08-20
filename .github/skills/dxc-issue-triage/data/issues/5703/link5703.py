#!/usr/bin/env python
"""#5703 harness: compile a library, link it to a concrete shader profile,
and report whether the RDAT (RuntimeData) container part survives.

The reported symptom -- "RDAT part is missing when linking a compute
shader" -- needs two different executables (`dxc` to compile the library,
`dxl` to link it) plus a container-part reader, while `triage.py run` hands
every `cmd.txt` line to one registered executable. Per SKILL.md ("When the
symptom is in a pass dxc.exe cannot run, register the harness as a
compiler"), this script is registered as a compiler so `run`, `--shader`,
`--args`, `--expect` and `reindex` all keep working over it.

Container parsing is done directly from the documented binary layout
(include/dxc/DxilContainer/DxilContainer.h: DxilContainerHeader,
DxilPartHeader, `#pragma pack(push, 1)`), not through IDxcContainerReflection
or `dxa`, so the only "reader" in play is this file, which is small enough
to review in full and which self-tests against a known-RDAT-bearing
container on every single run (see `--lib-profile` stage below), rather
than needing a separately-run positive control to prove the reader can
detect a present part at all.

Argument spec for a `cmd.txt` line handed to this compiler (arguments
only, no exe path -- same convention `run --args` and `bisect` expect):

    --entry <name> --lib-profile <profile> --link-profile <profile>
      [--direct-profile <profile>] [-O0|-O1|-O2|-O3] <source.hlsl>

Stage A (always run): compile <source.hlsl> as --lib-profile (a library
profile, e.g. lib_6_3). This is the in-run self-test / anti-vacuity check:
a library compile is defined (DxilContainerAssembler.cpp) to always emit
RDAT, so if this stage's container is missing it, the reader or compiler
is broken, not the subject under test. Printed as "unlinked-lib-RDAT:".

Stage B (always run): link the stage-A library to --link-profile with
--entry as the entry point (IDxcLinker::Link semantics, exposed here via
`dxl <args>`, which tools/clang/tools/dxl/dxl.cpp implements as `dxc.exe`
plus a trailing `-link`). Printed as "linked-RDAT:" -- this is the
reported symptom.

Stage C (only if --direct-profile is given): compile <source.hlsl>
directly to --direct-profile with no linker step at all, to separate "the
linker strips RDAT" from "no non-library container ever has RDAT,
regardless of how it was produced". Printed as "direct-RDAT:".

Every subprocess invocation is echoed with `subprocess.list2cmdline`, with
paths printed relative to <repo>/<skill> so no machine layout lands in a
committed capture.
"""

import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LOCAL_BIN = os.environ.get("DXC_LINK5703_BIN") or os.path.join(
    REPO, "build", "Release", "bin")

RDAT_FOURCC = b"RDAT"


def display(path):
    """Machine-independent spelling of a path, for committed captures."""
    full = os.path.abspath(path)
    for root, name in ((SKILL, "<skill>"), (REPO, "<repo>")):
        if full.lower().startswith(root.lower() + os.sep):
            return name + full[len(root):].replace("\\", "/")
    return full


def display_arg(arg):
    """Like display(), but leaves plain option tokens (`-T`, `cs_6_3`, ...)
    alone. display() calls os.path.abspath, which resolves *any* string
    against the current working directory -- turning a bare flag or
    profile name into a fabricated path under the scratch cwd
    (`triage.py run` launches this harness inside a per-probe scratch
    directory). Only rewrite what is already an absolute filesystem path;
    an argument is otherwise printed exactly as it was passed in."""
    if os.path.isabs(arg):
        return display(arg)
    return arg


def tool(name):
    exe = os.path.join(LOCAL_BIN, name + ".exe")
    if not os.path.isfile(exe):
        sys.exit(f"link5703: {display(exe)} does not exist")
    return exe


def run_tool(name, args):
    exe = tool(name)
    printable = [display(exe)] + [display_arg(a) for a in args]
    print("$ " + subprocess.list2cmdline(printable))
    sys.stdout.flush()
    p = subprocess.run([exe] + args, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    if p.stdout:
        print(p.stdout.rstrip("\n"))
    if p.stderr:
        print(p.stderr.rstrip("\n"))
    print(f"[link5703] {name} exit {p.returncode}")
    sys.stdout.flush()
    return p.returncode


def list_parts(container_path):
    """Return the list of 4-byte FourCC part codes in a DXIL container.

    Layout (include/dxc/DxilContainer/DxilContainer.h, #pragma pack(push, 1)):
      DxilContainerHeader { uint32 FourCC; uint8[16] Hash; uint16 VerMajor;
        uint16 VerMinor; uint32 ContainerSize; uint32 PartCount; }  (32 bytes)
      followed by uint32 PartOffset[PartCount]   (offset from container start)
      each offset points to DxilPartHeader { uint32 FourCC; uint32 PartSize; }
      followed by that many bytes of part data.
    """
    with open(container_path, "rb") as f:
        data = f.read()
    if len(data) < 32:
        return None, f"container too small ({len(data)} bytes)"
    header_fourcc = data[0:4]
    if header_fourcc != b"DXBC":
        return None, f"unexpected header FourCC {header_fourcc!r} (want DXBC)"
    (part_count,) = struct.unpack_from("<I", data, 28)
    offsets = struct.unpack_from(f"<{part_count}I", data, 32)
    parts = []
    for off in offsets:
        if off + 8 > len(data):
            return None, f"part offset {off} out of range"
        fourcc = data[off:off + 4]
        (size,) = struct.unpack_from("<I", data, off + 4)
        parts.append((fourcc.decode("ascii", "replace"), size))
    return parts, None


def report_rdat(label, container_path):
    parts, err = list_parts(container_path)
    if err:
        print(f"[link5703] {label}: PARSE-ERROR: {err}")
        print(f"{label}-RDAT: PARSE-ERROR")
        return
    names = ", ".join(f"{fourcc}({size})" for fourcc, size in parts)
    print(f"[link5703] {label} parts: {names}")
    has_rdat = any(fourcc == "RDAT" for fourcc, _ in parts)
    print(f"{label}-RDAT: {'PRESENT' if has_rdat else 'MISSING'}")


def emit_version():
    print("link5703 harness (dxc-lib / dxl-link / container-part-reader); "
          "tool directory " + display(LOCAL_BIN))
    dxc = os.path.join(LOCAL_BIN, "dxc.exe")
    if os.path.isfile(dxc):
        p = subprocess.run([dxc, "--version"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
        line = (p.stdout or p.stderr or "").strip().replace("\n", " ")
        print(f"dxc: {line}")
    else:
        print(f"dxc: MISSING at {display(dxc)}")
    dxl = os.path.join(LOCAL_BIN, "dxl.exe")
    print(f"dxl: {'present' if os.path.isfile(dxl) else 'MISSING'} at "
          f"{display(dxl)}")
    return 0


def parse_args(argv):
    entry = "main"
    lib_profile = None
    link_profile = None
    direct_profile = None
    extra = []
    source = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--entry":
            i += 1
            entry = argv[i]
        elif a == "--lib-profile":
            i += 1
            lib_profile = argv[i]
        elif a == "--link-profile":
            i += 1
            link_profile = argv[i]
        elif a == "--direct-profile":
            i += 1
            direct_profile = argv[i]
        elif a.lower().endswith(".hlsl"):
            source = a
        else:
            extra.append(a)
        i += 1
    if lib_profile is None or link_profile is None or source is None:
        sys.exit("link5703: need --lib-profile, --link-profile and a "
                  ".hlsl source in cmd.txt")
    return entry, lib_profile, link_profile, direct_profile, extra, source


def main(argv):
    if not argv or argv[0] in ("--version", "-version", "/version"):
        return emit_version()

    entry, lib_profile, link_profile, direct_profile, extra, source = \
        parse_args(argv)
    source = os.path.abspath(source)

    worst = 0
    # A directory under the issue folder, not the system temp dir: the
    # latter bakes the current Windows user's profile directory into every
    # printed path, which is exactly the machine-path leak
    # `scripts/check_paths.py` exists to catch. `work/` is listed in
    # .gitignore next to this file, same pattern as #4168's
    # `scratch-dxl-equiv/`.
    tmp = os.path.join(HERE, "work")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    try:
        lib_out = os.path.join(tmp, "lib5703.dxo")
        rc = run_tool("dxc", ["-T", lib_profile] + extra +
                      ["-Fo", lib_out, source])
        worst = worst or rc
        if rc == 0 and os.path.isfile(lib_out):
            report_rdat("unlinked-lib", lib_out)
        else:
            print("unlinked-lib-RDAT: NO-CONTAINER (compile failed)")

        linked_out = os.path.join(tmp, "linked5703.dxo")
        rc = run_tool("dxl", ["-T", link_profile, "-E", entry] + extra +
                      ["-Fo", linked_out, lib_out])
        worst = worst or rc
        if rc == 0 and os.path.isfile(linked_out):
            report_rdat("linked", linked_out)
        else:
            print("linked-RDAT: NO-CONTAINER (link failed)")

        if direct_profile:
            direct_out = os.path.join(tmp, "direct5703.dxo")
            rc = run_tool("dxc", ["-T", direct_profile, "-E", entry] +
                          extra + ["-Fo", direct_out, source])
            worst = worst or rc
            if rc == 0 and os.path.isfile(direct_out):
                report_rdat("direct", direct_out)
            else:
                print("direct-RDAT: NO-CONTAINER (compile failed)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
