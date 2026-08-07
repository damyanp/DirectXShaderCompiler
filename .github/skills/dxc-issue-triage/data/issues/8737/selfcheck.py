"""By-hand completeness self-check for #8737.

Replaces the `triage.py reindex` audit, which the orchestrator withdrew for parallel
batches because its --reset default deletes other workers' in-flight database rows.
This script is READ-ONLY: it touches no database and nothing outside this directory.
"""
import json, os, re, sys

D = os.path.dirname(os.path.abspath(__file__))
ok, bad = [], []


def check(cond, msg):
    (ok if cond else bad).append(msg)


def has(name):
    return os.path.isfile(os.path.join(D, name))


def read(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return f.read()


print("by-hand completeness check for #8737")
print("=" * 70)

# --- 1. the deliverables the orchestrator listed -------------------------
for f in ("expected.md", "cmd.txt", "notes.md", "comment.md", "match.json"):
    check(has(f), "deliverable present: %s" % f)

repros = [f for f in os.listdir(D) if f.endswith(".hlsl")]
check(repros, "repro file(s) present: %d .hlsl" % len(repros))

# --- 2. cmd.txt names a repro that exists --------------------------------
cmd = [l.strip() for l in read("cmd.txt").splitlines()
       if l.strip() and not l.startswith("#")]
check(len(cmd) == 1, "cmd.txt is a single invocation: %r" % (cmd[0] if cmd else None))
named = [t for t in cmd[0].split() if t.endswith(".hlsl")]
check(named and has(named[0]),
      "cmd.txt names an existing repro: %s" % (named[0] if named else "NONE"))

# --- 3. every probe has a capture, and every capture agrees with cmd.txt --
outs = sorted(f for f in os.listdir(D) if f.startswith("out-") and f.endswith(".txt"))
variants = sorted(f for f in os.listdir(D)
                  if f.startswith("variant-") and f.endswith(".txt"))
check(outs, "cmd.txt probes captured: %d (out-*.txt)" % len(outs))
check(variants, "variant/control probes captured: %d (variant-*.txt)" % len(variants))

verdicts, stale, noexit = {}, [], []
for f in outs + variants:
    head = dict(re.findall(r"^# (\w+): (.*)$", read(f), re.M))
    if "exit" not in head:
        noexit.append(f)
        continue
    verdicts.setdefault(head.get("verdict", "?"), []).append(f)
    if f in outs and head.get("cmd") and head["cmd"] != cmd[0]:
        stale.append("%s captured %r" % (f, head["cmd"]))
check(not noexit, "every capture carries an exit code (%d checked)" % len(outs + variants))
check(not stale, "no capture is stale w.r.t. cmd.txt")
print("  capture verdicts: " +
      ", ".join("%s=%d" % (k, len(v)) for k, v in sorted(verdicts.items())))

# --- 4. compiler coverage: one capture per compiler probed ---------------
def compilers(files, prefix):
    return {f[len(prefix):-4] for f in files}


ice = compilers(outs, "out-")
ub = compilers([f for f in variants if f.startswith("variant-silent-ub-")],
               "variant-silent-ub-")
check("main-debug" in ice, "ground-truth compiler probed for the ICE")
check("main-debug" in ub, "ground-truth compiler probed for the silent case")
print("  ICE probed on %d compilers; silent case on %d" % (len(ice), len(ub)))
print("  silent case not probed on: " +
      (", ".join(sorted(ice - ub)) or "(nothing)") +
      "   <- expected: the pre-SM6.7 releases + n/a")

# --- 5. verdict.json is complete and self-consistent ---------------------
check(has("verdict.json"), "verdict.json present")
v = json.loads(read("verdict.json"))
for k in ("status", "repro_quality", "history", "confidence", "suggested_action",
          "summary", "notes_path", "triaged_with_commit", "triaged_by",
          "godbolt_url", "labels_now", "labels_add", "labels_remove", "title",
          "url", "batch"):
    check(v.get(k), "verdict.json has %s" % k)
check("reviewed_by" not in v,
      "verdict.json has NO reviewed_by (correct: step 10 is deferred to collation)")
check(has(os.path.basename(v.get("notes_path", ""))),
      "verdict.json notes_path resolves: %s" % v.get("notes_path"))

# --- 6. every claim-backing file notes.md references actually exists -----
notes = read("notes.md")
refd = sorted(set(re.findall(r"`((?:manual|variant|out|match|control|repro|"
                             r"const|msarray|expected|cmd|godbolt|verify)[\w.\-]*"
                             r"\.(?:txt|json|hlsl|md|py))`", notes)))
missing = [r for r in refd if not has(r)]
check(not missing, "every file notes.md cites exists (%d cited)" % len(refd))
if missing:
    print("  MISSING: " + ", ".join(missing))

# --- 7. hand measurements are backed --------------------------------------
for f in ("manual-ground-truth-version.txt", "manual-source-citations.txt",
          "manual-testsuite-search.txt", "manual-godbolt-verification.txt",
          "manual-godbolt-rejected-panes.txt"):
    check(has(f), "hand measurement captured: %s" % f)
check("eff900d54" in read("manual-ground-truth-version.txt"),
      "ground-truth capture shows the expected build (main, eff900d54)")
gv = read("manual-godbolt-verification.txt")
check("FAIL" not in gv, "no failing check in the CE verification capture")
check(gv.count("[exit] 0") == 3, "all 3 CE panes captured with exit 0")
check(v.get("godbolt_url", "") in gv, "CE capture is for the published link")

print("=" * 70)
for m in ok:
    print("  [PASS] " + m)
for m in bad:
    print("  [FAIL] " + m)
print("=" * 70)
print("%d passed, %d failed" % (len(ok), len(bad)))
sys.exit(1 if bad else 0)
