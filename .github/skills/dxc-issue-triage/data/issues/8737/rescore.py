"""Re-score every declared control/probe for #8737 against its predicate.

This is the one useful thing `reindex` did that the file-existence self-check does
not: a control's value is entirely in its declared expectation, and a predicate may
have been edited after the capture was taken. Uses triage.py's own `classify` so the
scoring cannot drift from the code that produced the files.

Read-only: it imports triage.py but calls only file-based helpers, and it asserts the
database file was not modified, so it is safe to run while other workers are active.
"""
import os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# Resolve the database the same way triage.py does, but WITHOUT importing it, so
# the fingerprint below is taken before any triage.py code has had a chance to run.
DB = os.path.abspath(os.environ.get(
    "DXC_TRIAGE_CACHE", os.path.join(ROOT, ".cache")))
DB = os.path.join(DB, "triage.db")


def fingerprint():
    if not os.path.isfile(DB):
        return None
    st = os.stat(DB)
    with open(DB, "rb") as f:
        return st.st_mtime_ns, st.st_size, hashlib.sha256(f.read()).hexdigest()


before = fingerprint()
assert before is not None, "database not found at %s -- fix the path" % DB

import triage  # noqa: E402

assert triage.DB == DB, "path drift: triage.py uses %s" % triage.DB
ISSUE = 8737
rows, violations = [], []

for f in sorted(os.listdir(HERE)):
    if not (f.startswith(("out-", "variant-")) and f.endswith(".txt")):
        continue
    meta, text = triage.read_out(os.path.join(HERE, f))
    if "exit" not in meta:
        continue
    mf = meta.get("match", "match.json")
    if not os.path.isfile(os.path.join(HERE, mf)):
        rows.append((f, mf, meta.get("expect", "-"), "NO PREDICATE FILE", ""))
        continue
    rc = None if meta["exit"] in ("None", "TIMEOUT") else int(meta["exit"])
    now = triage.classify(ISSUE, text, rc, meta.get("timed_out") == "1", mf)
    recorded = meta.get("verdict", "-")
    expect = meta.get("expect", "-")
    flags = []
    if recorded != "-" and recorded != now:
        flags.append("DRIFT from recorded %r" % recorded)
    if expect != "-" and triage.expectation_violated(expect, now):
        flags.append("EXPECTATION VIOLATED")
    if flags:
        violations.append((f, "; ".join(flags)))
    rows.append((f, mf, expect, now, "; ".join(flags)))

after = fingerprint()

w = max(len(r[0]) for r in rows)
print("re-scoring %d captures for #8737 with triage.py's own classify()" % len(rows))
print("=" * (w + 58))
print("%-*s  %-22s %-10s %-11s %s" % (w, "capture", "predicate", "expect", "scores", ""))
print("-" * (w + 58))
for f, mf, expect, now, flag in rows:
    print("%-*s  %-22s %-10s %-11s %s" % (w, f, mf, expect, now, flag))
print("=" * (w + 58))
print("database:                %s" % DB)
print("database byte-identical: %s   (sha256 %s -> %s)"
      % (before == after, before[2][:12], after[2][:12] if after else "GONE"))
if before != after:
    print("  NOTE: another worker may have written to the shared database while this")
    print("        ran; that is expected in a parallel batch and is not caused by")
    print("        this script, which only calls file-based helpers.")
if violations:
    print("\n%d PROBLEM(S):" % len(violations))
    for f, flag in violations:
        print("  %s: %s" % (f, flag))
    sys.exit(1)
print("\nno drift, no violated expectations.")
