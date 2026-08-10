"""Unit tests for the symptom predicates.

    python scripts/test_predicates.py

These guard the two failure modes that produce wrong triage verdicts:

* treating an ordinary diagnosed error as a crash (invents bugs), and
* treating one signature of a defect as the whole symptom (invents fixes).

Both have happened. See SKILL.md step 4.
"""
import json
import os
import subprocess
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
internal("DXC_E_GENERAL_INTERNAL_ERROR without text", "", 0x80AA0018, True)
internal("DXC_E_LLVM_FATAL_ERROR without text", "", 0x80AA001B, True)
internal("DXC_E_LLVM_UNREACHABLE without text", "", 0x80AA001C, True)
internal("DXC_E_LLVM_CAST_ERROR without text", "", 0x80AA001D, True)
internal("DXC_E_OPTIMIZATION_FAILED is not assumed internal", "", 0x80AA0017, False)
internal("DXC_E_ABORT_COMPILATION_ERROR is not assumed internal", "", 0x80AA0019, False)
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

print("Compiler Explorer annotation")
_annotation_dir = tempfile.mkdtemp()
_old_issue_dir = triage.issue_dir
triage.issue_dir = lambda n: _annotation_dir
try:
    with open(os.path.join(_annotation_dir, "godbolt-note.txt"), "w",
              encoding="utf-8") as f:
        f.write("// already marked\nplain prose\n")
    annotated = triage.annotate(1, "float4 main() : SV_Target { return 0; }\n")
    check("annotation owns exactly one comment marker",
          "// already marked" in annotated and "// // already marked" not in annotated,
          True)
finally:
    triage.issue_dir = _old_issue_dir

check("fetch records the issue author",
      "author" in triage.ISSUE_FETCH_FIELDS.split(","), True)

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

    def stub(issue, compiler, match_file="match.json", record=True, repeat=1,
             shader=None, label=None, args=None, expect=None, force=False):
        if repeat > 1:
            return _real_execute(issue, compiler, match_file, record, repeat,
                                 shader, label, args, expect, force)
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

# An absence clause is satisfied for free by a compile that failed early, and
# `classify` only demotes such a probe when it also tripped a feature-absence
# marker or failed internally. An ORDINARY DIAGNOSED ERROR is neither -- on
# Windows, E_FAIL plus an `error:` line -- so an absence-only predicate scores
# it `repro`. Measured on #2792 against real captured output. The predicate
# cannot be demoted (that is #3055's defect in a new shape), so the runner
# warns; this is the test for what it warns about.
for desc, pred, want in [
    ("absence-only predicate has no positive clause",
     {"kind": "not_contains", "value": "fptosi"}, False),
    ("a contains clause anchors it",
     {"kind": "all_of", "value": [{"kind": "contains", "value": "extractvalue"},
                                  {"kind": "not_contains", "value": "cmp"}]}, True),
    ("a regex clause anchors it",
     {"kind": "all_of", "value": [{"kind": "regex", "value": "dx[.]op[.]"},
                                  {"kind": "not_regex", "value": "error:"}]}, True),
    ("internal_failure is a positive observation",
     {"kind": "any_of", "value": [{"kind": "internal_failure"},
                                  {"kind": "not_contains", "value": "x"}]}, True),
    ("timeout is a positive observation",
     {"kind": "any_of", "value": [{"kind": "timeout"},
                                  {"kind": "not_contains", "value": "x"}]}, True),
    # A rejected input exits nonzero too, so this anchors nothing.
    ("nonzero_exit does NOT anchor an absence predicate",
     {"kind": "all_of", "value": [{"kind": "nonzero_exit"},
                                  {"kind": "not_contains", "value": "x"}]}, False),
    ("an inverted contains does not anchor it either",
     {"kind": "all_of", "value": [{"kind": "contains", "value": "x",
                                   "invert": True},
                                  {"kind": "not_contains", "value": "y"}]}, False),
    ("an inverted not_contains is a positive clause",
     {"kind": "not_contains", "value": "x", "invert": True}, True),
]:
    _write_pred(pred)
    check(desc, triage._has_positive_clause(1877), want)

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

