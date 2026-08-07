"""Probe #3693's three source forms on Compiler Explorer and capture the results.

Writes manual-case-compiler-explorer.txt. Each cell records the CE compiler id, the exact
arguments, the exit code, every diagnostic line, and -- for a compile that succeeded --
the generated instruction that consumed the out-of-bounds element.

A pane is only evidence if the compiler can run the source, and silence is only evidence
if the compiler would have spoken had there been something to say. Hence the matrix: the
swizzle form is the control that makes each compiler prove it is looking.

Usage: python ce-probe.py
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CE = "https://godbolt.org"
FILTERS = {"execute": False, "intel": False, "demangle": False, "labels": False,
           "directives": False, "commentOnly": False, "trim": False, "binary": False}

SOURCES = [
    ("case-compute.hlsl",
     "g_vertices[indices[3]] -- the reporter's shape: out-of-bounds subscript as the "
     "index operand of another subscript"),
    ("case-compute-hoisted.hlsl",
     "uint oob = indices[3]; -- the same access in a plain local initializer"),
    ("case-compute-swizzle.hlsl",
     "indices.w -- CONTROL: the swizzle spelling of the same out-of-bounds element"),
]

COMPILERS = [
    ("fxc_10_0_19041", "/T cs_5_0 /E main /Od"),
    ("dxc_1_6_2112", "-T cs_6_0 -E main -Od"),
    ("dxc_trunk", "-T cs_6_0 -E main -Od"),
    ("hlsl_clang_trunk", "-T cs_6_0 -E main"),
]


def compile_one(source, compiler, args):
    req = urllib.request.Request(
        f"{CE}/api/compiler/{compiler}/compile",
        data=json.dumps({
            "source": source, "lang": "hlsl", "compiler": compiler,
            "options": {"userArguments": args,
                        "compilerOptions": {"skipAsm": False, "executorRequest": False},
                        "filters": dict(FILTERS), "tools": [], "libraries": []},
            "allowStoreCodeDebug": True,
        }).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.loads(r.read().decode())
    text = "\n".join(x.get("text", "") for stream in ("stdout", "stderr")
                     for x in res.get(stream, []))
    asm = "\n".join(x.get("text", "") for x in res.get("asm", [])
                    if isinstance(x, dict))
    return res.get("code"), text, asm


def main():
    out = ["# Compiler Explorer results for #3693, probed via the CE compile API.",
           "# CE runs Linux Release builds; it corroborates the local Debug build,"
           " never overrules it.",
           "# Written by ce-probe.py -- rerun it to re-derive this file.", ""]
    for name, descr in SOURCES:
        with open(os.path.join(HERE, name)) as f:
            source = f.read()
        out.append("#" * 78)
        out.append("# SOURCE %s" % name)
        out.append("#   %s" % descr)
        out.append("")
        for cid, args in COMPILERS:
            rc, text, asm = compile_one(source, cid, args)
            out.append("=" * 78)
            out.append("# compiler: %s" % cid)
            out.append("# args: %s" % args)
            out.append("# exit: %s" % rc)
            diags = [ln for ln in text.splitlines()
                     if ln.strip() and "Copyright" not in ln
                     and "Direct3D Shader Compiler" not in ln]
            if diags:
                out.extend("  | " + ln for ln in diags[:8])
            else:
                out.append("  | <no diagnostic>")
            interesting = [ln.strip() for ln in asm.splitlines()
                           if "undef" in ln and "ufferLoad" in ln]
            interesting += [ln.strip() for ln in asm.splitlines()
                            if "poison" in ln][:3]
            for ln in interesting[:4]:
                out.append("  A " + ln)
            out.append("  # asm lines: %d" % len(asm.splitlines()))
            out.append("")
    path = os.path.join(HERE, "manual-case-compiler-explorer.txt")
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(out))
    print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
