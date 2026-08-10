#!/usr/bin/env python
"""#4168 harness: run a dxc/dxl/dxa chain as if it were one compiler.

The reported symptom is `D3D12_SHADER_BUFFER_DESC::Variables == 0` on a
*linked* shader. Reaching it needs three different executables -- `dxc` to build
the library, `dxl` to link it into a shader, and `dxa -dumpreflection` to walk
`ID3D12ShaderReflection` -- while `triage.py run` hands every `cmd.txt` line to
one registered executable. SKILL.md's answer is to make the harness look like a
compiler ("When the symptom is in a pass dxc.exe cannot run, register the
harness as a compiler"), so `run`, `--shader`, `--args`, `--expect` and
`reindex` all keep working.

Each command starts with the tool it means:

    dxc -T lib_6_x -Fo lib4168.dxo repro.hlsl
    dxl -T ps_6_0 -E main -Fo linked4168.dxo lib4168.dxo
    dxa -dumpreflection linked4168.dxo

A single argv may carry several commands separated by a bare `;`, which is what
lets a one-line `run --args` control express a whole chain.

`--release <tag>` runs the *producer* tools (dxc, dxl) from that catalogued
release instead of the local build, resolved through triage.py's own release
table so no machine path is written into a committed file. Two consequences,
both deliberate and both echoed into the capture:

* No stable release archive ships `dxl.exe` (see manual-case-release-tools.txt),
  so `dxl` runs as `dxc.exe -link`. That is exactly what `dxl.exe` is:
  tools/clang/tools/dxl/dxl.cpp is a `main` that appends `-link` to argv and
  calls `dxc::main`. `variant-dxl-equivalence-*.txt` measures the equivalence
  rather than assuming it.
* No release archive ships `dxa.exe` either, so the reflection *reader* is
  always the local build. The thing under test is the container the linker
  produced; holding the reader fixed while varying the producer is the #3535
  pattern and is what isolates it. A per-release control (the same source
  compiled straight to the shader profile) proves the fixed reader can read
  that release's containers at all.

Every command is echoed with `subprocess.list2cmdline`, with the executable
path shown, so the capture records what actually ran rather than a
transcription of it. Paths are printed relative to `<repo>`/`<skill>` so no
machine layout lands in committed evidence.
"""

import json
import os
import subprocess
import sys

TOOLS = ("dxc", "dxl", "dxa")
PRODUCERS = ("dxc", "dxl")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TRIAGE = os.path.join(SKILL, "scripts", "triage.py")
LOCAL_BIN = os.environ.get("DXC_LINK4168_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")


def display(path):
    """Machine-independent spelling of a path, for committed captures."""
    full = os.path.abspath(path)
    for root, name in ((SKILL, "<skill>"), (REPO, "<repo>")):
        if full.lower().startswith(root.lower() + os.sep):
            return name + full[len(root):].replace("\\", "/")
    return full


def release_bin(tag):
    """Directory of a catalogued release's dxc.exe, from the release table."""
    query = ("SELECT tag, cached_path FROM releases WHERE cached_path"
             " IS NOT NULL")
    p = subprocess.run([sys.executable, TRIAGE, "sql", query],
                       capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"link4168: could not query the release table:\n{p.stderr}")
    for row in json.loads(p.stdout):
        if row["tag"] == tag:
            return os.path.dirname(row["cached_path"])
    sys.exit(f"link4168: release {tag} is not cached locally; "
             f"run `triage.py catalog` / a bisect that downloads it first")


def resolve(tool, rel_bin):
    """Return (argv-prefix, note) for one tool under the selected build."""
    if rel_bin and tool in PRODUCERS:
        exe = os.path.join(rel_bin, tool + ".exe")
        if os.path.isfile(exe):
            return [exe], ""
        if tool == "dxl":
            # dxl.exe is dxc.exe plus a trailing -link
            # (tools/clang/tools/dxl/dxl.cpp).
            dxc = os.path.join(rel_bin, "dxc.exe")
            if os.path.isfile(dxc):
                return [dxc], "release ships no dxl.exe; using dxc.exe -link"
        sys.exit(f"link4168: {tool} is missing from {display(rel_bin)}")
    exe = os.path.join(LOCAL_BIN, tool + ".exe")
    if not os.path.isfile(exe):
        sys.exit(f"link4168: {display(exe)} does not exist")
    note = ""
    if rel_bin and tool not in PRODUCERS:
        note = "reader held fixed at the local build (no dxa.exe in releases)"
    return [exe], note


def emit_version():
    print("link4168 harness (dxc/dxl/dxa chain runner); "
          "tool directory " + display(LOCAL_BIN))
    for name in TOOLS:
        exe = os.path.join(LOCAL_BIN, name + ".exe")
        if not os.path.isfile(exe):
            print(f"{name}: MISSING at {display(exe)}")
            continue
        if name == "dxa":
            # dxa has no --version, and its "unknown argument" diagnostic
            # quotes its own absolute path -- which would then be stored in the
            # compiler registry and in every capture header.
            print(f"{name}: (no --version option) at {display(exe)}")
            continue
        p = subprocess.run([exe, "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        line = (p.stdout or p.stderr or "").strip().replace("\n", " ")
        print(f"{name}: {line}")
    return 0


def split_commands(argv):
    groups, current = [], []
    for tok in argv:
        if tok == ";":
            if current:
                groups.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        groups.append(current)
    return groups


def main(argv):
    if not argv or argv[0] in ("--version", "-version", "/version"):
        return emit_version()

    rel_bin, tag = None, None
    if argv[0] == "--release":
        if len(argv) < 2:
            sys.exit("link4168: --release needs a release tag")
        tag = argv[1]
        rel_bin = release_bin(tag)
        argv = argv[2:]
        print(f"[link4168] producers (dxc, dxl) from release {tag}: "
              f"{display(rel_bin)}")

    worst = 0
    for group in split_commands(argv):
        tool = group[0]
        if tool not in TOOLS:
            print(f"link4168: the first token of a command must be one of "
                  f"{'/'.join(TOOLS)}, got {tool!r}", file=sys.stderr)
            return 2
        prefix, note = resolve(tool, rel_bin)
        rest = list(group[1:])
        if tool == "dxl" and os.path.basename(prefix[0]).lower() == "dxc.exe":
            rest.append("-link")
        print("$ " + subprocess.list2cmdline(
            [display(prefix[0])] + rest)
            + (f"   # {note}" if note else ""))
        sys.stdout.flush()
        rc = subprocess.run(prefix + rest).returncode
        print(f"[link4168] {tool} exit {rc}")
        sys.stdout.flush()
        if rc != 0 and worst == 0:
            worst = rc
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