# --- controls (step 4/7): a control must differ from the repro in exactly one
# way, so retargeting may touch only the source operand.
for desc, line, want in [
    ("replaces the source file",
     "-T cs_6_5 -E main repro.hlsl", "-T cs_6_5 -E main control.hlsl"),
    ("leaves an -I path alone",
     "-I inc.hlsl repro.hlsl", "-I inc.hlsl control.hlsl"),
    ("leaves an -Fo target alone",
     "-Fo out.hlsl repro.hlsl", "-Fo out.hlsl control.hlsl"),
    ("replaces only the first source",
     "repro.hlsl extra.hlsl", "control.hlsl extra.hlsl"),
    ("a value-less flag does not shield the source",
     "-T cs_6_5 -Od repro.hlsl", "-T cs_6_5 -Od control.hlsl"),
]:
    check(desc, triage.retarget_cmd(line, "control.hlsl"), want)

try:
    triage.retarget_cmd("-T cs_6_5 -E main", "control.hlsl")
    check("refuses a command with no source", "no error", "SystemExit")
except SystemExit:
    check("refuses a command with no source", "SystemExit", "SystemExit")

# A control's expected result is the whole point of running it, and it runs in
# both directions: #3009's control must NOT match (a predicate firing on a
# correct shader cannot discriminate) while #1803's must (identical DXIL from
# a column_major declaration is what proves row_major is ignored).
for desc, expect, verdict, want in [
    ("negative control that stays clean is fine", "no-match", "no-repro", False),
    ("negative control that matches is a violation", "no-match", "repro", True),
    ("identity control that matches is fine", "match", "repro", False),
    ("identity control that stops matching is a violation", "match", "no-repro", True),
    ("no declared expectation cannot be violated", None, "repro", False),
    # An invalid probe is not a clean run: it is a run that never happened.
    # Measured on #8527, whose as-filed control was rejected for using cs_6_6
    # on a release that predates it and quietly satisfied `--expect no-match`,
    # so the reindex re-check that exists to catch exactly this said nothing.
    ("invalid probe does NOT satisfy no-match", "no-match", "invalid-probe", True),
    ("invalid probe does not satisfy match", "match", "invalid-probe", True),
    ("an expected invalid probe is fine", "invalid-probe", "invalid-probe", False),
    ("an expected invalid probe that compiles is a violation",
     "invalid-probe", "no-repro", True),
    ("an expected invalid probe that reproduces is a violation",
     "invalid-probe", "repro", True),
]:
    check(desc, triage.expectation_violated(expect, verdict), want)

# --- a probe is identified by its predicate, not just by its compiler ------
# Two predicates over the same release are two measurements. Deriving the
# filename from the compiler alone made the second overwrite the first;
# measured on #2191, which lost 20 of 21 primary-predicate captures.
for desc, args, want in [
    ("the default predicate keeps the bare name",
     ("d", "v1.8.2403", "match.json", None), "out-v1.8.2403.txt"),
    ("a second predicate gets its own slot",
     ("d", "v1.8.2403", "match-rejected.json", None),
     "out-v1.8.2403--match-rejected.txt"),
    ("labelled variants follow the same rule",
     ("d", "main-debug", "match.json", "scalar"),
     "variant-scalar-main-debug.txt"),
    ("a labelled variant under a second predicate cannot collide",
     ("d", "main-debug", "match-rejected.json", "scalar"),
     "variant-scalar-main-debug--match-rejected.txt"),
]:
    check(desc, _os.path.basename(triage.probe_path(*args)), want)

check("two predicates over one release cannot share a path",
      triage.probe_path("d", "v1.8.2403", "match.json") !=
      triage.probe_path("d", "v1.8.2403", "match-rejected.json"), True)

# --- a crashed probe measured nothing --------------------------------------
# Measured on #2202: v1.8.2403 access-violates on the repro. Scoring that as a
# clean run erases a defect at a release boundary someone will act on.
_write_pred({"kind": "contains", "value": "never appears in this text"})
for desc, text, rc, want in [
    ("an access violation is not a clean run", "", 0xC0000005, "invalid-probe"),
    ("an assert is not a clean run", "", 0xE0000001, "invalid-probe"),
    ("an ordinary clean compile still scores no-repro",
     "; shader hash: abc", 0, "no-repro"),
    ("an ordinary diagnostic still scores no-repro",
     "error: expected ';' after expression", 1, "no-repro"),
]:
    check(desc, triage.classify(1877, text, rc, False), want)

