#!/usr/bin/env python3
"""Compiler Explorer probe for #4096's discriminating case.

The published link (`godbolt.txt`) carries the reporter's exact shader, on which
Clang exits 0 -- but that shader's body is dead code, so an empty `main()` does
not say whether Clang *invoked* the operator or merely accepted the source.

`case-cstyle-cast.hlsl` and `case-if-discriminating.hlsl` make the two candidate
conversions disagree and write the answer to a buffer: 222 if the operator body
ran, 111 if HLSL's flat conversion was substituted. The first uses an explicit
C-style cast, the second the reporter's own `if` condition. This asks Clang and
DXC that question, and also compiles two controls
(`control-no-operator.hlsl`, `control-rwbuffer-only.hlsl`) so a Clang failure
cannot be mistaken for a verdict about the operator when it is really about
`RWBuffer` or the shader shape.

Every request is echoed. Run from this directory:

    python probe-clang.py > manual-case-clang-discriminating.txt
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))

spec = importlib.util.spec_from_file_location(
    "triage", os.path.join(SKILL, "scripts", "triage.py"))
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)

PANES = [
    ("case-if-discriminating.hlsl", "dxc_1_6_2112", "-T cs_6_0 -E main -HV 2021"),
    ("case-if-discriminating.hlsl", "dxc_trunk", "-T cs_6_0 -E main -HV 2021"),
    ("case-if-discriminating.hlsl", "hlsl_clang_trunk", "-T cs_6_0 -E main"),
    ("case-cstyle-cast.hlsl", "dxc_1_6_2112", "-T cs_6_0 -E main -HV 2021"),
    ("case-cstyle-cast.hlsl", "dxc_trunk", "-T cs_6_0 -E main -HV 2021"),
    ("case-cstyle-cast.hlsl", "hlsl_clang_trunk", "-T cs_6_0 -E main"),
    ("control-no-operator.hlsl", "hlsl_clang_trunk", "-T cs_6_0 -E main"),
    ("control-rwbuffer-only.hlsl", "hlsl_clang_trunk", "-T cs_6_0 -E main"),
]

DISCRIMINATING = ("case-cstyle-cast.hlsl", "case-if-discriminating.hlsl")


def read(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read()


def main():
    print("# #4096: Compiler Explorer probe of the discriminating case.")
    print("# Written by probe-clang.py; rerun it to re-derive.")
    print("# CE runs Linux Release builds and never overrules the local "
          "Debug build.")
    print("# NOTE: no godbolt-note.txt banner is prepended here -- this file "
          "is a")
    print("#       measurement, not a published link, so the source is "
          "exactly the")
    print("#       committed shader.")
    print()
    for shader, compiler, args in PANES:
        print("=" * 74)
        print("# POST /api/compiler/%s/compile" % compiler)
        print("# source:   %s" % shader)
        print("# args:     %s" % args)
        rc, text, crashed = triage.ce_compile(read(shader), compiler, args)
        print("# exit:     %s%s" % (rc, "  (internal failure)"
                                    if crashed else ""))
        stored = [v for v in ("111", "222") if ("i32 %s," % v) in text]
        if shader in DISCRIMINATING:
            if len(stored) == 1:
                print("# read:     stored %s -> %s" % (
                    stored[0],
                    "FLAT CONVERSION used, operator body NOT invoked"
                    if stored[0] == "111" else "operator body invoked"))
            elif rc == 0:
                print("# read:     PROBE-4096: PARSE-WARNING: compiled "
                      "cleanly but neither constant is in the output %r "
                      "-- read the text below" % stored)
            else:
                print("# read:     rejected; see diagnostics below")
        print()
        print(text)
        print()


if __name__ == "__main__":
    main()
