"""#4273 -- is `-remove-unused-globals` actually parsed and honoured by the
rewriter, or does the retained `cbuffer` merely mean the flag was ignored?

SKILL.md's standing hazard: "Unrecognised `/`-style flags are silently ignored
-- `/ZZZNONSENSE` can exit 0 -- so a clean exit never proves a flag was
honoured. Put the nonsense control where the real option goes and compare the
produced artifact byte-for-byte with the same command WITHOUT the option."

That matters more than usual here, because the whole finding is that a flag ran
and left something behind. If the flag were being dropped on the floor, the
retained `cbuffer cbB` would be an artefact of the harness rather than a
property of the rewriter, and the verdict would be worthless.

Every case below is one `dxr.exe` invocation over the same `repro.hlsl`,
differing only in the token that occupies the `-remove-unused-globals` slot.
`sha256` is over combined stdout+stderr; two cases with the same digest
produced byte-identical output.

    python flagcheck.py     # writes manual-case-flag-parsing.txt
"""

import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
DXR = os.path.join(BUILD_BIN, "dxr.exe")

TAIL = ["-remove-unused-functions", "-extract-entry-uniforms", "repro.hlsl"]
CASES = [
    ("real-dash", ["-remove-unused-globals"],
     "the reporter's spelling"),
    ("real-slash", ["/remove-unused-globals"],
     "MSVC-style prefix of the same option"),
    ("absent", [],
     "baseline: the option removed entirely"),
    ("nonsense-slash", ["/ZZZNONSENSE"],
     "SKILL.md's silent-ignore control, in the option's own slot"),
    ("nonsense-dash", ["-ZZZNONSENSE"],
     "same nonsense with the '-' prefix"),
    ("misspelled", ["-remove-unused-global"],
     "the real option minus one character -- proves the exact spelling is "
     "what the parser recognises"),
]


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
    argv = [DXR, "-E", "vsMain", *slot, *TAIL]
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, timeout=300)
    text = p.stdout + p.stderr
    return {"case": name, "why": why,
            # echoed from the argv that actually ran, not transcribed
            "cmd": redact(argv[0]) + " " + subprocess.list2cmdline(argv[1:]),
            "exit": p.returncode,
            "sha256": hashlib.sha256(
                text.encode("utf-8", "replace")).hexdigest(),
            "loose_unused_removed": "gLooseUnused" not in text,
            "cbB_present": "cbuffer cbB" in text,
            "output": text}


def main():
    if not os.path.isfile(DXR):
        sys.exit(f"no dxr.exe at {redact(DXR)}; set DXC_BUILD_BIN")
    rows = [run(c) for c in CASES]
    by = {r["case"]: r for r in rows}

    out = [
        "#4273 -- is -remove-unused-globals parsed and honoured?",
        "",
        "Produced by `python flagcheck.py`. Every case is the same dxr.exe over",
        "the same repro.hlsl, differing only in the token occupying the",
        "-remove-unused-globals slot. sha256 is over combined stdout+stderr.",
        "",
        "  gLooseUnused is an unused LOOSE global (it would land in $Globals).",
        "  Removing it is the documented job of -remove-unused-globals, so its",
        "  disappearance is the behavioural proof the flag was honoured -- exit",
        "  status and the absence of a diagnostic are both insufficient.",
        "  cbuffer cbB is the unused explicit block this issue is about.",
        "",
        f"{'case':>15} {'exit':>5} {'gLooseUnused':>13} {'cbuffer cbB':>12}"
        f"  sha256(first 16)",
        f"{'-' * 15} {'-' * 5} {'-' * 13} {'-' * 12}  {'-' * 16}",
    ]
    for r in rows:
        # A run that exited non-zero emitted a diagnostic and no rewritten
        # HLSL, so neither identifier column says anything about it; printing
        # "removed"/"absent" there would read as a measurement it did not make.
        loose = ("removed" if r["loose_unused_removed"] else "KEPT") \
            if r["exit"] == 0 else "n/a"
        cbb = ("present" if r["cbB_present"] else "absent") \
            if r["exit"] == 0 else "n/a"
        out.append(
            f"{r['case']:>15} {r['exit']:>5} {loose:>13} {cbb:>12}  "
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
        ("real-dash and real-slash are byte-identical",
         by["real-dash"]["sha256"] == by["real-slash"]["sha256"],
         "both spellings of the real option reach the same code"),
        ("nonsense-slash is byte-identical to absent",
         by["nonsense-slash"]["sha256"] == by["absent"]["sha256"],
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
         "the parser recognises the exact spelling, so real-dash cannot have "
         "been an accidental near-match"),
        ("cbuffer cbB survives in every case that ran",
         all(r["cbB_present"] for r in rows if r["exit"] == 0),
         "the retained block is not a function of the flag at all"),
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