# The forward-in-time version of the feature-absence trap: a NEWER compiler
# rejecting an OLDER repro because the default language version moved.
check("today's -HV 2021 rejecting a 2019 repro is an invalid probe",
      triage.classify(1877, "error: for non-scalar types use 'select'", 1, False),
      "invalid-probe")

# A crash the predicate is looking FOR must still score as a reproduction --
# the guard above must not swallow the symptom it exists to find.
_write_pred({"kind": "internal_failure"})
check("a crash the predicate wants is still a reproduction",
      triage.classify(1877, "", 0xC0000005, False), "repro")

# --- the feature-absence markers must not eat DIAGNOSTIC symptoms ----------
#
# The markers are a proxy for "this build rejected the input before reaching
# the code under test". On an issue whose reported symptom IS a diagnostic the
# proxy and the symptom become the same observation, which batch 004 predicted
# and #3055 then measured in both directions. See triage._predicate_quotes.
_GOOD_DIAG = ("error: no matching function for call to 'clamp'\n"
              "note: candidate function not viable: no known conversion from "
              "'SamplerComparisonState' to 'vector<float, 1>' for 2nd argument")
_UNDECLARED = "error: use of undeclared identifier 'clamp'"

# Direction A. A release emitting the GOOD diagnostic the issue asks for scores
# no-repro -- that is what "fixed here" looks like -- and used to be demoted,
# so `bisect` trimmed away the very release that fixed it. The symptom is the
# rejection WITHOUT the note naming the bad argument, so the note's arrival is
# the fix.
_write_pred({"kind": "all_of", "value": [
    {"kind": "contains", "value": "no matching function for call to 'clamp'"},
    {"kind": "not_regex", "value": "no known conversion"}]})
check("a release emitting the diagnostic the issue asks for is a real no-repro",
      triage.classify(1877, _GOOD_DIAG, 0x80004005, False), "no-repro")

# ...but only because THIS issue's predicate quotes it. The same output under a
# predicate about something else is still a build that never ran the repro.
_write_pred({"kind": "contains", "value": "DXIL intrinsic overload must be valid"})
check("the same output under an unrelated predicate is still an invalid probe",
      triage.classify(1877, _GOOD_DIAG, 0x80004005, False), "invalid-probe")

# Direction B. A probe that MATCHES gets demoted when the predicate happens to
# carry any absence clause. Every release including ground truth would be
# discarded and `bisect` would report "no release could run this repro".
_write_pred({"kind": "all_of", "value": [
    {"kind": "contains", "value": "use of undeclared identifier 'clamp'"},
    {"kind": "not_regex", "value": "candidate function"}]})
check("a matching probe whose symptom IS the marker is a real reproduction",
      triage.classify(1877, _UNDECLARED, 0x80004005, False), "repro")

# The suppression is verbatim containment in a POSITIVE clause, and nothing
# looser. #3055's own primary predicate quotes the *member* spelling, which the
# marker is not a substring of, so it must not suppress anything.
_write_pred({"kind": "all_of", "value": [
    {"kind": "contains", "value": "no matching member function for call to 'Sample'"},
    {"kind": "not_regex", "value": "no known conversion"}]})
check("a near-miss quotation does not suppress the demotion",
      triage.classify(1877, _GOOD_DIAG, 0x80004005, False), "invalid-probe")

# "The symptom is that X is ABSENT" does not make X's presence a measurement.
_write_pred({"kind": "contains", "value": "use of undeclared identifier",
             "invert": True})
check("an inverted clause naming the marker does not suppress the demotion",
      triage.classify(1877, _UNDECLARED, 0x80004005, False), "invalid-probe")

# The fake-regression bug the markers exist to prevent must stay prevented. It
# has produced wrong verdicts twice; a more permissive classifier reintroduces
# it. #3873 (ps_6_7 did not exist yet) and #3038 (DXR 1.1 did not exist yet).
_write_pred({"kind": "any_of", "value": [{"kind": "timeout"},
                                         {"kind": "internal_failure"}]})
check("a release predating the profile is still an invalid probe",
      triage.classify(1877, "error: invalid profile ps_6_7", 1, False),
      "invalid-probe")
