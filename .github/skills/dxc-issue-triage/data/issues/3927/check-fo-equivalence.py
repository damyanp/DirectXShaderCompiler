"""#3927: prove that dropping `-Fo` from the reporter's command line changes nothing.

cmd.txt runs `-T ps_6_0 -spirv repro.hlsl`; the issue was filed as
`-T ps_6_0 -spirv test.hlsl -Fo test.spv` followed by `spirv-dis test.spv`. `-Fo` only
selects the output sink, but that is an assertion until it is measured, and this repository
has no `spirv-dis` binary to compare against -- so this script parses the `.spv` module
itself and checks the two agree on the thing the predicate reads: the id->name table and the
Binding / DescriptorSet decorations.

Writes manual-case-fo-equivalence.txt. Run from this directory:

    python check-fo-equivalence.py > manual-case-fo-equivalence.txt

No absolute path is baked in: the compiler is taken from the triage registry (or $DXC), and
every path printed is rewritten to <repo>, derived from this script's own location.
"""
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/3927/ -> six levels to <repo>
REPO_ROOT = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
SKILL = os.path.join(REPO_ROOT, ".github", "skills", "dxc-issue-triage")

SPV_OP_NAME = 5
SPV_OP_DECORATE = 71
DECORATION = {33: "Binding", 34: "DescriptorSet"}


def redact(text):
    for root, tag in ((SKILL, "<skill>"), (REPO_ROOT, "<repo>")):
        for sep in ("\\", "/"):
            text = text.replace(root.replace("\\", sep), tag)
    return text


def find_dxc():
    if os.environ.get("DXC"):
        return os.environ["DXC"]
    reg = os.path.join(SKILL, ".cache", "compilers", "main-debug.json")
    with open(reg, encoding="utf-8") as f:
        return json.load(f)["exe_path"]


def run(argv):
    print("$ " + redact(subprocess.list2cmdline(argv)))
    p = subprocess.run(argv, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=HERE)
    print(f"[exit] {p.returncode}")
    if p.stderr.strip():
        print("[stderr] " + redact(p.stderr.strip()))
    return p


def parse_spv(path):
    """Return (bound, {id: name}, [(id, decoration, operand)]) from a SPIR-V binary."""
    with open(path, "rb") as f:
        blob = f.read()
    magic, = struct.unpack_from("<I", blob, 0)
    if magic != 0x07230203:
        sys.exit(f"not a SPIR-V module: magic {magic:#x}")
    bound, = struct.unpack_from("<I", blob, 12)
    words = struct.unpack_from(f"<{len(blob) // 4}I", blob, 0)
    names, decos, i = {}, [], 5
    while i < len(words):
        count, op = words[i] >> 16, words[i] & 0xFFFF
        if count == 0:
            break
        ops = words[i + 1:i + count]
        if op == SPV_OP_NAME:
            raw = b"".join(struct.pack("<I", w) for w in ops[1:])
            names[ops[0]] = raw.split(b"\0")[0].decode("utf-8")
        elif op == SPV_OP_DECORATE and len(ops) >= 3 and ops[1] in DECORATION:
            decos.append((ops[0], DECORATION[ops[1]], ops[2]))
        i += count
    return bound, names, decos


def main():
    dxc = find_dxc()
    print("#3927 -- is `-Fo test.spv` (as filed) equivalent to no `-Fo` (cmd.txt)?")
    print("# compiler: main-debug")
    print(f"# exe: {redact(dxc)}")
    print()

    spv = os.path.join(HERE, "fo-equivalence.spv")
    print("--- as filed: binary out via -Fo, then parsed by this script ---")
    run([dxc, "-T", "ps_6_0", "-spirv", "repro.hlsl", "-Fo", "fo-equivalence.spv"])
    bound, names, decos = parse_spv(spv)
    binary = [f"{names.get(i, '%' + str(i))} {d} {v}"
              for i, d, v in sorted(decos, key=lambda t: (t[0], t[1]))]
    print(f"[bound] {bound}")
    for line in binary:
        print(f"[binary] {line}")
    print()

    print("--- cmd.txt: disassembly on stdout ---")
    p = run([dxc, "-T", "ps_6_0", "-spirv", "repro.hlsl"])
    text = [ln.strip() for ln in p.stdout.splitlines()]
    dis_bound = next((ln.split(":")[1].strip() for ln in text
                      if ln.startswith("; Bound:")), None)
    dis = sorted(ln[len("OpDecorate "):].replace("%", "")
                 for ln in text
                 if ln.startswith("OpDecorate")
                 and (" Binding " in ln or " DescriptorSet " in ln))
    print(f"[bound] {dis_bound}")
    for line in dis:
        print(f"[stdout] {line}")
    print()

    ok = (str(bound) == str(dis_bound)) and sorted(binary) == dis
    print(f"[bound match] {str(bound) == str(dis_bound)}")
    print(f"[decoration match] {sorted(binary) == dis}")
    print(f"[RESULT] {'equivalent' if ok else 'NOT EQUIVALENT'}"
          " -- dropping -Fo changes only where the module is written")
    os.remove(spv)
    print("[cleanup] removed fo-equivalence.spv")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
