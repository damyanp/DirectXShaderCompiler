"""#4415: build the DXIL modules the validator is asked about.

The issue's ask is that DXIL validation reject an `annotateHandle` whose `res`
operand is an invalid handle. DXC's own front end produces exactly that from
repro.hlsl, but the validator's job is to reject such DXIL whoever produced it,
so the interesting cases are also constructed deliberately -- a third-party
producer emitting the same shape without any of DXC's front end involved.

Every command is echoed with `subprocess.list2cmdline` before it runs, and every
textual patch asserts it actually changed something, so a reader can re-derive
this file instead of trusting it (SKILL.md: "Generate every manual-case-*.txt
from a small script that echoes the command it is about to run", and "if a
harness generates the text its own predicate scores, make it assert what it
expects to find and print a loud marker when it finds nothing").

Run from this directory:
    python make-modules.py > manual-case-make-modules.txt
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4415/ -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
BIN = os.environ.get("DXC_BIN", os.path.join(REPO, "build", "Debug", "bin"))
DXC = os.path.join(BIN, "dxc.exe")

# Normalise machine paths with triage.py's own rule rather than reimplementing
# it here; it tokenises the checkout, triage and release-cache roots, matching
# either separator, repeated separators and any case.
sys.path.insert(0, os.path.join(REPO, ".github", "skills", "dxc-issue-triage",
                                "scripts"))
import triage  # noqa: E402

ANNOT = "@dx.op.annotateHandle(i32 216, %dx.types.Handle "
CBLOAD = "@dx.op.cbufferLoadLegacy.i32(i32 59, %dx.types.Handle "
TEXLOAD = "@dx.op.textureLoad.f32(i32 66, %dx.types.Handle "


def display(path):
    return triage.redact_paths(os.path.abspath(path)).replace(os.sep, "/")


def run(argv):
    print("$ " + subprocess.list2cmdline(
        [display(a) if os.path.isabs(a) else a for a in argv]))
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    text = triage.redact_paths((p.stdout + p.stderr).strip())
    if text:
        print(text)
    print("[exit] 0x%08X" % (p.returncode & 0xFFFFFFFF))
    return p.returncode


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def write(name, text):
    with open(os.path.join(HERE, name), "w", encoding="utf-8",
              newline="\n") as f:
        f.write(text)
    print("[wrote] %s (%d bytes)" % (name, len(text)))


def patch(src, dst, old, new, expect, why):
    """Replace `old` with `new` exactly `expect` times, or say so loudly."""
    text = read(src)
    n = text.count(old)
    print("\n---- %s: %s" % (dst, why))
    print("[patch] %d occurrence(s) of %r" % (n, old))
    if n != expect:
        print("[PATCH-WARNING] expected %d, found %d -- module NOT written, "
              "and anything downstream that names it is measuring nothing"
              % (expect, n))
        return False
    out = text.replace(old, new)
    if out == text:
        print("[PATCH-WARNING] substitution changed nothing")
        return False
    write(dst, out)
    return True


def show_annotate(name):
    """Echo the annotateHandle lines of a module, so the diff is visible here."""
    for line in read(name).splitlines():
        if "annotateHandle(i32 216" in line:
            print("    %s | %s" % (name, line.strip()))


def main():
    print("#4415 module generator")
    run([DXC, "--version"])

    print("\n================ compiler-produced modules ================")
    print("# repro.hlsl is the issue body verbatim. DXC's own output is the")
    print("# first subject: the reporter quoted its annotateHandle line.")
    if run([DXC, "-T", "vs_6_6", "-E", "main", "repro.hlsl",
            "-Fc", "emitted.ll"]) != 0:
        sys.exit("repro.hlsl did not compile; nothing below is meaningful")
    show_annotate("emitted.ll")

    print("\n# control-valid.hlsl is the same shader with the initialization")
    print("# order fixed. It is the base for every doctored module below, so")
    print("# each one differs from a KNOWN-VALID module in one operand only.")
    if run([DXC, "-T", "vs_6_6", "-E", "main", "control-valid.hlsl",
            "-Fc", "valid.ll"]) != 0:
        sys.exit("control-valid.hlsl did not compile")
    show_annotate("valid.ll")

    valid = read("valid.ll")
    hit = re.search(re.escape(ANNOT) + r"([^,]+),", valid)
    if not hit:
        sys.exit("[PATCH-WARNING] no annotateHandle in valid.ll")
    handle = hit.group(1).strip()
    print("\n[base] valid.ll annotateHandle res operand = %r" % handle)
    if handle in ("undef", "zeroinitializer", "null"):
        sys.exit("[PATCH-WARNING] the base module is already invalid")

    cbhit = re.search(re.escape(CBLOAD) + r"([^,]+),", valid)
    if not cbhit:
        sys.exit("[PATCH-WARNING] no cbufferLoadLegacy in valid.ll")
    cbhandle = cbhit.group(1).strip()
    print("[base] valid.ll cbufferLoadLegacy handle operand = %r" % cbhandle)

    print("\n================ doctored modules ================")
    patch("valid.ll", "zeroinit.ll",
          ANNOT + handle + ",", ANNOT + "zeroinitializer,", 1,
          "SUBJECT: annotateHandle res operand -> zeroinitializer, the exact "
          "shape the issue quotes, in a module DXC's front end never made")
    show_annotate("zeroinit.ll")

    patch("valid.ll", "undefhandle.ll",
          ANNOT + handle + ",", ANNOT + "undef,", 1,
          "SUBJECT: annotateHandle res operand -> undef, the other spelling of "
          "an invalid handle")
    show_annotate("undefhandle.ll")

    patch("valid.ll", "control-undef-checked-op.ll",
          CBLOAD + cbhandle + ",", CBLOAD + "undef,", 1,
          "CONTROL, must FAIL: the same invalid handle on cbufferLoadLegacy, "
          "an opcode ValidateHandleArgs does check. NB this one fails via an "
          "internal cast error (0x80aa001d) rather than the rule text -- see "
          "method-notes.md; the clean-rule-text controls are the textureLoad "
          "pair below")

    patch("valid.ll", "control-badprops.ll",
          ANNOT + handle + ", %dx.types.ResourceProperties { i32 13, i32 4 }",
          ANNOT + handle + ", %dx.types.ResourceProperties { i32 0, i32 0 }", 1,
          "CONTROL, must FAIL: the SAME annotateHandle instruction with an "
          "invalid resource kind in its props operand. Proves the validator "
          "does inspect this instruction -- just not its handle operand")
    show_annotate("control-badprops.ll")

    print("\n================ checked-opcode controls ================")
    print("# Same two invalid handle values, on an opcode ValidateHandleArgs")
    print("# does check. These are the pair the verdict rests on: if these")
    print("# fail and the annotateHandle subjects pass, the difference is the")
    print("# opcode, because nothing else differs.")
    if run([DXC, "-T", "ps_6_6", "-E", "main", "control-checked-op.hlsl",
            "-Fc", "checkedop.ll"]) != 0:
        sys.exit("control-checked-op.hlsl did not compile")

    checked = read("checkedop.ll")
    txhit = re.search(re.escape(TEXLOAD) + r"([^,]+),", checked)
    if not txhit:
        sys.exit("[PATCH-WARNING] no textureLoad in checkedop.ll")
    txhandle = txhit.group(1).strip()
    print("[base] checkedop.ll textureLoad handle operand = %r" % txhandle)
    if txhandle in ("undef", "zeroinitializer", "null"):
        sys.exit("[PATCH-WARNING] the base module is already invalid")

    patch("checkedop.ll", "control-checkedop-zeroinit.ll",
          TEXLOAD + txhandle + ",", TEXLOAD + "zeroinitializer,", 1,
          "CONTROL, must FAIL: zeroinitializer handle on textureLoad. Same "
          "invalid value as zeroinit.ll, different opcode")

    patch("checkedop.ll", "control-checkedop-undef.ll",
          TEXLOAD + txhandle + ",", TEXLOAD + "undef,", 1,
          "CONTROL, must FAIL: undef handle on textureLoad. Same invalid "
          "value as undefhandle.ll, different opcode")

    print("\n================ summary ================")
    for name in ("emitted.ll", "valid.ll", "zeroinit.ll", "undefhandle.ll",
                 "control-undef-checked-op.ll", "control-badprops.ll",
                 "checkedop.ll", "control-checkedop-zeroinit.ll",
                 "control-checkedop-undef.ll"):
        p = os.path.join(HERE, name)
        print("  %-30s %s" % (name, "%d bytes" % os.path.getsize(p)
                              if os.path.isfile(p) else "MISSING"))


if __name__ == "__main__":
    main()