_write_pred({"kind": "internal_failure"})
check("a release predating the intrinsic is still an invalid probe",
      triage.classify(1877, "error: use of undeclared identifier 'RayQuery'",
                      1, False),
      "invalid-probe")
_write_pred({"kind": "not_contains", "value": "fptosi"})
check("an absence predicate satisfied by an early failure is still demoted",
      triage.classify(1877, "error: use of undeclared identifier 'RayQuery'",
                      1, False),
      "invalid-probe")

# --- "is not supported" has to name something the compiler does not HAVE ----
# DXC emits that phrase from ~25 diagnostics about present-day code, so
# unqualified it demoted ordinary errors. Noticed independently on #8732,
# whose PR #8517 branch emits one of them.
_write_pred({"kind": "contains", "value": "never appears in this text"})
for desc, text, want in [
    ("a bound/heap mixing diagnostic is an ordinary error",
     "error: mixing bound and descriptor heap resources in the same variable "
     "is not supported with SPV_EXT_descriptor_heap", "no-repro"),
    ("'operator is not supported' is an ordinary error",
     "error: operator is not supported", "no-repro"),
    ("'not supported on minimum-precision types' is an ordinary error",
     "error: signed integer division is not supported on minimum-precision "
     "types, cast to int to use 32-bit division", "no-repro"),
    ("'not supported for the current target' really is feature absence",
     "error: thread-local storage is not supported for the current target",
     "invalid-probe"),
    ("'not supported for this target' really is feature absence",
     "error: 'foo' attribute is not supported for this target",
     "invalid-probe"),
]:
    check(desc, triage.classify(1877, text, 1, False), want)

# --- an invalid-probe verdict has to say WHY, in the capture ---------------
# It is the one verdict that means "ignore this measurement", and `bisect`
# trims the release on the strength of it.
_v, _r = triage.classify(1877, "error: invalid profile ps_6_7", 1, False,
                         explain=True)
check("explain=True returns the verdict and a reason", _v, "invalid-probe")
check("the reason names the marker that fired",
      _r is not None and '"invalid profile"' in _r, True)
check("explain defaults off, so callers keep getting a bare verdict",
      isinstance(triage.classify(1877, "error: invalid profile ps_6_7", 1, False),
                 str), True)
check("a clean verdict carries no reason",
      triage.classify(1877, "; shader hash: abc", 0, False, explain=True),
      ("no-repro", None))

_reasoned = _os.path.join(_tmp, "out-reason-test.txt")
with open(_reasoned, "w", encoding="utf-8") as fh:
    fh.write("# compiler: v1.4.1907\n# exit: 1\n# match: match.json\n"
             "# verdict: invalid-probe\n\nthe measurement\n")
triage.stamp_reason(_reasoned, "because the marker fired")
_m, _t = triage.read_out(_reasoned)
check("the reason lands in the header, not the measurement",
      (_m["invalid-probe-reason"], _t.strip()),
      ("because the marker fired", "the measurement"))
triage.stamp_reason(_reasoned, "a different reason")
check("restamping replaces the reason rather than accumulating them",
      open(_reasoned, encoding="utf-8").read().count("# invalid-probe-reason:"), 1)
triage.stamp_reason(_reasoned, None)
check("a verdict that is no longer a demotion drops the reason",
      "invalid-probe-reason" in triage.read_out(_reasoned)[0], False)

# --- ce_args: most dxc flags take no value ---------------------------------
# Deciding "is this token a flag's value?" by "did the previous token start
# with a dash" kept the source file after every value-less flag, and handed CE
# a second, nonexistent input. Measured on #8732 (`... -spirv repro.hlsl`).
_ce = _tf.mkdtemp()
triage.issue_dir = lambda n: _ce
open(_os.path.join(_ce, "repro.hlsl"), "w").close()
open(_os.path.join(_ce, "forced.h"), "w").close()
for desc, line, want in [
    ("a value-less flag does not shield the source from being dropped",
     "-T cs_6_6 -E main -fspv-use-descriptor-heap -spirv repro.hlsl",
     "-T cs_6_6 -E main -fspv-use-descriptor-heap -spirv"),
    ("an ordinary positional source is still dropped",
     "-T ps_6_0 -E main repro.hlsl", "-T ps_6_0 -E main"),
    ("a flag's file VALUE is still kept",
     "-T ps_6_0 -include forced.h repro.hlsl", "-T ps_6_0 -include forced.h"),
]:
    with open(_os.path.join(_ce, "cmd.txt"), "w") as fh:
        fh.write(line + "\n")
    check(desc, triage.ce_args(0)[0], want)
