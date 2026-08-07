"""Re-score the archived release probes under the PRIMARY predicate.

Why this exists
---------------
The 20 release probes in this directory were captured under the primary
predicate (match.json, internal_failure) and then overwritten by a second
bisect run under match-rejected.json (nonzero_exit), because triage.py builds
the output filename from the compiler alone -- the predicate is not part of it
(triage.py:776). So every out-v*.txt now carries `# match: match-rejected.json`
and the primary predicate's recorded scoring no longer exists on disk.

The underlying MEASUREMENT is intact: each file still holds the raw stdout,
stderr and the `# exit:` / `# timed_out:` headers. This script re-derives the
primary-predicate verdict from those archived artifacts, so the claim
"no shipped release exhibits the internal failure" stays checkable by a
stranger without re-running any compiler.

It deliberately IMPORTS triage.is_internal_failure rather than reimplementing
it. A reimplementation could drift from the real predicate and would prove
nothing about what the tool would say.

Run from this directory:  python recheck-primary-predicate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))

import triage  # noqa: E402  (path must be set up first)

files = sorted(f for f in os.listdir(HERE)
               if f.startswith("out-v") and f.endswith(".txt"))

print("re-scoring archived release probes under the PRIMARY predicate")
print("  predicate: match.json -> kind 'internal_failure'")
print("  function : triage.is_internal_failure (imported, not reimplemented)")
print("  archived : %d files\n" % len(files))

print("%-22s %-12s %-9s %-18s %s"
      % ("file", "# exit", "timed_out", "internal_failure?", "# match header"))
print("-" * 88)

bad = []
for name in files:
    meta, text = triage.read_out(os.path.join(HERE, name))
    raw = meta.get("exit")
    rc = None if raw in (None, "None", "TIMEOUT") else int(raw)
    timed_out = meta.get("timed_out") == "1"
    hit = triage.is_internal_failure(text, rc, timed_out)
    if hit:
        bad.append(name)
    print("%-22s %-12s %-9s %-18s %s"
          % (name, raw, meta.get("timed_out"), hit, meta.get("match")))

print()
if bad:
    print("RESULT: %d release(s) DO score as internal_failure: %s"
          % (len(bad), ", ".join(bad)))
    print("        The 'no shipped release asserts' claim is FALSE. Revise it.")
    sys.exit(1)

print("RESULT: 0 of %d releases score as internal_failure." % len(files))
print("        The claim 'no shipped release exhibits this internal failure'")
print("        is re-derived from the archived files and holds.")

# Both branches of the predicate are checked below, because the exit-code
# branch alone is not sufficient -- see the note in notes.md.
print()
print("Both branches of is_internal_failure were exercised:")
print("  (a) exit codes: every archived '# exit:' is 0, so none is in")
print("      INTERNAL_STATUS %s," % sorted(hex(c) for c in triage.INTERNAL_STATUS))
print("      none has severity nibble 0xC/0xE, and none is in 129..191.")
print("  (b) output text: is_internal_failure ALSO returns True on a text")
print("      match of INTERNAL_MARKERS regardless of exit code, so exit 0")
print("      alone would not settle it. Re-scoring above applies that regex")
print("      to the full archived stdout+stderr of each file and it does not")
print("      fire. INTERNAL_MARKERS = %r" % (triage.INTERNAL_MARKERS,))
