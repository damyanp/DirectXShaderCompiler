"""Measure whether Compiler Explorer can host #3943's repro at all.

#3943 needs two files: a shader and a `#pragma once` header reached by two
spellings of one path. A CE pane has exactly one source, so the question is
whether some single-file restatement measures the same rule. SKILL.md records
that the obvious fold -- a file that includes *itself* under a different
spelling -- does not, because clang ignores `#pragma once` in the main file.
That claim is checked here rather than assumed, by running the fold on a
known-good case (matched spellings) and seeing whether it still passes.

Writes manual-case-ce-infeasible.txt beside this script. Re-runnable: it takes
no arguments and hardcodes nothing about the local machine.

    python ce-probe.py
"""

import json
import os
import re
import sys
import urllib.request

CE = "https://godbolt.org"
FILTERS = {"execute": False, "intel": False, "demangle": False,
           "labels": False, "directives": False, "commentOnly": False,
           "trim": False, "binary": False}
COMPILERS = ["dxc_trunk", "dxc_1_6_2112"]
ARGS = "-T ps_6_0 -E main -I inc"
HERE = os.path.dirname(os.path.abspath(__file__))


def ce_compile(source, compiler, args):
    payload = {
        "source": source, "lang": "hlsl", "compiler": compiler,
        "options": {
            "userArguments": args,
            "compilerOptions": {"skipAsm": False, "executorRequest": False},
            "filters": dict(FILTERS), "tools": [], "libraries": [],
        },
        "allowStoreCodeDebug": True,
    }
    req = urllib.request.Request(
        f"{CE}/api/compiler/{compiler}/compile", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        res = json.loads(r.read().decode())
    text = "\n".join(x.get("text", "") for stream in ("stdout", "stderr")
                     for x in res.get(stream, []))
    asm = "\n".join(x.get("text", "") for x in res.get("asm", [])
                    if isinstance(x, dict))
    return res.get("code"), (text + "\n" + asm).strip()


def main():
    out = []

    def emit(line=""):
        out.append(line)
        print(line)

    emit("# Can Compiler Explorer host #3943's repro?  Measured, not assumed.")
    emit(f"# probe: POST {CE}/api/compiler/<id>/compile   lang=hlsl")
    emit(f"# args:  {ARGS}")
    emit()

    # Phase 1 -- the real repro, unchanged. CE has no second file to give it.
    with open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8") as f:
        repro = f.read()
    cases = [("as-filed multi-file repro (repro.hlsl verbatim)", repro)]

    # Phase 2 -- the single-file fold and its control. A fold needs the name CE
    # gives the pane's source, which is read out of phase 1's diagnostic rather
    # than guessed.
    main_name = None
    for cid in COMPILERS[:1]:
        rc, text = ce_compile(repro, cid, ARGS)
        # CE masks the pane's real temporary path in compiler output, so the
        # name a diagnostic reports is whatever the reader would have to type.
        hit = re.search(r"^(\S+):\d+:\d+:", text, re.MULTILINE)
        if hit:
            main_name = hit.group(1)
    if not main_name:
        main_name = "<stdin>"
        emit(f"# NOTE: could not read the pane's source filename out of a "
             f"diagnostic; folds below use {main_name!r} and are inconclusive.")
        emit()

    fold_mismatched = (
        "// FOLD, mismatched spellings: the pane's own source includes itself\n"
        "// twice under two spellings. This is the transformation under test.\n"
        "#pragma once\n"
        f'#include "{main_name}"\n'
        f'#include "./{main_name}"\n'
        "float CommonValue() { return 1.0f; }\n"
        "float4 main() : SV_Target { return CommonValue(); }\n")
    fold_matched = (
        "// CONTROL for the fold: identical construction, but both spellings\n"
        "// MATCH. If `#pragma once` worked in the main file this must compile,\n"
        "// and the fold above would be a fair restatement of #3943. If this\n"
        "// fails too, the fold is measuring a different rule and must not be\n"
        "// published as a repro.\n"
        "#pragma once\n"
        f'#include "{main_name}"\n'
        f'#include "{main_name}"\n'
        "float CommonValue() { return 1.0f; }\n"
        "float4 main() : SV_Target { return CommonValue(); }\n")
    cases.append(("single-file FOLD, two spellings", fold_mismatched))
    cases.append(("single-file FOLD CONTROL, matched spellings", fold_matched))

    for title, source in cases:
        for cid in COMPILERS:
            emit(f"=== {title} -- {cid} ===")
            emit("--- source ---")
            for line in source.rstrip("\n").split("\n"):
                emit(f"  {line}")
            rc, text = ce_compile(source, cid, ARGS)
            emit(f"--- exit: {rc} ---")
            for line in (text or "(no output)").split("\n")[:14]:
                emit(f"  {line}")
            emit()

    with open(os.path.join(HERE, "manual-case-ce-infeasible.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
