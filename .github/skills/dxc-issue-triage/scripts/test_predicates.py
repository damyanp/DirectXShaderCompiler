"""Unit tests for the symptom predicates.

    python scripts/test_predicates.py

These guard the two failure modes that produce wrong triage verdicts:

* treating an ordinary diagnosed error as a crash (invents bugs), and
* treating one signature of a defect as the whole symptom (invents fixes).

Both have happened. See SKILL.md step 4.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402

FAILURES = []


def check(desc, got, want):
    if got != want:
        FAILURES.append(f"{desc}: got {got!r}, want {want!r}")
        print(f"  FAIL  {desc}: got {got!r}, want {want!r}")
    else:
        print(f"  ok    {desc}")


def internal(desc, text, rc, want, timed_out=False):
    check(desc, triage.is_internal_failure(text, rc, timed_out), want)


def evaluate(spec, text="", rc=0, timed_out=False):
    return triage._eval_match(spec, text, rc, timed_out, "<test>")


print("is_internal_failure -- ordinary diagnosed errors are NOT crashes")
internal("success", "", 0, False)
internal("file not found", "dxc failed : cannot open file", 1, False)
internal("syntax error (E_FAIL)", "error: expected ';'", 0x80004005, False)
internal("invalid profile (E_FAIL)", "error: invalid profile ps_9_9", 0x80004005, False)
internal("validation failure (E_FAIL)",
         "error: validation errors\nAssignment of undefined values to UAV.",
         0x80004005, False)

print("is_internal_failure -- real internal failures")
internal("assert / breakpoint", "", 0x80000003, True)
internal("access violation", "", 0xC0000005, True)
internal("stack overflow", "", 0xC00000FD, True)
internal("STATUS_LLVM_ASSERT", "Internal compiler error: LLVM Assert", 0xE0000001, True)
internal("STATUS_LLVM_UNREACHABLE", "", 0xE0000002, True)
internal("STATUS_LLVM_FATAL", "", 0xE0000003, True)
internal("other 0xC structured exception", "", 0xC000001D, True)
internal("heap corruption", "", 0xC0000374, True)
internal("timeout counts as internal", "", 0, True, timed_out=True)

print("is_internal_failure -- POSIX signals (Compiler Explorer's Linux builds)")
internal("SIGSEGV", "Program terminated with signal: SIGSEGV", 139, True)
internal("SIGABRT", "", 134, True)
internal("exit 5 is not a signal", "", 5, False)

print("is_internal_failure -- text markers must be build-agnostic")
internal("windows llvm::cast spelling",
         "error: llvm::cast<X>() argument of incompatible type!", 0x80004005, True)
internal("linux cast spelling",
         "error: cast<X>() argument of incompatible type!", 0x80004005, True)
internal("stack dump", "Stack dump:\n0.\tProgram arguments:", 0, True)

print("any_of / all_of -- one defect, several signatures")
disj = {"kind": "any_of", "value": [{"kind": "timeout"},
                                    {"kind": "internal_failure"}]}
check("any_of matches the hang (release)", evaluate(disj, timed_out=True), True)
check("any_of matches the assert (debug)", evaluate(disj, rc=0xE0000001), True)
check("any_of rejects a clean compile", evaluate(disj, rc=0), False)
check("any_of rejects an ordinary error", evaluate(disj, "error: expected ';'",
                                                   rc=0x80004005), False)
conj = {"kind": "all_of", "value": [{"kind": "nonzero_exit"},
                                    {"kind": "contains", "value": "undef"}]}
check("all_of needs both", evaluate(conj, "undef", rc=1), True)
check("all_of rejects one", evaluate(conj, "clean", rc=1), False)

print("regex -- the #3009 shape must not match structurally-undef operands")
rx = {"kind": "regex",
      "value": r"@dx\.op\.(?:tertiary|binary|unary)\.[a-z0-9]+\(i32 \d+,"
               r"[^)]*\b(?:i32|float|half|double) undef"}
bug = "%11 = call i32 @dx.op.tertiary.i32(i32 48, i32 undef, i32 %6, i32 %10)"
benign_input = ("%2 = call i32 @dx.op.loadInput.i32"
                "(i32 4, i32 0, i32 0, i8 0, i32 undef)")
benign_store = ("call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1,"
                " i32 0, i32 0, i32 %11, i32 %13, i32 undef, i32 undef, i8 3)")
check("matches undef into arithmetic", evaluate(rx, bug), True)
check("ignores loadInput gsVertexAxis", evaluate(rx, benign_input), False)
check("ignores bufferStore coords", evaluate(rx, benign_store), False)
check("ignores both together (a correct shader)",
      evaluate(rx, benign_input + "\n" + benign_store), False)

print("invert")
check("invert flips the result",
      evaluate({"kind": "contains", "value": "x", "invert": True}, "y"), True)

print("malformed predicates fail loudly")
for spec in ({"kind": "contains"}, {"kind": "any_of"},
             {"kind": "any_of", "value": []}):
    try:
        evaluate(spec)
    except SystemExit:
        print(f"  ok    {spec.get('kind')} without usable value exits")
    else:
        FAILURES.append(f"{spec} should have exited")
        print(f"  FAIL  {spec} did not exit")

print("--repeat -- a nondeterministic symptom must not be decided by one run")
# Fakes a compiler that only fails on some runs, as #3768 does at v1.6.2104
# (68-82%). A single probe there calls a reproducing release clean about a
# quarter of the time, which during a linear scan invents a release boundary.
_real_execute = triage.execute


def fake_runs(verdicts):
    """Drive execute()'s repeat loop over a fixed sequence of single-run results."""
    seq = list(verdicts)
    calls = {"n": 0}

    def stub(issue, compiler, match_file="match.json", record=True, repeat=1):
        if repeat > 1:
            return _real_execute(issue, compiler, match_file, record, repeat)
        v = seq[min(calls["n"], len(seq) - 1)]
        calls["n"] += 1
        return {"compiler": compiler, "exit": 0 if v == "no-repro" else 1,
                "timed_out": False, "verdict": v, "output": "<stub>",
                "text": ""}
    return stub, calls