triage.issue_dir = lambda n: _tmp
_write_pred({"kind": "contains", "value": "never appears in this text"})

# --- a capture is never silently overwritten by a different predicate ------
# The reason #2191 lost 20 of 21 primary probes. probe_path() now separates
# them, but a --force or a renamed predicate could still land on an existing
# file, so the writer refuses rather than trusting the path scheme alone.
_stale = _os.path.join(_tmp, "out-v1.4.1907.txt")
with open(_stale, "w") as fh:
    fh.write("# compiler: v1.4.1907\n# exit: 0\n# match: match-rejected.json\n"
             "# verdict: no-repro\n\nolder measurement\n")
try:
    triage.execute(1877, "v1.4.1907", "match.json", record=True)
    check("refuses to overwrite a capture scored by another predicate",
          "no error", "SystemExit")
except SystemExit as e:
    check("refuses to overwrite a capture scored by another predicate",
          "--label" in str(e) and "--force" in str(e), True)
except Exception:
    check("refuses to overwrite a capture scored by another predicate",
          "wrong exception", "SystemExit")

# `# verdict:` is derived, so restamping it must move that line and no other.
check("restamp moves only the named field",
      triage.restamp(_stale, "verdict", "invalid-probe"), True)
_m, _t = triage.read_out(_stale)
check("restamp leaves the measurement alone",
      (_m["verdict"], _m["exit"], _m["match"], _t.strip()),
      ("invalid-probe", "0", "match-rejected.json", "older measurement"))
check("restamp reports an absent field rather than inventing one",
      triage.restamp(_stale, "expect", "no-match"), False)

# The bisect stub stands in for execute(); if their signatures drift, the stub
# silently stops modelling the thing under test.
import inspect as _inspect
check("bisect stub mirrors execute()'s signature",
      str(_inspect.signature(fake_runs([])[0])),
      str(_inspect.signature(triage.execute)))


# --- cmd.txt is a Windows command line, not a POSIX one --------------------
# `shlex.split` is POSIX-mode, where `\` escapes the next character. Every DXC
# path on Windows is spelled with it, so `-I inc\sub` silently became
# `-I incsub` -- a probe that compiled the wrong thing and still looked fine in
# the capture. Quoting must keep working; only the escape is disabled.
for desc, line, want in [
    ("a backslash path separator survives the split",
     r"-T ps_6_0 -I inc\sub repro.hlsl",
     ["-T", "ps_6_0", "-I", r"inc\sub", "repro.hlsl"]),
    ("a rooted Windows path survives the split",
     r"-Fo C:\out\a.dxo repro.hlsl",
     ["-Fo", r"C:\out\a.dxo", "repro.hlsl"]),
    ("quoting still groups a spaced filename",
     '-T ps_6_0 "my repro.hlsl"',
     ["-T", "ps_6_0", "my repro.hlsl"]),
    ("an ordinary line is unchanged",
     "-T ps_6_0 -E main -Od repro.hlsl",
     ["-T", "ps_6_0", "-E", "main", "-Od", "repro.hlsl"]),
]:
    check(desc, triage.split_cmd(line), want)

# --- an unknown option can be a legacy spelling, not a missing feature -----
check("extracts the rejected option from an Unknown argument diagnostic",
      triage.unknown_argument_token(
          "dxc failed : Unknown argument: '-pack-optimized'"),
      "-pack-optimized")
_spellings = triage.argument_spelling_variants("-pack-optimized")
check("tries the underscore spelling before changing prefix",
      _spellings[0], "-pack_optimized")
check("also tries the slash spelling",
      "/pack-optimized" in _spellings, True)
_rewritten = triage.replace_argument_spelling(
    ["-T ds_6_0 -pack-optimized repro.hlsl",
     "-T ps_6_0 -pack-optimized repro.hlsl"],
    "-pack-optimized", "-pack_optimized")
check("rewrites the rejected flag in every invocation",
      [triage.split_cmd(line)[2] for line in _rewritten],
      ["-pack_optimized", "-pack_optimized"])

