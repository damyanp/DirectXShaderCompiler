"""Probes Compiler Explorer's HLSL Clang build for issue 3429, with a control.

SKILL.md: "A Clang error is not evidence until you have a control." Clang's DXIL backend is
incomplete, so it fails on inputs that have nothing to do with the issue. This script
compiles BOTH the repro and a trivial groupshared compute shader with identical flags, so a
difference between them can be attributed to the repro rather than to the stage or backend.

Writes manual-case-clang-probe.txt. Every request is echoed, including the exact source sent.

Usage (from this directory):
    python make-clang-probe.py
"""

import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "manual-case-clang-probe.txt")
API = "https://godbolt.org/api/compiler/%s/compile"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

CONTROL = """groupshared float trivial[6];

[numthreads(8, 1, 1)]
void main(uint gi : SV_GroupIndex) {
  trivial[gi] = 1.0;
}
"""


def compile_on_ce(compiler, source, args):
    body = json.dumps({
        "source": source,
        "options": {
            "userArguments": args,
            "filters": {"execute": False, "intel": False, "demangle": True,
                        "labels": True, "libraryCode": True, "directives": True,
                        "commentOnly": False, "trim": False},
            "compilerOptions": {},
        },
        "lang": "hlsl",
        "allowStoreCodeDebug": True,
    }).encode()
    req = urllib.request.Request(API % compiler, data=body,
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def text_of(result, key):
    return ANSI.sub("", "\n".join(x.get("text", "") for x in result.get(key, []) or []))


def main():
    repro = open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8").read()
    args = "-T cs_6_0 -E main"
    cases = [
        ("repro.hlsl", repro, "hlsl_clang_trunk", args),
        ("control (trivial groupshared compute shader)", CONTROL, "hlsl_clang_trunk", args),
        ("repro.hlsl", repro, "hlsl_clang_trunk", args + " -fsyntax-only"),
        ("control (trivial groupshared compute shader)", CONTROL, "hlsl_clang_trunk",
         args + " -fsyntax-only"),
    ]
    lines = [
        "# issue: 3429",
        "# what: does CE's HLSL Clang say anything useful about this repro?",
        "# generator: make-clang-probe.py (committed next to its output)",
        "# note: each repro request is paired with a CONTROL -- a trivial groupshared compute",
        "#       shader under identical flags. A Clang failure that the control shares is a",
        "#       statement about Clang's DXIL backend, not about issue 3429.",
        "",
    ]
    for label, src, compiler, argstr in cases:
        res = compile_on_ce(compiler, src, argstr)
        lines.append("=" * 74)
        lines.append("# compiler: %s" % compiler)
        lines.append("# args:     %s" % argstr)
        lines.append("# source:   %s" % label)
        lines.append("# exit:     %s" % res.get("code"))
        lines.append("--- stderr ---")
        lines.append(text_of(res, "stderr").rstrip())
        lines.append("--- stdout ---")
        lines.append(text_of(res, "stdout").rstrip())
        asm = ANSI.sub("", "\n".join(x.get("text", "") for x in res.get("asm", []) or []))
        # Self-consistency: the whole point of this probe is whether Clang forms a merge of
        # groupshared pointers the way DXC does. Say loudly when the search finds nothing,
        # so "no merge here" and "no output to search" cannot arrive through one channel.
        lines.append("--- groupshared-pointer phi/select in the output ---")
        if not asm.strip():
            lines.append("3429: PARSE-WARNING: no output to search")
        else:
            hits = [("%d: %s" % (n, ln.rstrip()))
                    for n, ln in enumerate(asm.splitlines(), 1)
                    if ("phi" in ln or "select" in ln) and "addrspace(3)" in ln]
            lines.extend(hits if hits else
                         ["none (%d output lines searched)" % len(asm.splitlines())])
        lines.append("--- output ---")
        lines.append(asm.rstrip())
        lines.append("")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote " + OUT)


if __name__ == "__main__":
    main()