for desc, seq, repeat, want_verdict, want_calls in [
    ("finds the symptom hiding behind clean runs",
     ["no-repro", "no-repro", "repro"], 10, "repro", 3),
    ("stops at the first sighting",
     ["repro", "no-repro"], 10, "repro", 1),
    ("all-clean stays no-repro",
     ["no-repro"], 5, "no-repro", 5),
    ("invalid-probe outranks a clean run",
     ["no-repro", "invalid-probe"], 2, "invalid-probe", 2),
]:
    triage.execute = _real_execute
    stub, calls = fake_runs(seq)
    triage.execute = stub
    try:
        r = _real_execute(3768, "stub", "match.json", record=False,
                          repeat=repeat)
    finally:
        triage.execute = _real_execute
    check(desc, (r["verdict"], calls["n"]), (want_verdict, want_calls))

# --- absence-based predicate detection (batch 003, #1877 / #3038) -----------
# A predicate defined by something being MISSING is satisfied for free by any
# compile that never got far enough to emit it.
import json as _json, tempfile as _tf, os as _os, re as _re

_tmp = _tf.mkdtemp()
triage.issue_dir = lambda n: _tmp

def _write_pred(obj):
    with open(_os.path.join(_tmp, "match.json"), "w") as fh:
        _json.dump(obj, fh)

for desc, pred, want in [
    ("not_contains is absence-based", {"kind": "not_contains", "value": "fptosi"}, True),
    ("not_regex is absence-based", {"kind": "not_regex", "value": "fptosi"}, True),
    ("contains is not absence-based", {"kind": "contains", "value": "x"}, False),
    ("inverted contains IS absence-based",
     {"kind": "contains", "value": "x", "invert": True}, True),
    ("inverted not_contains is NOT absence-based",
     {"kind": "not_contains", "value": "x", "invert": True}, False),
    ("internal_failure is not absence-based", {"kind": "internal_failure"}, False),
    ("any_of containing an absence predicate counts",
     {"kind": "any_of", "value": [{"kind": "timeout"},
                                  {"kind": "not_contains", "value": "x"}]}, True),
    ("any_of with no absence predicate does not",
     {"kind": "any_of", "value": [{"kind": "timeout"},
                                  {"kind": "internal_failure"}]}, False),
]:
    _write_pred(pred)
    check(desc, triage._is_absence_predicate(1877), want)

# --- feature-absence diagnostics are invalid probes, not clean runs --------
# Measured on #3038: v1.4.1907 predates DXR 1.1 and answers "use of undeclared
# identifier 'RayQuery'". That is not evidence the bug was absent.
_unsupported_re = r"(?i)invalid profile|unsupported profile|unrecognized (?:argument|option)|unknown argument|is not supported|requires shader model|CodeGen not available|recompile with -D|use of undeclared identifier|unknown type name|no member named|no matching function for call to"

for desc, text, want in [
    ("undeclared identifier is an invalid probe",
     "error: use of undeclared identifier 'RayQuery'", True),
    ("unknown type name is an invalid probe",
     "error: unknown type name 'RayQuery'", True),
    ("no matching function is an invalid probe",
     "error: no matching function for call to 'TraceRayInline'", True),
    ("invalid profile still detected", "error: invalid profile ps_6_7", True),
    ("an ordinary syntax error is NOT an invalid probe",
     "error: expected ';' after expression", False),
    ("clean output is NOT an invalid probe", "; shader hash: abc", False),
]:
    check(desc, bool(_re.search(_unsupported_re, text)), want)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S)")
    sys.exit(1)
print("all predicate tests passed")



