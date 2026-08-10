"""#4273 -- does the retained `cbuffer` block actually cost anything downstream?

The reporter's stated harm is register-slot pressure:

    "If the unused cbuffer remains. It wasted register slot of cbuffer when
     compiled shader. Too many unused cbuffer remains overflow the limit of
     cbuffer slot(15 in dx11)."

and their stated use of the rewriter output is "I used the result code generate
reflect infomation and compile". Both are checkable, so check them rather than
assuming either way.

This script regenerates `rewritten.hlsl` (byte-identical to what dxr prints for
the repro -- it is the rewriter's own output, not an edited copy), compiles it
with the ground-truth dxc for vs_6_0, and reads back the DXIL resource-binding
table and the D3D12 reflection.

SCOPE. This measures the DXC/SM6 path only. DX11 shaders are compiled by FXC
for SM5.x, which is a different compiler and is not tested here; nothing below
is evidence about it.

    python downstream.py     # writes manual-case-downstream-cost.txt
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
DXR = os.path.join(BUILD_BIN, "dxr.exe")
DXC = os.path.join(BUILD_BIN, "dxc.exe")
DXA = os.path.join(BUILD_BIN, "dxa.exe")

REWRITE_ARGS = ["-E", "vsMain", "-remove-unused-globals",
                "-remove-unused-functions", "-extract-entry-uniforms",
                "repro.hlsl"]


def redact(path):
    """Absolute path -> the placeholders triage.py writes in capture headers."""
    p = os.path.abspath(path).replace(os.sep, "/")
    for base, token in ((os.path.join(SKILL, ".cache"), "<cache>"),
                        (SKILL, "<triage>"), (REPO, "<repo>")):
        b = os.path.abspath(base).replace(os.sep, "/")
        if p.lower() == b.lower():
            return token
        if p.lower().startswith(b.lower() + "/"):
            return token + p[len(b):]
    return p


def run(argv, stdout_to=None):
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    text = p.stdout + p.stderr
    if stdout_to:
        with open(os.path.join(HERE, stdout_to), "w", newline="\n") as f:
            f.write(p.stdout)
    # echoed from the argv that actually ran, not transcribed
    return {"cmd": redact(argv[0]) + " " + subprocess.list2cmdline(
        [redact(x) if os.path.isabs(x) else x for x in argv[1:]]),
        "exit": p.returncode, "stdout": p.stdout, "output": text}


def main():
    for exe in (DXR, DXC, DXA):
        if not os.path.isfile(exe):
            sys.exit(f"missing {redact(exe)}; set DXC_BUILD_BIN")

    # the container is a binary, so it goes to the gitignored scratch tree
    scratch = os.path.join(SKILL, ".cache", "rw4273")
    os.makedirs(scratch, exist_ok=True)
    dxo = os.path.join(scratch, "rewritten.dxo")

    steps = {}
    # 1. rewriter output, verbatim, straight to rewritten.hlsl
    steps["rewrite"] = run([DXR, *REWRITE_ARGS], stdout_to="rewritten.hlsl")
    # 2. compile it and emit the DXIL listing
    steps["compile"] = run([DXC, "-T", "vs_6_0", "-E", "vsMain",
                            "rewritten.hlsl", "-Fc", "rewritten.dxil.txt"])
    # 3. compile to a container and dump D3D12 reflection
    steps["container"] = run([DXC, "-T", "vs_6_0", "-E", "vsMain",
                              "rewritten.hlsl", "-Qstrip_debug", "-Fo", dxo])
    steps["reflect"] = run([DXA, "-dumpreflection", dxo])

    listing = ""
    lp = os.path.join(HERE, "rewritten.dxil.txt")
    if os.path.isfile(lp):
        with open(lp, errors="replace") as f:
            listing = f.read()

    # Read the binding table rows out of the DXIL listing comment block. The
    # parser announces its own failure rather than returning an empty list that
    # would read as "no bindings" (#2923's broken-reader trap).
    bind = []
    m = re.search(r"^; Resource Bindings:\n(?:^;.*\n)+", listing, re.M)
    if m:
        for line in m.group(0).splitlines():
            row = re.match(r"^;\s+(\S+)\s+(cbuffer|texture|sampler|UAV|SRV)\s",
                           line)
            if row:
                bind.append((row.group(1), row.group(2)))
    parse_warn = None
    if not bind:
        parse_warn = ("PARSE-WARNING: no Resource Bindings rows were parsed "
                      "out of the DXIL listing -- treat the table below as "
                      "unread, not as empty")

    refl = steps["reflect"]["stdout"]
    cb_count = re.search(r"ConstantBuffers:\s*(\d+)", refl)
    cb_names = re.findall(r"D3D12_SHADER_BUFFER_DESC: Name: (\S+)", refl)
    if not cb_count:
        parse_warn = (parse_warn or "") + (
            " PARSE-WARNING: no ConstantBuffers count found in the reflection "
            "dump")

    out = [
        "#4273 -- what does the retained `cbuffer cbB` cost downstream?",
        "",
        "Produced by `python downstream.py`. rewritten.hlsl in this directory",
        "is step 1's stdout verbatim -- the rewriter's own output, not an",
        "edited copy.",
        "",
        "SCOPE: the DXC/SM6 path only. DX11 shaders are built by FXC for",
        "SM5.x, a different compiler, which is NOT tested here.",
        "",
        "STEPS", "",
    ]
    for name in ("rewrite", "compile", "container", "reflect"):
        out.append(f"  {name:<10} exit {steps[name]['exit']}   "
                   f"{steps[name]['cmd']}")
    out += ["", "REWRITER OUTPUT (rewritten.hlsl) -- `cbuffer cbB` is present:",
            ""]
    out += ["  " + ln for ln in steps["rewrite"]["stdout"].rstrip().splitlines()]

    out += ["", "", "DXIL RESOURCE BINDINGS of the compiled result:", ""]
    if parse_warn:
        out += ["  " + parse_warn, ""]
    for name, kind in bind:
        out.append(f"  {name:<12} {kind}")
    out += ["", "  cbuffer rows found: "
            + (", ".join(n for n, k in bind if k == "cbuffer") or "(none)"), ""]

    out += ["", "D3D12 REFLECTION of the compiled result:", "",
            f"  ConstantBuffers: {cb_count.group(1) if cb_count else '(unread)'}",
            "  D3D12_SHADER_BUFFER_DESC names: "
            + (", ".join(cb_names) or "(none)"), ""]

    out += ["", "VERBATIM -- the DXIL listing's resource block and the",
            "reflection dump's constant-buffer section.", ""]
    if m:
        out += [m.group(0).rstrip(), ""]
    keep = [ln for ln in refl.splitlines()
            if re.search(r"ConstantBuffers:|BoundResources:|"
                         r"D3D12_SHADER_BUFFER_DESC|D3D12_SHADER_VARIABLE_DESC"
                         r"|D3D12_SHADER_INPUT_BIND_DESC", ln)]
    out += keep + [""]

    with open(os.path.join(HERE, "downstream.json"), "w") as f:
        json.dump({"steps": {k: {kk: vv for kk, vv in v.items()
                                 if kk != "stdout"}
                             for k, v in steps.items()},
                   "bindings": bind, "reflection_cb_names": cb_names,
                   "reflection_cb_count":
                       cb_count.group(1) if cb_count else None}, f, indent=2)
    path = os.path.join(HERE, "manual-case-downstream-cost.txt")
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("bindings:", bind)
    print("reflection constant buffers:", cb_names)
    if parse_warn:
        print(parse_warn)
    print("wrote", redact(path))
    return 1 if parse_warn else 0


if __name__ == "__main__":
    sys.exit(main())
