#!/usr/bin/env python3
"""Derive the per-layer, per-release table for #3726 from the committed captures.

Reads only `out-<tag>.txt` in this directory -- it runs no compiler, so it cannot
disagree with the evidence. Every capture holds three dxc invocations (DXIL, SPIR-V,
-fcgl) of repro.hlsl, and the question this issue asks is *which of them says
anything*, which is not something a single symptom predicate can express.

Paths are derived from __file__, so a stranger can run this straight from a clone:

    python make-layer-history.py > manual-case-layer-history.txt
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

RESMAP = "local resource not guaranteed to map to unique global resource"
ORDER = [
    "v1.4.1907", "v1.5.2010", "v1.6.2104", "v1.6.2106", "v1.6.2112",
    "v1.7.2207", "v1.7.2212", "v1.7.2212.1", "v1.7.2308",
    "v1.8.2403", "v1.8.2403.1", "v1.8.2403.2", "v1.8.2405", "v1.8.2407",
    "v1.8.2502", "v1.8.2505", "v1.8.2505.1",
    "v1.9.2602", "v1.9.2602.24", "v1.9.2607", "main-debug",
]


def blocks(path):
    """Split one capture into its dxc invocations: [(argv, exit, body), ...]."""
    text = open(path, encoding="utf-8", errors="replace").read()
    parts = re.split(r"^\$ dxc ", text, flags=re.M)[1:]
    out = []
    for p in parts:
        argv, _, rest = p.partition("\n")
        m = re.search(r"^\[exit\] (\S+)", rest, re.M)
        out.append((argv.strip(), m.group(1) if m else "?", rest))
    return out


def spirv_shape(body):
    """What the emitted SPIR-V actually binds, in one token."""
    if "SPIR-V CodeGen not available" in body:
        return "no-spirv-codegen"
    names = set(re.findall(r"^\s*%(r[012]|x[012]) = OpVariable", body, re.M))
    if not names:
        return "no resource OpVariable at all" + \
               (" (+OpUndef)" if "OpUndef" in body else "")
    tag = "+".join(sorted(names))
    return tag + (" (+OpUndef)" if "OpUndef" in body else "")


def main():
    print("# #3726 -- which layer diagnoses `a0 = r0;`, per release")
    print("#")
    print("# Derived from the committed out-<tag>.txt captures by make-layer-history.py;")
    print("# no compiler is run here. Each capture's three invocations are cmd.txt's:")
    print("#   1. -T ps_6_0 -E main repro.hlsl              (DXIL)")
    print("#   2. -T ps_6_0 -E main -spirv repro.hlsl       (SPIR-V)")
    print("#   3. -T ps_6_0 -E main -fcgl repro.hlsl        (front end only)")
    print("#")
    print("# 0x80004005 is E_FAIL, which is what dxc returns for an ordinary diagnosed")
    print("# error on Windows -- not an internal failure.")
    print()
    hdr = (f"{'release':<14} {'DXIL exit':>10}  {'resmap err':<10} "
           f"{'SPIRV exit':>10}  {'SPIR-V binds':<28} {'-fcgl exit':>10}  fcgl diags")
    print(hdr)
    print("-" * len(hdr))
    missing = []
    for tag in ORDER:
        path = os.path.join(HERE, f"out-{tag}.txt")
        if not os.path.isfile(path):
            missing.append(tag)
            continue
        bs = blocks(path)
        by = {}
        for argv, rc, body in bs:
            key = "spirv" if "-spirv" in argv else \
                  "fcgl" if "-fcgl" in argv else "dxil"
            by[key] = (rc, body)
        if len(by) != 3:
            print(f"{tag:<14}  PARSE-WARNING: {len(by)} of 3 invocations found")
            continue

        def hexrc(rc):
            try:
                return "0x%08X" % (int(rc) & 0xFFFFFFFF)
            except ValueError:
                return rc

        drc, dbody = by["dxil"]
        src, sbody = by["spirv"]
        frc, fbody = by["fcgl"]
        resmap = "yes" if RESMAP in dbody else "NO"
        fdiag = "yes" if re.search(r"^.*error: ", fbody, re.M) else "none"
        print(f"{tag:<14} {hexrc(drc):>10}  {resmap:<10} {hexrc(src):>10}  "
              f"{spirv_shape(sbody):<28} {hexrc(frc):>10}  {fdiag}")

    if missing:
        print()
        print("PARSE-WARNING: no capture on disk for: " + ", ".join(missing))
    print()
    print("Reading of the table:")
    print("  * `resmap err` is yes on every release: the DXIL back end has always")
    print("    rejected this, and match.json scores every release `repro`.")
    print("  * `-fcgl exit` is 0 with no diagnostics on every release: the front end")
    print("    has never had anything to say, which is the issue's actual complaint.")
    print("  * `SPIR-V binds` is x0+x1+x2 wherever SPIR-V exists: the module is built")
    print("    from the resources that were assigned INTO, not the ones assigned FROM,")
    print("    so r0/r1/r2 never appear. This records the lowering shape; because the")
    print("    issue asks for this source to be rejected, it is not evidence of a miscompile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