# `bisect` may vary dxc itself, never an API/pass harness that happens to be
# registered as a compiler. That substitution has produced the inverse result
# repeatedly because every release dxc scored a plausible no-repro.
check("recognises dxc.exe as a real driver",
      triage.is_dxc_binary(r"C:\build\Debug\bin\dxc.exe"), True)
check("recognises a harness as not dxc",
      triage.is_dxc_binary(r"C:\triage\run-reflection.cmd"), False)
_old_gt, _old_con = triage.ground_truth_compiler, triage.con


class _OneRow:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _HarnessDb:
    def execute(self, *_args):
        return _OneRow({"exe_path": r"C:\triage\run-reflection.cmd"})


try:
    triage.ground_truth_compiler = lambda _issue: "main-debug-reflection"
    triage.con = lambda: _HarnessDb()
    try:
        triage.refuse_harness_bisect(2952)
    except SystemExit as e:
        check("bisect hard-errors on a harness compiler",
              "refusing to bisect" in str(e) and "explicit release matrix" in str(e),
              True)
    else:
        check("bisect hard-errors on a harness compiler", "no error", "SystemExit")
finally:
    triage.ground_truth_compiler, triage.con = _old_gt, _old_con

_excluded = [
    {"tag": "v1.2.0-alpha", "build_date": None, "asset_name": None,
     "prerelease": 1, "bisectable": 0},
    {"tag": "v1.5.2003", "build_date": "2020-03-25", "asset_name": "dxc.zip",
     "prerelease": 1, "bisectable": 0},
]
check("catalog exclusions distinguish missing assets from prereleases",
      triage.release_exclusion_groups(_excluded),
      {"no usable dxc asset": ["v1.2.0-alpha"],
       "prerelease": ["v1.5.2003"]})
check("bisect states which prerelease it skipped and why",
      triage.release_exclusion_messages([_excluded[1]]),
      ["skipped 1 prerelease from search by policy: v1.5.2003"])
_stable = {"tag": "v1.5.2010", "build_date": "2020-10-22",
           "asset_name": "dxc.zip", "prerelease": 0, "bisectable": 1}
_included, _still_excluded, _named = triage.split_release_search_rows(
    _excluded + [_stable], {"title": "ordinary bug", "body": "no build named"})
check("prereleases stay outside the stable-release search by policy",
      [r["tag"] for r in _included], ["v1.5.2010"])
check("excluded prereleases remain visible for reporting",
      [r["tag"] for r in _still_excluded],
      ["v1.2.0-alpha", "v1.5.2003"])
_included, _still_excluded, _named = triage.split_release_search_rows(
    _excluded + [_stable],
    {"title": "regression in v1.5.2003", "body": "tested that prerelease"})
check("naming a prerelease does not silently opt it into the search",
      [r["tag"] for r in _included], ["v1.5.2010"])
_included, _still_excluded, _named = triage.split_release_search_rows(
    _excluded + [_stable],
    {"title": "regression in v1.5.2003", "body": "tested that prerelease"},
    ["v1.5.2003"])
check("an explicitly opted-in and named usable prerelease enters the search",
      [r["tag"] for r in _included], ["v1.5.2003", "v1.5.2010"])
check("the persistent prerelease carve-out is reported",
      _named, ["v1.5.2003"])
try:
    triage.split_release_search_rows(
        _excluded + [_stable],
        {"title": "ordinary bug", "body": "no build named"},
        ["v1.5.2003"])
except SystemExit as e:
    check("an opt-in is rejected unless the issue explicitly names the prerelease",
          "do not explicitly name" in str(e), True)
else:
    check("an opt-in is rejected unless the issue explicitly names the prerelease",
          "no error", "SystemExit")
check("a longer release name does not accidentally name its prefix",
      triage.issue_filing_names_release(
          {"title": "regression in v1.5.2003.1", "body": ""}, "v1.5.2003"),
      False)
check("an issue may explicitly name a release without the v prefix",
      triage.issue_filing_names_release(
          {"title": "regression in 1.5.2003", "body": ""}, "v1.5.2003"),
      True)
