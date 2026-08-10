"""Generate the DXIL modules used to triage #4256.

Every module is derived from `repro.hlsl` by compiling it with the ground-truth
`dxc` and then applying one documented text edit to the resulting disassembly.
The script echoes every command it runs (`subprocess.list2cmdline`), so the
transcript in `manual-case-make-modules.txt` is what actually executed rather
than a transcription of it.

  full.ll      unmodified DXC output. Positive control: this must validate.
  nostate.ll   `!dx.viewIdState = !{!4}` deleted -- the module a producer that
               "just does not emit a view ID metadata node" would hand over.
               Issue #4256's second sentence, exactly.
  zerodeps.ll  the state node kept but its payload reduced to the two scalar
               counts with every dependency bit cleared: "no output depends on
               ViewID, no input contributes to any output". Issue #4256's third
               sentence -- the input->output dependency mapping omitted.
  wrongdeps.ll the state node kept, sizes kept, dependency bits replaced with a
               different, non-zero, *false* mapping. Distinguishes "absence is
               tolerated" from "the contents are never checked at all".
  badsig.ll    NEGATIVE CONTROL, unrelated to ViewID: one storeOutput given an
               out-of-range signature id. The validator must reject it, which
               is what proves the harness really validates.
  sm60.ll      NEGATIVE CONTROL, on-topic: shader model lowered to 6.0 with the
               ViewID op left in place. The validator must reject it, which is
               what proves the validator does read the `dx.op.viewID` call in
               the body -- it has the information, it just never compares it
               with the serialized state.

A second, identical set is emitted with the `val18-` prefix, compiled with
`-validator-version 1.8`. It exists only for `release-matrix.py`: the default
set declares `!dx.valver = !{i32 1, i32 10}` and every shipped validator caps
at 1.9, so the whole matrix -- the positive control included -- came back
"Validator version in metadata (1.10) is not supported", which is an
`invalid-probe` that measured nothing. `validate.py` is run over the val18 set
on ground truth as well, so the deviation is measured rather than assumed inert
(SKILL.md: "measure every command-line deviation ... with an equivalence
control").

Run from this directory:  python make-modules.py
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4256/ -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
BIN = os.environ.get("DXC_BIN", os.path.join(REPO, "build", "Debug", "bin"))
DXC = os.path.join(BIN, "dxc.exe")


def display(path):
    """Machine-independent spelling; `scripts/check_paths.py` rejects the other."""
    p = os.path.abspath(path)
    rel = os.path.relpath(p, REPO)
    if not rel.startswith(os.pardir):
        return "<repo>/" + rel.replace(os.sep, "/")
    return os.path.basename(p)


# The exact array DXC computes for repro.hlsl, and the pieces of it.
#   [0]  8   number of input scalars   (POSITION.xyzw + COLOR.xyzw)
#   [1]  8   number of output scalars  (SV_Position.xyzw + COLOR.xyzw)
#   [2] 15   OutputsDependentOnViewId bitmask -> outputs {0,1,2,3}
#   [3..10]  InputsContributingToOutputs, one uint per input scalar
TRUE_STATE = [8, 8, 15, 1, 2, 4, 8, 16, 32, 64, 128]
ZERO_DEPS = [8, 8] + [0] * 9
WRONG_DEPS = [8, 8, 240, 128, 64, 32, 16, 8, 4, 2, 1]


def state_literal(vals):
    return "[%d x i32] [%s]" % (len(vals), ", ".join("i32 %d" % v for v in vals))


def run(argv):
    print("$ " + subprocess.list2cmdline([display(argv[0])] + argv[1:]),
          flush=True)
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.stdout.strip():
        print(p.stdout.rstrip())
    if p.stderr.strip():
        print(p.stderr.rstrip())
    print("[exit] %d" % p.returncode, flush=True)
    if p.returncode != 0:
        sys.exit("command failed")


def substitute_once(text, pattern, replacement, what):
    """Apply exactly one substitution, or fail loudly.

    A silently-missing edit is the whole hazard here: the file would still be
    written, still validate, and still look like evidence.
    """
    new, n = re.subn(pattern, replacement.replace("\\", "\\\\"), text, count=1)
    if n != 1:
        sys.exit("EDIT-FAILED: %s matched %d times, expected 1" % (what, n))
    return new


def write(name, text):
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("[wrote] %s (%d bytes)" % (name, len(text)), flush=True)


def main():
    run([DXC, "--version"])
    emit("", [])
    emit("val18-", ["-validator-version", "1.8"])
    print("[done] both module sets generated")


def emit(prefix, extra_args):
    src = prefix + "full.ll"
    run([DXC, "-T", "vs_6_1", "-E", "main", "repro.hlsl", "-Fc", src]
        + extra_args)

    with open(os.path.join(HERE, src), encoding="utf-8") as f:
        full = f.read().replace("\r\n", "\n")
    write(src, full)

    if state_literal(TRUE_STATE) not in full:
        sys.exit("EDIT-FAILED: DXC did not emit the expected ViewID state "
                 "%s -- the constants in this script are stale" % TRUE_STATE)
    print("[selftest] dxc emitted the expected ViewID state %s" % TRUE_STATE)
    valver = re.search(r"!dx\.valver = !\{!(\d+)\}", full)
    if valver:
        node = re.search(r"^!%s = !\{i32 (\d+), i32 (\d+)\}\s*$"
                         % valver.group(1), full, re.MULTILINE)
        if node:
            print("[selftest] module declares validator version %s.%s"
                  % node.groups())

    write(prefix + "nostate.ll", substitute_once(
        full, r"!dx\.viewIdState = !\{![0-9]+\}\n", "",
        "delete the dx.viewIdState named metadata"))

    write(prefix + "zerodeps.ll", substitute_once(
        full, re.escape(state_literal(TRUE_STATE)), state_literal(ZERO_DEPS),
        "clear every dependency bit in the ViewID state"))

    write(prefix + "wrongdeps.ll", substitute_once(
        full, re.escape(state_literal(TRUE_STATE)), state_literal(WRONG_DEPS),
        "replace the ViewID state with a different, false mapping"))

    write(prefix + "badsig.ll", substitute_once(
        full,
        r"@dx\.op\.storeOutput\.f32\(i32 5, i32 1, i32 0, i8 3, float %4\)",
        "@dx.op.storeOutput.f32(i32 5, i32 7, i32 0, i8 3, float %4)",
        "point one storeOutput at an out-of-range signature id"))

    write(prefix + "sm60.ll", substitute_once(
        full, r'!\{!"vs", i32 6, i32 1\}', '!{!"vs", i32 6, i32 0}',
        "lower the shader model to 6.0 while keeping the ViewID op"))


if __name__ == "__main__":
    main()
