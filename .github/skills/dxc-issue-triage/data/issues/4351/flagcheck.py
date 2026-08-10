"""#4351 -- is `-remove-unused-globals` actually parsed and honoured here, or is
the missing `struct Child` an artefact of an option that never took effect?

SKILL.md's standing hazard: unrecognised `/`-style flags are silently ignored,
so a clean exit never proves a flag was honoured. The way to prove it is a
three-way comparison -- flag present vs flag absent vs flag misspelled --
where present-vs-absent must DIFFER (the flag did something) and misspelled
must FAIL LOUDLY (the name typed is the name the parser knows).

That matters for this issue specifically because the reported symptom is an
ABSENCE. If the option were being dropped on the floor, the missing `struct
Child` would have to come from somewhere else entirely, and the attribution in
the issue title would be wrong.

Every case below is one `dxr.exe` invocation over the same `repro.hlsl`,
differing only in the token occupying the `-remove-unused-globals` slot.
`sha256` is over combined stdout+stderr; equal digests mean byte-identical
output.

    python flagcheck.py     # writes manual-case-flag-parsing.txt
"""

import hashlib
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

HEAD = ["-E", "InitArgs"]
TAIL = ["repro.hlsl"]
CASES = [
    ("real-dash", ["-remove-unused-globals"],
     "the reporter's spelling, exactly as filed"),
    ("real-slash", ["/remove-unused-globals"],
     "MSVC-style prefix of the same option"),
    ("absent", [],
     "baseline: the option removed entirely"),
    ("nonsense-slash", ["/ZZZNONSENSE", "-remove-unused-globals"],
     "SKILL.md's silent-ignore control, alongside the real option"),
    ("nonsense-dash", ["-ZZZNONSENSE", "-remove-unused-globals"],
     "the same nonsense with a '-' prefix"),
    ("misspelled", ["-remove-unused-global"],
     "the real option minus one character -- proves the exact spelling is "
     "what the parser recognises, so real-dash was not an accidental "
     "near-match"),
]

CHILD_DEFN = re.compile(r"struct\s+Child\s*\{")
BANNER = "// Rewrite unchanged result:"


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


def run(case):
    name, slot, why = case
    argv = [DXR, *HEAD, *slot, *TAIL]
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    text = p.stdout + p.stderr
    return {"case": name, "why": why,
            # echoed from the argv that actually ran, not transcribed
            "cmd": redact(argv[0]) + " " + subprocess.list2cmdline(argv[1:]),
            "exit": p.returncode,
            "sha256": hashlib.sha256(
                text.encode("utf-8", "replace")).hexdigest(),
            "child_defn_present": bool(CHILD_DEFN.search(text)),
            "unchanged_banner": BANNER in text,
            "output": text}


def main():
    if not os.path.isfile(DXR):
        sys.exit(f"no dxr.exe at {redact(DXR)}; set DXC_BUILD_BIN")
    rows = [run(c) for c in CASES]
    by = {r["case"]: r for r in rows}

    out = [
        "#4351 -- is -remove-unused-globals parsed and honoured?",
        "",
        "Produced by `python flagcheck.py`. Every case is the same dxr.exe over",
        "the same repro.hlsl, differing only in the token occupying the",
        "-remove-unused-globals slot. sha256 is over combined stdout+stderr.",
        "",
        "  `struct Child` is the definition this issue says is wrongly removed.",
        "  The `// Rewrite unchanged result:` banner is printed by",
        "  tools/clang/tools/libclang/dxcrewriteunused.cpp:1087 only when",
        "  NEITHER -remove-unused-globals NOR -remove-unused-functions was set,",
        "  so it is a positive marker of which code path the run took -- which",
        "  exit status alone cannot tell you.",
        "",
        f"{'case':>15} {'exit':>5} {'struct Child':>13}"
        f" {'unchanged banner':>17}  sha256(first 16)",
        f"{'-' * 15} {'-' * 5} {'-' * 13} {'-' * 17}  {'-' * 16}",
    ]
    for r in rows:
        # A run that exited non-zero emitted a diagnostic and no rewritten
        # HLSL, so neither content column says anything about it; printing
        # "present"/"removed" there would read as a measurement it did not make.
        child = ("present" if r["child_defn_present"] else "REMOVED") \
            if r["exit"] == 0 else "n/a"
        banner = ("yes" if r["unchanged_banner"] else "no") \
            if r["exit"] == 0 else "n/a"
        out.append(f"{r['case']:>15} {r['exit']:>5} {child:>13} {banner:>17}  "
                   f"{r['sha256'][:16]}")
    out += ["", "WHAT EACH CASE IS FOR", ""]
    for r in rows:
        out.append(f"  {r['case']:<15} {r['why']}")

    out += ["", "READINGS", ""]
    checks = [
        ("real-dash differs from absent",
         by["real-dash"]["sha256"] != by["absent"]["sha256"],
         "the option changes the output, so it is parsed and honoured -- not "
         "silently ignored"),
        ("the difference is exactly the removal under test",
         by["real-dash"]["child_defn_present"] is False
         and by["absent"]["child_defn_present"] is True,
         "with the option, `struct Child` is gone; without it, `struct Child` "
         "is present -- so the removal is attributable to this option and to "
         "nothing else in the command line"),
        ("real-dash and real-slash are byte-identical",
         by["real-dash"]["sha256"] == by["real-slash"]["sha256"],
         "both spellings of the real option reach the same code"),
        ("nonsense-slash is byte-identical to real-dash",
         by["nonsense-slash"]["sha256"] == by["real-dash"]["sha256"],
         "/ZZZNONSENSE exits 0 and does nothing: a clean exit proves nothing "
         "about a '/'-prefixed flag, exactly as SKILL.md warns"),
        ("nonsense-dash is diagnosed",
         by["nonsense-dash"]["exit"] != 0
         and "Unknown argument" in by["nonsense-dash"]["output"],
         "the '-' prefix IS validated by dxr's own option parse, so the "
         "silent-ignore hazard is specific to '/'"),
        ("misspelled is diagnosed",
         by["misspelled"]["exit"] != 0
         and "Unknown argument" in by["misspelled"]["output"],
         "the parser recognises the exact spelling"),
        ("the unchanged-rewrite banner tracks the option",
         by["absent"]["unchanged_banner"] is True
         and by["real-dash"]["unchanged_banner"] is False,
         "confirms match.json clause 4 is a valid in-run self-test that a "
         "rewriter option was honoured"),
    ]
    for label, ok, why in checks:
        out.append(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        out.append(f"         {why}")
    out.append("")

    out += ["", "VERBATIM", ""]
    for r in rows:
        out += [f"=== {r['case']} ===", f"$ {r['cmd']}", f"[exit] {r['exit']}",
                f"[sha256] {r['sha256']}", "", r["output"].rstrip("\n"), ""]

    with open(os.path.join(HERE, "flagcheck.json"), "w") as f:
        json.dump(rows, f, indent=2)
    path = os.path.join(HERE, "manual-case-flag-parsing.txt")
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    for label, ok, _ in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print("wrote", redact(path))
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
