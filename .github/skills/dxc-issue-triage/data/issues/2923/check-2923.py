"""Report the PIX virtual-register annotation of a module for issue #2923.

Input: the textual LLVM IR produced by

    dxc -Zi -Qembed_debug ... -Fo x.dxo
    dxa -extractpart=dbgmodule -o=x.ll x.dxo
    dxopt -o=x.bc x.ll -opt-mod-passes \
          -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
    opt -S -o=x.annotated.ll x.bc

which is the same pass pipeline PixTest.cpp's RunAnnotationPasses uses.

What it prints, and why those things:

* Every alloca that carries !pix-alloca-reg, with its (base, count) virtual
  register range, the llvm.dbg.declare(s) that describe it, and every
  !pix-alloca-reg-write recorded against it.
* Per source variable, the registers its debug info claims and the registers
  that were actually written.
* An emulation of the assertions PixTest.cpp's TestStructAnnotationCase makes.
  PixTest gathers `AllocaWrites` only from stores whose alloca has exactly one
  llvm.dbg.* user (FindStructMemberFromStore, PixTest.cpp:1090), so that gate
  is applied here too. Member *names* are not emulated: they need the DWARF
  member walk, which is out of scope for a text reader.
* A single machine-readable symptom line, consumed by match.json:
      PIX-2923: DECLARED-BUT-UNWRITTEN <n> register(s) ...
      PIX-2923: ALL-DECLARED-REGISTERS-WRITTEN
"""

import re
import sys

MD_RE = re.compile(r"^(![0-9]+) = (?:distinct )?!\{(.*)\}\s*$")
ALLOCA_RE = re.compile(
    r"^\s*(%[-\w.]+) = alloca (.+?), !pix-alloca-reg (![0-9]+)")
# The pointer type can contain spaces ("[1 x float]*"), so it cannot be \S+.
DECLARE_RE = re.compile(
    r"llvm\.dbg\.declare\(metadata (.+?) (%[-\w.]+), metadata (![0-9]+), "
    r"metadata (![0-9]+)\)")
VARNAME_RE = re.compile(r'; var:"([^"]*)"\s*(!DIExpression\([^)]*\))?')
WRITE_RE = re.compile(r"!pix-alloca-reg-write (![0-9]+)")
# Two different source variables can both be called "p" -- main's local and the
# inlined subroutine's parameter -- and telling them apart is the whole point,
# so resolve the DILocalVariable rather than trusting the name.
DILOCAL_RE = re.compile(
    r"^(![0-9]+) = !DILocalVariable\((.*)\)\s*$")


