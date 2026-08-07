"""Probe `triage.py`'s invalid-probe classifier on a MISSING-DIAGNOSTIC issue.

#2792's reported symptom is an error that does not appear, so its predicate has
to express an absence. `classify()` carries three demotion rules that interact
with that shape, and this script exercises all of them against *real* captured
output plus a small set of hypothetical diagnostics, so the finding in
method-notes.md is reproducible rather than asserted.

Run from the skill root:

    python data/issues/2792/classifier-probe.py

Writes nothing. Reads only this issue's captures and the throwaway predicates
in classifier-probe-*.json (named so they cannot be mistaken for match.json or
for a second `match-*.json` predicate).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import triage  # noqa: E402

ISSUE = 2792
E_FAIL = 0x80004005


def body(path):
    """The captured output beneath an out-*/variant-* header."""
    with open(os.path.join(HERE, path), encoding="utf-8", errors="replace") as f:
        text = f.read()
    meta, out = triage.read_out(os.path.join(HERE, path))
    return out, int(meta.get("exit", "0"))


def show(title, text, rc, match_file):
    v, why = triage.classify(ISSUE, text, rc, False,
                             match_file=match_file, explain=True)
    absence = triage._is_absence_predicate(ISSUE, match_file)
    print(f"  {title}")
    print(f"    predicate      : {match_file} (absence-shaped: {absence})")
    print(f"    exit           : 0x{rc & 0xFFFFFFFF:08X}"
          f"   internal_failure: {triage.is_internal_failure(text, rc, False)}")
    print(f"    -> verdict     : {v}")
    if why:
        print(f"    -> reason      : {why}")
    print()


print("=" * 78)
print("A. The real probes, under the predicate actually shipped (match.json)")
print("=" * 78)
print()
for label, path in (
        ("repro.hlsl on main-debug (out-of-bounds, accepted silently)",
         "out-main-debug.txt"),
        ("repro.hlsl on v1.4.1907 (oldest release)", "out-v1.4.1907.txt"),
        ("control-in-bounds (fully correct shader)",
         "variant-in-bounds-main-debug.txt"),
        ("control-rs-register-mismatch (dxc DOES diagnose this)",
         "variant-rs-register-mismatch-main-debug.txt"),
        ("control-rootconst-fits (correct; identical output to the repro)",
         "variant-rootconst-fits-main-debug.txt")):
    text, rc = body(path)
    show(label, text, rc, "match.json")

print("=" * 78)
print("B. Hypothetical future DXC that FIXES #2792 by emitting the diagnostic.")
print("   Scores no-repro (correct). Is it then demoted by the marker rule?")
print("=" * 78)
print()
FIXED = [
    ("plain wording",
     "repro.hlsl:9:10: error: cbuffer 'cb' is 8 bytes but the root constant "
     "block at b0 declares only 1 32-bit constant\n"),
    ("validator wording, mirroring the existing RS check",
     "error: validation errors\nerror: Root Signature in DXIL container is not "
     "compatible with shader.\nerror: Shader root constant range "
     "(RegisterSpace=0, ShaderRegister=0, Num32BitValues=1) does not cover "
     "cbuffer of size 8.\n"),
    ("wording that merely mentions the target -- does NOT trip a marker",
     "repro.hlsl:9:10: error: reading past the end of a root constant block "
     "is not supported for the target profile\n"),
    ("gated wording -- DOES trip the 'requires shader model' marker",
     "repro.hlsl:9:10: error: diagnosing a root constant overrun requires "
     "shader model 6.0 or above\n"),
]
for label, text in FIXED:
    show(label, text, E_FAIL, "match.json")

print("=" * 78)
print("C. The trap this issue is exposed to: a NAIVE absence-only predicate")
print("   ('no error mentions the root constant size'), which is what an")
print("   absence predicate for this issue looks like without a positive")
print("   anchor. Fed REAL output from an input dxc genuinely rejected.")
print("=" * 78)
print()
text, rc = body("variant-rs-register-mismatch-main-debug.txt")
show("control-rs-register-mismatch under the naive predicate",
     text, rc, "classifier-probe-naive-predicate.json")
show("a bare syntax error under the naive predicate",
     "repro.hlsl:3:3: error: expected ')'\n", E_FAIL,
     "classifier-probe-naive-predicate.json")
show("a release that cannot express the input (marker present)",
     "error: invalid profile ps_6_0\n", E_FAIL,
     "classifier-probe-naive-predicate.json")
show("a release that crashed",
     "Internal compiler error: access violation\n", 0xC0000005,
     "classifier-probe-naive-predicate.json")

print("=" * 78)
print("D. _predicate_quotes suppression -- the #3055 fix -- on this issue")
print("=" * 78)
print()
with open(os.path.join(HERE, "match.json"), encoding="utf-8") as f:
    m = json.load(f)
positives = [c.get("value") for c in m["value"]
             if c.get("kind") in ("contains", "regex") and not c.get("invert")]
print(f"  positive clauses of match.json: {positives}")
for marker in ("is not supported for the target", "use of undeclared identifier",
               "invalid profile"):
    print(f"  _predicate_quotes({marker!r}) = "
          f"{triage._predicate_quotes(ISSUE, 'match.json', marker)}")
print()
print("  The suppression requires a positive clause of the issue's own")
print("  predicate to quote the marker verbatim. #2792 asks for a diagnostic")
print("  that does not exist in any DXC, so there is no text to quote and the")
print("  suppression is structurally unavailable here.")
print()

print("=" * 78)
print("E. The mitigation actually used by match.json: anchor the absence with")
print("   a positive clause. Same four inputs as section C.")
print("=" * 78)
print()
text, rc = body("variant-rs-register-mismatch-main-debug.txt")
show("control-rs-register-mismatch under the anchored predicate",
     text, rc, "classifier-probe-anchored-predicate.json")
show("a bare syntax error under the anchored predicate",
     "repro.hlsl:3:3: error: expected ')'\n", E_FAIL,
     "classifier-probe-anchored-predicate.json")
show("a release that cannot express the input",
     "error: invalid profile ps_6_0\n", E_FAIL,
     "classifier-probe-anchored-predicate.json")
show("a release that crashed",
     "Internal compiler error: access violation\n", 0xC0000005,
     "classifier-probe-anchored-predicate.json")
print("  All four score no-repro or invalid-probe -- never a false `repro`.")
print("  The anchor, not the classifier, is what makes this issue safe.")