_policy_dir = _tf.mkdtemp()
_old_issue_dir = triage.issue_dir
triage.issue_dir = lambda _n: _policy_dir
try:
    check("no release-policy artifact means no prerelease opt-ins",
          triage.prerelease_opt_ins(1), [])
    with open(_os.path.join(_policy_dir, "release-policy.json"), "w") as f:
        _json.dump(["v1.5.2003"], f)
    try:
        triage.prerelease_opt_ins(1)
    except SystemExit as e:
        check("release-policy.json must be a JSON object",
              "must be a JSON object" in str(e), True)
    else:
        check("release-policy.json must be a JSON object",
              "no error", "SystemExit")
    with open(_os.path.join(_policy_dir, "release-policy.json"), "w") as f:
        _json.dump({"include_prereleases": ["v1.5.2003"]}, f)
    check("release-policy.json makes the exception persistent and visible",
          triage.prerelease_opt_ins(1), ["v1.5.2003"])
finally:
    triage.issue_dir = _old_issue_dir

# --- `run` must not pick a compiler for you --------------------------------
# Measured on #2923: the symptom lives in a PIX pass `dxc.exe` never runs, so
# the issue is registered against a harness compiler. `run` with no --compiler
# fell back to `main-debug`, scored a plausible `no-repro`, and contradicted the
# repro rows already on disk. The existing captures name the right answer.
_gt = _tf.mkdtemp()
triage.issue_dir = lambda n: _gt
check("no captures means no opinion", triage.ground_truth_compiler(1), None)
open(_os.path.join(_gt, "out-main-debug-pix.txt"), "w").close()
open(_os.path.join(_gt, "out-v1.6.2104.txt"), "w").close()
check("release captures do not count as a ground-truth compiler",
      triage.ground_truth_compiler(1), "main-debug-pix")
open(_os.path.join(_gt, "out-main-debug.txt"), "w").close()
check("two candidates means no opinion, so the default stands",
      triage.ground_truth_compiler(1), None)
triage.issue_dir = lambda n: _tmp


# --- the overview staleness gate -------------------------------------------
#
# `reports/overview.md` is generated, so the only way it goes wrong is by not
# being regenerated after a batch. `audit_overview` is what catches that, and a
# guard that never fires is worse than none -- it reads as reassurance. These
# drive it through all three states against a temporary tree.
def _overview_state(tmp, overview_age=None, with_verdict=True):
    """Run audit_overview() against a throwaway ISSUES/REPORTS pair."""
    issues, reports = os.path.join(tmp, "issues"), os.path.join(tmp, "reports")
    os.makedirs(os.path.join(issues, "1234"), exist_ok=True)
    os.makedirs(reports, exist_ok=True)
    vpath = os.path.join(issues, "1234", "verdict.json")
    if with_verdict:
        with open(vpath, "w", encoding="utf-8") as f:
            json.dump({"number": 1234}, f)
    opath = os.path.join(reports, "overview.md")
    if overview_age is not None:
        with open(opath, "w", encoding="utf-8") as f:
            f.write("# overview\n")
        # Negative age == older than the verdict; positive == newer.
        os.utime(opath, (os.path.getmtime(vpath) + overview_age,) * 2)
    old = triage.ISSUES, triage.REPORTS
    triage.ISSUES, triage.REPORTS = issues, reports
    try:
        return triage.audit_overview()
    finally:
        triage.ISSUES, triage.REPORTS = old


with tempfile.TemporaryDirectory() as _t:
    check("a missing overview is reported",
          _overview_state(os.path.join(_t, "a")), 1)
    check("an overview older than a verdict is reported",
          _overview_state(os.path.join(_t, "b"), overview_age=-10), 1)
    check("an overview newer than every verdict is accepted",
          _overview_state(os.path.join(_t, "c"), overview_age=+10), 0)
    check("no verdicts means nothing to be stale against",
          _overview_state(os.path.join(_t, "d"), with_verdict=False), 0)

print("committable path gate")
_path_check = subprocess.run(
    [sys.executable, os.path.join(os.path.dirname(__file__), "check_paths.py")],
    capture_output=True, text=True)
if _path_check.stdout.strip():
    print(f"  {_path_check.stdout.strip()}")
if _path_check.returncode and _path_check.stderr.strip():
    print(_path_check.stderr.rstrip())
check("no unexpected checkout or user-profile paths",
      _path_check.returncode, 0)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S)")
    sys.exit(1)
print("all predicate tests passed")