def parse(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    md = {}
    dilocal = {}
    for ln in lines:
        m = MD_RE.match(ln)
        if m:
            md[m.group(1)] = [x.strip() for x in m.group(2).split(",")]
        m = DILOCAL_RE.match(ln)
        if m:
            body = m.group(2)
            tag = re.search(r"tag:\s*(\w+)", body)
            line = re.search(r"\bline:\s*(\d+)", body)
            dilocal[m.group(1)] = (
                (tag.group(1) if tag else "?")
                + (f" src-line {line.group(1)}" if line else ""))

    def ints(node):
        out = []
        for op in md.get(node, []):
            m = re.match(r"^i32 (-?\d+)$", op)
            out.append(int(m.group(1)) if m else None)
        return out

    allocas = {}          # ssa name -> dict
    order = []
    for ln in lines:
        m = ALLOCA_RE.match(ln)
        if m:
            name, ty, node = m.group(1), m.group(2).strip(), m.group(3)
            ty = ty.split(",")[0].strip()
            v = ints(node)
            # !pix-alloca-reg = !{i32 1, i32 <base>, i32 <count>}
            if len(v) != 3 or v[0] != 1:
                continue
            allocas[name] = {"type": ty, "node": node, "base": v[1],
                             "count": v[2], "declares": [], "writes": []}
            order.append(name)

    node_to_alloca = {a["node"]: n for n, a in allocas.items()}

    for ln in lines:
        m = DECLARE_RE.search(ln)
        if m and m.group(2) in allocas:
            vm = VARNAME_RE.search(ln)
            allocas[m.group(2)]["declares"].append({
                "var_md": m.group(3),
                "name": vm.group(1) if vm else "?",
                "kind": dilocal.get(m.group(3), "?"),
                "expr": (vm.group(2) if vm and vm.group(2) else "!DIExpression()"),
            })
        m = WRITE_RE.search(ln)
        if m:
            v = md.get(m.group(1), [])
            # !pix-alloca-reg-write = !{i32 2, <alloca-reg-node>, i32 kind, i32 index}
            if len(v) != 4:
                continue
            target = v[1]
            idx = re.match(r"^i32 (-?\d+)$", v[3])
            if target in node_to_alloca and idx:
                allocas[node_to_alloca[target]]["writes"].append(
                    (int(idx.group(1)), ln.strip()))

    return order, allocas, sum(
        1 for ln in lines if "call void @llvm.dbg.declare(" in ln)


def main(argv):
    if len(argv) < 2:
        print("usage: check-2923.py <annotated.ll> [-Od|-O1]", file=sys.stderr)
        return 2
    path = argv[1]
    opt = argv[2] if len(argv) > 2 else "-Od"

    order, allocas, declare_sites = parse(path)

    print(f"=== PIX virtual-register report: {path} ({opt}) ===")
    attributed = sum(len(allocas[n]["declares"]) for n in order)
    print(f"llvm.dbg.declare call sites: {declare_sites}, "
          f"attributed to an annotated alloca: {attributed}")
    if declare_sites != attributed:
        # Self-guard: an unattributed declare means this reader failed to parse
        # something, and every conclusion below would be silently wrong.
        print(f"PIX-2923: PARSE-WARNING {declare_sites - attributed} "
              f"dbg.declare(s) not attributed -- results are unreliable")
    print(f"allocas carrying !pix-alloca-reg: {len(order)}")
    for n in order:
        a = allocas[n]
        regs = f"{a['base']}..{a['base'] + a['count'] - 1}" \
            if a["count"] > 1 else f"{a['base']}"
        decl = "; ".join(f"{d['name']} [{d['kind']}] {d['expr']}"
                         for d in a["declares"]) or "(no dbg.declare)"
        wr = ",".join(str(a["base"] + i) for i, _ in sorted(a["writes"])) \
            or "(none)"
        print(f"  {n:<6} {a['type']:<28} regs[{regs}] "
              f"base={a['base']} count={a['count']}")
        print(f"         declares: {decl}")
        print(f"         writes  -> registers: {wr}")

    # Group by the DILocalVariable metadata node: two variables can share the
    # name "p" (caller's local and the inlined callee's parameter) and they are
    # different variables.
    groups = {}
    for n in order:
        for d in allocas[n]["declares"]:
            groups.setdefault((d["var_md"], d["name"], d["kind"]),
                              []).append(n)

    print()
    print("source variables described by alloca registers:")
    unwritten_total = []
    for (var_md, name, kind), names in sorted(groups.items()):
        declared, written = [], []
        for n in names:
            a = allocas[n]
            declared += list(range(a["base"], a["base"] + a["count"]))
            written += [a["base"] + i for i, _ in a["writes"]]
        missing = sorted(set(declared) - set(written))
        print(f'  var {var_md} "{name}" [{kind}]: {len(names)} alloca '
              f"range(s), declared registers {sorted(set(declared))}, "
              f"written registers {sorted(set(written))}")
        if missing:
            print(f"         registers declared but NEVER written: {missing}")
            unwritten_total += [(var_md, name, kind, missing)]

    # PixTest.cpp emulation.
    print()
    print("PixTest.cpp TestStructAnnotationCase emulation:")
    offset_and_sizes = [n for n in order if allocas[n]["declares"]]
    alloca_writes = []
    for n in order:
        a = allocas[n]
        if len(a["declares"]) != 1:
            continue  # FindStructMemberFromStore requires exactly one dbg user
        for i, _ in sorted(a["writes"]):
            alloca_writes.append((a["base"], i))
    exp_oas = 6 if opt == "-O1" else 1
    print(f"  OffsetAndSizes.size() : expected {exp_oas:<3} actual "
          f"{len(offset_and_sizes):<3} "
          f"{'ok' if len(offset_and_sizes) == exp_oas else 'FAIL'}")
    print(f"  AllocaWrites.size()   : expected 6   actual "
          f"{len(alloca_writes):<3} "
          f"{'ok' if len(alloca_writes) == 6 else 'FAIL'}")
    for i, (base, idx) in enumerate(alloca_writes):
        print(f"  ValidateAllocaWrite({i}): expected regBase+index == {i}, "
              f"actual {base}+{idx} == {base + idx} "
              f"{'ok' if base + idx == i else 'FAIL'}")

    print()
    if unwritten_total:
        n = sum(len(m) for _, _, _, m in unwritten_total)
        which = "; ".join(f'{v} "{nm}" [{k}] {m}'
                          for v, nm, k, m in unwritten_total)
        print(f"PIX-2923: DECLARED-BUT-UNWRITTEN {n} register(s) -- {which}")
    else:
        print("PIX-2923: ALL-DECLARED-REGISTERS-WRITTEN")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
