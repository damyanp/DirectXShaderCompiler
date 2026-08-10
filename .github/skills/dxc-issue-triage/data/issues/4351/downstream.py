"""#4351 -- what is the harm? Compile the rewriter's own output with `dxc`.

The issue's symptom is stated as text going missing. That is only interesting if
the resulting source is actually broken, so this script closes the loop: it
takes the bytes `dxr` emitted for the reporter's exact command line, hands them
to `dxc`, and records what happens.

Two controls make the result attributable:

  original      the reporter's UNREWRITTEN repro.hlsl, same dxc command. It must
                COMPILE. Without it, a failure on the rewritten source could be
                a bad profile, a wrong entry point name, or a shader that never
                compiled in the first place.
  unchanged     the same rewriter, same driver, same file, with NO rewriter
                option -- i.e. `// Rewrite unchanged result:` mode. It must also
                COMPILE. This is the one that isolates the removal: it proves
                the rewriter's reformatting, its handling of `[numthreads]`, its
                `RWStructuredBuffer` printing and everything else about its
                output shape are fine, so the only thing that breaks the
                rewritten source is the deleted type definition.

    python downstream.py    # writes rewritten.hlsl + manual-case-downstream.txt
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
SCRATCH = os.path.join(SKILL, ".cache", "scratch4351")
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
DXR = os.path.join(BUILD_BIN, "dxr.exe")
DXC = os.path.join(BUILD_BIN, "dxc.exe")

REPRO_OPTS = ["-E", "InitArgs", "-remove-unused-globals"]
DXC_OPTS = ["-T", "cs_6_0", "-E", "InitArgs"]


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


def run(argv, cwd=HERE):
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=cwd, timeout=300)
    return {"cmd": redact(argv[0]) + " " + subprocess.list2cmdline(
                [redact(x) if os.path.isabs(x) else x for x in argv[1:]]),
            "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def main():
    for exe in (DXR, DXC):
        if not os.path.isfile(exe):
            sys.exit(f"missing {redact(exe)}; set DXC_BUILD_BIN")
    os.makedirs(SCRATCH, exist_ok=True)

    steps = []

    # 1. the reporter's command; its stdout IS the rewritten shader.
    rw = run([DXR, *REPRO_OPTS, "repro.hlsl"])
    rw["what"] = "the reporter's command line; stdout is the rewritten shader"
    steps.append(rw)
    rewritten = os.path.join(HERE, "rewritten.hlsl")
    with open(rewritten, "w", newline="") as f:
        f.write(rw["stdout"])

    # 2. the same rewriter with no rewriter option -- the CONTROL output.
    un = run([DXR, "-E", "InitArgs", "repro.hlsl"])
    un["what"] = "CONTROL: same rewriter, no rewriter option (unchanged mode)"
    steps.append(un)
    unchanged = os.path.join(SCRATCH, "rewritten-unchanged.hlsl")
    with open(unchanged, "w", newline="") as f:
        f.write(un["stdout"])

    # 3-5. hand all three sources to dxc, identical options.
    c_orig = run([DXC, *DXC_OPTS, "repro.hlsl"])
    c_orig["what"] = ("CONTROL: the reporter's ORIGINAL source. Must compile, "
                      "or nothing below is attributable to the rewrite")
    steps.append(c_orig)

    c_unch = run([DXC, *DXC_OPTS, unchanged])
    c_unch["what"] = ("CONTROL: the unchanged-mode rewriter output. Must "
                      "compile -- isolates the removal from the rewriter's "
                      "output shape")
    steps.append(c_unch)

    c_rw = run([DXC, *DXC_OPTS, "rewritten.hlsl"])
    c_rw["what"] = "SUBJECT: the rewritten shader from step 1"
    steps.append(c_rw)

    checks = [
        ("the original source compiles", c_orig["exit"] == 0,
         "the repro is a valid shader at cs_6_0 with entry point InitArgs"),
        ("the unchanged-mode rewriter output compiles", c_unch["exit"] == 0,
         "the rewriter's output shape is fine; only the removal is at issue"),
        ("the rewritten shader does NOT compile", c_rw["exit"] != 0,
         "the emitted source is not valid HLSL"),
        ("dxc names the removed type",
         "Child" in (c_rw["stdout"] + c_rw["stderr"]),
         "the failure is about `Child` specifically, not some unrelated error"),
    ]

    out = [
        "#4351 -- downstream cost: does the rewriter's output still compile?",
        "",
        "Produced by `python downstream.py`. Every command below is echoed from",
        "the argv that actually ran (subprocess.list2cmdline), not transcribed.",
        "",
        "READINGS", "",
    ]
    for label, ok, why in checks:
        out += [f"  [{'PASS' if ok else 'FAIL'}] {label}", f"         {why}"]
    out += ["", "", "VERBATIM", ""]
    for s in steps:
        out += [f"=== {s['what']} ===", f"$ {s['cmd']}", f"[exit] {s['exit']}",
                "--- stdout ---", s["stdout"].rstrip("\n"),
                "--- stderr ---", s["stderr"].rstrip("\n"), ""]

    with open(os.path.join(HERE, "downstream.json"), "w") as f:
        json.dump(steps, f, indent=2)
    path = os.path.join(HERE, "manual-case-downstream.txt")
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    for label, ok, _ in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print("wrote", redact(rewritten))
    print("wrote", redact(path))
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
