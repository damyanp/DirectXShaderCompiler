#!/usr/bin/env python3
"""Tooling for evidence-backed, report-only DXC open-issue triage.

Answers, per issue: is there a usable repro, does it still reproduce against a
current build, and which release fixed it or introduced it.

Committed evidence defaults to `<skill>/data`; machine-local release binaries
and the derived SQLite index default to `<skill>/.cache`. Override with
DXC_TRIAGE_ROOT and DXC_TRIAGE_CACHE. The index is derived, not authoritative:
disk is truth, and `reindex` rebuilds it by re-scoring every archived capture
with today's predicate code, so a long pass can be stopped and resumed.

  triage.py init
  triage.py catalog
  triage.py compiler --id main-debug --exe <path/to/dxc>
  triage.py fetch    --issue 1768
  triage.py expect   --issue 1768
  triage.py run      --issue 1768 [--compiler main-debug] [--match match.json]
                                  [--repeat N] [--shader X --label Y --expect E]
  triage.py bisect   --issue 1768 [--match match.json] [--linear] [--repeat N]
  triage.py godbolt  --issue 1768 [--compilers ...] [--skip "reason"]
  triage.py labels   [--refresh] [--issue 1768]
  triage.py verdict  --issue 1768 --status repros --repro-quality complete ...
  triage.py reindex
  triage.py audit    [--issue 1768] [--collated]
  triage.py status
  triage.py sql "SELECT ..."

`reindex` rewrites shared state and is unsafe to run while per-issue workers
are live; it belongs to the collation phase.

This tool is read-only with respect to GitHub: it only ever runs `gh issue
view`, `gh release list/view/download`. It never edits, labels, comments on or
closes an issue.
"""

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
REPO = "microsoft/DirectXShaderCompiler"

# Two roots, deliberately separate.
#
#   ROOT       triage artifacts -- repros, captured output, notes, verdicts.
#              Committed: they are the evidence, and a verdict nobody can
#              re-check is just an assertion.
#   CACHE_ROOT downloaded release compilers and the SQLite index. Local-only
#              and .gitignore'd: 1.2 GB of third-party binaries does not belong
#              in a source tree, and the database is *derived* -- `reindex`
#              rebuilds it from ROOT -- so it is a cache, not a source of truth.
#
# Both default to living beside this script's skill, so the tool works from a
# fresh clone with no configuration.
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))
ROOT = os.path.abspath(os.environ.get(
    "DXC_TRIAGE_ROOT", os.path.join(SKILL_DIR, "data")))
CACHE_ROOT = os.path.abspath(os.environ.get(
    "DXC_TRIAGE_CACHE", os.path.join(SKILL_DIR, ".cache")))
DB = os.path.join(CACHE_ROOT, "triage.db")
ISSUES = os.path.join(ROOT, "issues")
CACHE = os.path.join(CACHE_ROOT, "compilers", "releases")
REPORTS = os.path.join(ROOT, "reports")
TIMEOUT = 60  # seconds; hangs are a real DXC failure mode
EXE = "dxc.exe" if os.name == "nt" else "dxc"

SCHEMA = """
CREATE TABLE IF NOT EXISTS issues (
    number              INTEGER PRIMARY KEY,
    title               TEXT,
    url                 TEXT,
    created_at          TEXT,
    labels              TEXT,
    batch               TEXT,
    repro_quality       TEXT,   -- complete|partial|prose-only|none|agent-constructed
    status              TEXT,   -- repros|does-not-repro|changed-behavior|
                                -- not-compiler-verifiable|inconclusive
    history             TEXT,   -- always-repro'd|fixed|regressed|unknown
    fixed_in            TEXT,
    regressed_in        TEXT,
    suggested_action    TEXT,
    confidence          TEXT,   -- high|medium|low
    summary             TEXT,
    expected_symptom    TEXT,
    notes_path          TEXT,
    triaged_at          TEXT,
    triaged_with_commit TEXT,
    godbolt_url         TEXT,
    godbolt_skip        TEXT,  -- why a link is deliberately absent
    labels_now          TEXT,  -- labels observed at triage time
    labels_add          TEXT,  -- proposed additions (validated, never applied)
    labels_remove       TEXT   -- proposed removals (validated, never applied)
);
CREATE TABLE IF NOT EXISTS labels (
    name        TEXT PRIMARY KEY,
    description TEXT,
    fetched_at  TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_number  INTEGER NOT NULL,
    compiler      TEXT NOT NULL,
    cmd           TEXT NOT NULL,
    exit_code     INTEGER,
    timed_out     INTEGER DEFAULT 0,
    output_path   TEXT,
    verdict       TEXT,
    note          TEXT,
    ran_at        TEXT
);
CREATE TABLE IF NOT EXISTS releases (
    tag           TEXT PRIMARY KEY,
    published_at  TEXT,
    build_date    TEXT,
    asset_name    TEXT,
    bisectable    INTEGER DEFAULT 1,
    prerelease    INTEGER DEFAULT 0,
    cached_path   TEXT
);
CREATE TABLE IF NOT EXISTS compilers (
    id            TEXT PRIMARY KEY,
    exe_path      TEXT,
    git_commit    TEXT,
    version       TEXT,
    built_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_issue ON runs(issue_number);
"""

ISSUE_FIELDS = [
    "title", "url", "created_at", "labels", "batch", "repro_quality", "status",
    "history", "fixed_in", "regressed_in", "suggested_action", "confidence",
    "summary", "expected_symptom", "notes_path", "triaged_at",
    "triaged_with_commit", "godbolt_url", "godbolt_skip",
    "labels_now", "labels_add", "labels_remove",
    # Provenance. `triaged_with_commit` says which compiler was measured;
    # these say who did the measuring and who checked the write-up. A verdict
    # is read differently depending on which model produced it, and step 10's
    # independent review is unverifiable if nothing records that it happened.
    "triaged_by", "reviewed_by",
    # Set when the issue's own title or body no longer describes what the
    # compiler does. The batch reports call these the highest-value findings,
    # because anyone spot-checking the issue against its description wrongly
    # concludes "cannot reproduce" while the defect is real. Free text: say
    # what is stale, so the overview can quote it rather than just flag it.
    "text_stale",
]

# Columns added after the first release of this script. Applied on connect so
# that workspaces created by an older version keep working.
MIGRATIONS = {"issues": {
    "godbolt_url": "TEXT", "godbolt_skip": "TEXT", "labels_now": "TEXT",
    "labels_add": "TEXT", "labels_remove": "TEXT",
    "triaged_by": "TEXT", "reviewed_by": "TEXT", "text_stale": "TEXT",
}}


_READY = False


def con():
    global _READY
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=60)
    c.row_factory = sqlite3.Row
    # Parallel per-issue sessions all write here. WAL lets readers proceed
    # while a writer commits, and the long busy timeout turns contention into
    # a short wait rather than a `database is locked` failure part-way through
    # an expensive bisection.
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=60000")
    if not _READY:
        # Applied once per process, and idempotent: CREATE TABLE IF NOT EXISTS
        # picks up tables added since the workspace was created, the ALTERs
        # pick up new columns. Together they let an old workspace keep working
        # after this script is updated.
        c.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            for name, decl in cols.items():
                if name not in have:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
        c.commit()
        _READY = True
    return c


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def issue_dir(n):
    return os.path.join(ISSUES, f"{n:04d}")


def _prefix_pattern(base):
    """Match one local root however it is spelled inside captured output."""
    parts = [p for p in re.split(r"[\\/]+", os.path.abspath(base)) if p]
    if not parts:
        return None
    return re.compile(r"[\\/]+".join(re.escape(p) for p in parts),
                      re.IGNORECASE)


def redact_paths(text):
    """Tokenise local directory prefixes appearing *inside* captured output.

    Same rationale as `display_exe`, one level deeper. A Debug build bakes
    `__FILE__` into `llvm_unreachable` and `DXASSERT` messages, so a crash
    capture reproduces the triaging machine's checkout layout verbatim -- and
    those captures are committed. The informative part is the path *within* the
    tree (which file asserted), so keep that and tokenise the prefix.

    Both separators and repeated separators are matched, so a JSON-escaped
    spelling is caught as well as a raw one. Applied before scoring as well as
    before writing, so a predicate matches exactly what a reader sees in the
    file; no predicate may key on a machine path, which is what makes that
    safe.

    This is normalisation, not redaction of evidence: nothing that carries
    information about the compiler's behaviour is removed. Hand-editing a
    capture after the fact is a different act entirely, and is falsification.
    """
    for base, token in ((CACHE_ROOT, "<cache>"), (ROOT, "<triage>"),
                        (REPO_ROOT, "<repo>")):
        if not base:
            continue
        pattern = _prefix_pattern(base)
        if pattern is not None:
            text = pattern.sub(token, text)
    return text


def display_exe(path):
    """Machine-independent spelling of a compiler path, for captured output.

    Run outputs are committed, so an absolute path bakes one contributor's
    directory layout into the repo and makes every diff machine-specific. The
    part that carries information is the tail -- which release, which flavour,
    Debug or Release -- so keep that and tokenise the prefix. Separators are
    normalised too, so a Windows and a Linux run of the same probe produce
    byte-identical provenance lines.
    """
    p = os.path.abspath(path)
    for base, token in ((CACHE_ROOT, "<cache>"), (ROOT, "<triage>"),
                        (REPO_ROOT, "<repo>")):
        try:
            rel = os.path.relpath(p, base)
        except ValueError:      # different drive on Windows
            continue
        if not rel.startswith(os.pardir):
            return f"{token}/" + rel.replace(os.sep, "/")
    return p.replace(os.sep, "/")


def read_out(path):
    """Split a captured run file into its `# key: value` header and body.

    The body is reconstructed exactly as `execute` had it, so a predicate
    re-evaluated here sees the same text the live run did.
    """
    meta, body = {}, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not body and line.startswith("# ") and ":" in line:
                k, _, v = line[2:].partition(":")
                meta[k.strip()] = v.strip()
                continue
            body.append(line)
    return meta, "".join(body).lstrip("\n")


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True,
                                   encoding="utf-8", errors="replace",
                                   shell=(os.name == "nt"))


# --------------------------------------------------------------------------
# symptom predicates
# --------------------------------------------------------------------------

INTERNAL_MARKERS = (
    # Keep these build-agnostic. The same failure is worded differently across
    # platforms and configurations -- Windows Release says "llvm::cast<X>()",
    # the Linux build used by Compiler Explorer says plain "cast<X>()" -- so
    # anchoring on one spelling silently misses the other and yields a false
    # "does not reproduce".
    r"(?i)internal compiler error|Terminal Error|Stack dump|Assertion failed|"
    r"UNREACHABLE executed|Error: assert\(|terminated with signal|"
    r"PLEASE submit a bug report|(?:llvm::)?cast<[^>]*>\(\) argument")


# Exit codes that mean dxc did not fail cleanly. These come from DXC's defined
# internal HRESULTs and top-level exception handling, not from the broad shape
# "nonzero": ordinary diagnosed errors also fail and must stay excluded.
INTERNAL_STATUS = frozenset((
    0xC0000005,  # EXCEPTION_ACCESS_VIOLATION
    0xC00000FD,  # EXCEPTION_STACK_OVERFLOW
    0x80000003,  # breakpoint -- an assert firing with no debugger attached
    0x80AA0018,  # DXC_E_GENERAL_INTERNAL_ERROR
    0x80AA001B,  # DXC_E_LLVM_FATAL_ERROR
    0x80AA001C,  # DXC_E_LLVM_UNREACHABLE
    0x80AA001D,  # DXC_E_LLVM_CAST_ERROR
    0xE0000001,  # STATUS_LLVM_ASSERT
    0xE0000002,  # STATUS_LLVM_UNREACHABLE
    0xE0000003,  # STATUS_LLVM_FATAL
))

# Deliberately excluded: DXC_E_OPTIMIZATION_FAILED (0x80AA0017) is emitted by
# DXIL conversion cleanup checks, but the source does not establish that bad
# input can never reach them; DXC_E_ABORT_COMPILATION_ERROR (0x80AA0019) has no
# emitter in this tree. Classifying either code alone as a crash could invent a
# bug, so they need a captured failure or stronger emitter proof first.

# dxc returns E_FAIL for ORDINARY diagnosed errors on Windows -- a plain syntax
# error, an invalid target profile and a DXIL validation failure all exit with
# this. It must never be read as a crash.
E_FAIL = 0x80004005


def is_internal_failure(text, rc, timed_out):
    """True when dxc failed in a way that is not a clean user-facing diagnostic.

    Judged by exit code rather than message text, because the *same* bug
    surfaces differently across builds: an assert-enabled Debug build traps
    (0x80000003), while shipping Release builds have asserts compiled out and
    may instead access-violate (0xC0000005) or return E_FAIL with a stray
    llvm::cast message. Text-only matching reports those releases as "does not
    reproduce", which is a false "fixed" verdict.

    Do NOT simplify this to "anything that is not 0 or 1". On Windows dxc
    returns E_FAIL (0x80004005) for ordinary compile errors -- verified against
    a bare syntax error, an invalid profile and a DXIL validation failure --
    so that rule reports essentially every failing compile as a crash. The
    inverse false verdict, and the more dangerous one, since it invents bugs.
    """
    if timed_out:
        return True
    if rc is not None:
        code = rc & 0xFFFFFFFF
        if code in INTERNAL_STATUS:
            return True
        # Any other Windows structured exception: severity 0xC (error) or
        # 0xE (customer-defined, which is what LLVM's status codes use).
        # dxc prints "Terminal Error 0x..." for these.
        if code != E_FAIL and (code >> 28) in (0xC, 0xE):
            return True
        # POSIX: killed by a signal, e.g. 139 = SIGSEGV, 134 = SIGABRT.
        # This is how a crash shows up on Compiler Explorer's Linux builds.
        if 128 < code < 192:
            return True
    return re.search(INTERNAL_MARKERS, text) is not None


def matches(issue, text, rc, timed_out, match_file="match.json"):
    path = os.path.join(issue_dir(issue), match_file)
    with open(path) as f:
        m = json.load(f)
    return _eval_match(m, text, rc, timed_out, path)


def _is_absence_predicate(issue, match_file="match.json"):
    """True if the symptom is defined by something being ABSENT from the output.

    Such a predicate is satisfied for free by any compile that failed before it
    could emit the thing being looked for, so a probe that matches one is only
    trustworthy if the compiler actually got that far. See #1877.
    """
    path = os.path.join(issue_dir(issue), match_file)
    try:
        with open(path) as f:
            m = json.load(f)
    except (OSError, ValueError):
        return False

    def walk(node):
        if not isinstance(node, dict):
            return False
        kind = node.get("kind")
        if kind in ("any_of", "all_of"):
            return any(walk(s) for s in node.get("value") or [])
        if kind in ("not_contains", "not_regex"):
            return not node.get("invert", False)
        if kind in ("contains", "regex"):
            return bool(node.get("invert", False))
        return False

    return walk(m)


def _has_positive_clause(issue, match_file="match.json"):
    """True if the predicate contains a clause a failed compile cannot satisfy.

    The companion to `_is_absence_predicate`. An absence clause is satisfied for
    free by any run that never got far enough to emit the thing being looked
    for, and `classify`'s guard only demotes such a probe when the output
    carried a feature-absence marker or the run failed internally. **An
    ordinary diagnosed error is neither** -- on Windows that is E_FAIL
    (0x80004005) plus an `error:` line, which is by far the likeliest early
    failure across a 20-release history -- so it still scores as a textbook
    reproduction. Demonstrated on #2792 against real captured output: a probe
    with three `error:` lines and no DXIL scored `repro` under an unanchored
    absence predicate.

    Demoting that case is not available: an issue whose symptom is "the
    diagnostic exists but says the wrong thing" legitimately errors on every
    reproducing probe, and demoting it would be the #3055 defect in a new
    shape. What is available is to say so at capture time, so the predicate can
    be anchored before twenty releases are run against it. #2792 did anchor its
    predicate -- `extractvalue %dx.types.CBufRet.f32 <v>, 1` cannot be emitted
    by a compile that failed -- and that anchor, not the classifier, is what
    made the issue safe.
    """
    path = os.path.join(issue_dir(issue), match_file)
    try:
        with open(path) as f:
            m = json.load(f)
    except (OSError, ValueError):
        return False

    def walk(node):
        if not isinstance(node, dict):
            return False
        kind = node.get("kind")
        if kind in ("any_of", "all_of"):
            return any(walk(s) for s in node.get("value") or [])
        inverted = bool(node.get("invert", False))
        # `contains`/`regex` uninverted assert output the compiler had to reach
        # the code under test to produce. `internal_failure` and `timeout` are
        # positive observations of a failure mode. `nonzero_exit` is NOT: an
        # input rejected at parse exits nonzero too, which is the very failure
        # this is guarding against.
        if kind in ("contains", "regex", "internal_failure", "timeout"):
            return not inverted
        if kind in ("not_contains", "not_regex"):
            return inverted
        return False

    return walk(m)


def predicate_clause_signature(issue, text, rc, timed_out,
                               match_file="match.json"):
    """Return leaf results plus whether any positive observation succeeded.

    Spelling re-probes need evidence that an alternate spelling was honoured,
    not merely tolerated. Comparing the predicate's leaf results with the same
    command minus that option ties acceptance to the output the issue actually
    cares about and avoids trusting a silently ignored `/` option.
    """
    path = os.path.join(issue_dir(issue), match_file)
    try:
        with open(path, encoding="utf-8") as f:
            root = json.load(f)
    except (OSError, ValueError):
        return (), False

    results = []
    positive_hits = []

    def walk(node):
        kind = node.get("kind") if isinstance(node, dict) else None
        if kind in ("any_of", "all_of"):
            for sub in node.get("value") or []:
                walk(sub)
            return
        hit = _eval_match(node, text, rc, timed_out, path)
        results.append(bool(hit))
        inverted = bool(node.get("invert", False))
        positive = (
            (kind in ("contains", "regex", "internal_failure", "timeout")
             and not inverted)
            or (kind in ("not_contains", "not_regex") and inverted)
        )
        positive_hits.append(positive and bool(hit))

    walk(root)
    return tuple(results), any(positive_hits)


def spelling_reprobe_evidence(issue, match_file, candidate, baseline):
    """Explain why an alternate option spelling is observably effective.

    The candidate must reach at least one positive predicate anchor and change
    at least one predicate clause relative to the same command with the option
    removed. Exit zero and absence of an "Unknown argument" diagnostic are not
    evidence: unrecognised `/` options are silently ignored on Windows.
    """
    candidate_sig, positive = predicate_clause_signature(
        issue, candidate["text"], candidate["rc"], candidate["timed_out"],
        match_file)
    baseline_sig, _ = predicate_clause_signature(
        issue, baseline["text"], baseline["rc"], baseline["timed_out"],
        match_file)
    if not candidate_sig or not positive or candidate_sig == baseline_sig:
        return None
    changed = [str(i + 1) for i, (a, b) in
               enumerate(zip(candidate_sig, baseline_sig)) if a != b]
    return ("predicate clause(s) " + ",".join(changed)
            + " differ from the same command with the option removed")


def _predicate_quotes(issue, match_file, marker):
    """True if the issue's declared diagnostic surface spells out `marker`.

    The feature-absence markers in `classify` are a proxy for "this release
    rejected the input before reaching the code under test". That proxy breaks
    down on issues whose reported symptom IS a diagnostic, because then the
    signal and the symptom are the same observation. Measured on #3055, a
    diagnostic-quality issue, in both directions:

    * a release that emits the GOOD diagnostic the issue asks for ("no matching
      function for call to 'clamp'" plus the note naming the bad argument)
      scores no-repro -- correctly, that is what "fixed here" looks like -- and
      was then demoted to invalid-probe, so `bisect` trimmed away the very
      release that fixed it; and
    * a probe that MATCHES ("use of undeclared identifier 'clamp'" for a
      wrong-arity call to a plainly declared intrinsic, which is the filed bug)
      was demoted because the predicate happened to contain a `not_regex`
      clause, so every release including ground truth would have been
      discarded and `bisect` would have reported "no release could run this
      repro".

    The suppression is deliberately narrow: the demotion stands unless a
    *positive* clause contains the matched marker text verbatim. Usually that
    clause is in the active predicate. An issue that records one defect through
    several predicates may opt a secondary predicate into the same diagnostic
    surface with `"quote_from": ["match.json"]`; without that explicit link,
    sibling predicates remain isolated. This is needed for a diagnostic that
    later becomes an ICE: the ICE predicate must not call the earlier, valid
    diagnostic an invalid probe merely because the quotation lives in the
    diagnostic predicate.

    Inverted clauses do not count: "the symptom is that X is absent" does not
    make X's presence a measurement. No predicate is evaluated as a regex
    against the marker, so a loose pattern cannot widen this.

    Keeping it narrow matters. The converse rule -- treat any marker on a
    matching probe as a bad probe -- was rejected in batch 004 because #1627's
    reported symptom is an `unrecognized argument` diagnostic, and a permissive
    classifier reintroduces the fake-regression bug the markers exist to
    prevent (#3873, #3038), which has produced wrong verdicts twice.
    """
    if not marker:
        return False
    needle = marker.lower()

    def walk(node):
        if not isinstance(node, dict):
            return False
        kind = node.get("kind")
        if kind in ("any_of", "all_of"):
            return any(walk(s) for s in node.get("value") or [])
        if kind in ("contains", "regex") and not node.get("invert", False):
            return needle in str(node.get("value", "")).lower()
        return False

    def load(name, seen):
        if name in seen:
            return False
        if os.path.basename(name) != name or not name.endswith(".json"):
            sys.exit(f"{match_file}: quote_from entries must be predicate "
                     f"filenames in the issue directory, got {name!r}")
        seen.add(name)
        path = os.path.join(issue_dir(issue), name)
        try:
            with open(path) as f:
                predicate = json.load(f)
        except (OSError, ValueError):
            return False
        if walk(predicate):
            return True
        refs = predicate.get("quote_from", [])
        if isinstance(refs, str):
            refs = [refs]
        if not isinstance(refs, list) or not all(
                isinstance(ref, str) for ref in refs):
            sys.exit(f"{path}: quote_from must be a list of predicate "
                     f"filenames")
        return any(load(ref, seen) for ref in refs)

    return load(match_file, set())


def _eval_match(m, text, rc, timed_out, path):
    kind = m["kind"]
    # Fail loudly and specifically. A mistyped key here silently becomes a
    # KeyError deep in a batch run, and the cost of a misread predicate is a
    # wrong verdict on a real issue.
    if kind in ("contains", "not_contains", "regex", "not_regex") \
            and "value" not in m:
        sys.exit(f"{path}: kind '{kind}' requires a \"value\" key "
                 f"(found: {', '.join(sorted(m)) or 'nothing'})")
    if kind in ("any_of", "all_of"):
        # One defect can present with different signatures depending on build
        # config -- e.g. an infinite loop that hangs a Release build trips an
        # assert in a Debug one. Without a disjunction such an issue gets a
        # spurious "fixed" verdict from whichever build you happened to run.
        subs = m.get("value")
        if not isinstance(subs, list) or not subs:
            sys.exit(f"{path}: kind '{kind}' requires a non-empty list "
                     f"\"value\" of sub-predicates")
        results = [_eval_match(s, text, rc, timed_out, path) for s in subs]
        hit = any(results) if kind == "any_of" else all(results)
    elif kind == "internal_failure":
        hit = is_internal_failure(text, rc, timed_out)
    elif kind == "nonzero_exit":
        hit = timed_out or (rc not in (0, None))
    elif kind == "timeout":
        hit = timed_out
    elif kind == "contains":
        hit = m["value"] in text
    elif kind == "not_contains":
        hit = m["value"] not in text
    elif kind == "regex":
        hit = re.search(m["value"], text, re.MULTILINE) is not None
    elif kind == "not_regex":
        hit = re.search(m["value"], text, re.MULTILINE) is None
    else:
        sys.exit(f"unknown match kind: {kind}")
    return (not hit) if m.get("invert") else hit


# --------------------------------------------------------------------------
# release binaries
# --------------------------------------------------------------------------

def find_dxc(root):
    """Locate dxc inside an extracted release tree, preferring the x64 flavour."""
    best = None
    for dirpath, _, files in os.walk(root):
        if EXE not in files:
            continue
        p = os.path.join(dirpath, EXE)
        if os.path.basename(dirpath).lower() == "x64":
            return p
        best = best or p
    return best


@contextlib.contextmanager
def cache_lock(name, timeout=1800):
    """Serialise one release's download/extract across processes.

    Issues are triaged in parallel, and `bisect` probes both endpoints before
    anything else, so every worker asks for the oldest and newest releases at
    almost the same moment. On a cold cache that is a guaranteed race, not a
    theoretical one.

    os.mkdir is atomic on both Windows and POSIX, which is all the mutual
    exclusion this needs. The timeout is generous because the thing being
    guarded is a multi-hundred-megabyte download.
    """
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f".lock-{name}")
    deadline = time.time() + timeout
    while True:
        try:
            os.mkdir(path)
            break
        except FileExistsError:
            # A crashed worker leaves its lock behind; without this the next
            # run blocks for the full timeout on a cache that is merely dirty.
            try:
                if time.time() - os.path.getmtime(path) > timeout:
                    os.rmdir(path)
                    continue
            except OSError:
                pass
            if time.time() > deadline:
                sys.exit(f"timed out waiting for {path}; remove it if stale")
            time.sleep(2)
    try:
        yield
    finally:
        try:
            os.rmdir(path)
        except OSError:
            pass


def ensure_release(tag):
    c = con()
    row = c.execute("SELECT * FROM releases WHERE tag = ?", (tag,)).fetchone()
    if row is None:
        sys.exit(f"unknown release tag: {tag} (run 'triage.py catalog' first)")
    if row["cached_path"] and os.path.exists(row["cached_path"]):
        return row["cached_path"]
    if not row["asset_name"]:
        sys.exit(f"{tag} ships no dxc binary; not usable for bisection")

    dest = os.path.join(CACHE, tag)
    zip_path = os.path.join(dest, row["asset_name"])
    done = os.path.join(dest, ".extracted")

    with cache_lock(tag):
        # Re-check inside the lock: the worker we queued behind has very
        # likely just done this work for us.
        row = c.execute("SELECT * FROM releases WHERE tag = ?", (tag,)).fetchone()
        if row["cached_path"] and os.path.exists(row["cached_path"]):
            return row["cached_path"]

        os.makedirs(dest, exist_ok=True)
        if not os.path.exists(done):
            if not os.path.exists(zip_path):
                # Download into a scratch directory and move the finished file
                # into place. os.path.exists(zip_path) goes true the moment a
                # download *starts*, so without this a second worker would
                # happily extract a half-written archive.
                print(f"downloading {tag} ({row['asset_name']}) ...", file=sys.stderr)
                tmp = os.path.join(dest, ".part")
                shutil.rmtree(tmp, ignore_errors=True)
                os.makedirs(tmp, exist_ok=True)
                gh("release", "download", tag, "--repo", REPO,
                   "--pattern", row["asset_name"], "--dir", tmp, "--clobber")
                os.replace(os.path.join(tmp, row["asset_name"]), zip_path)
                shutil.rmtree(tmp, ignore_errors=True)
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(dest)
            open(done, "w").close()

        exe = find_dxc(dest)
        if not exe:
            sys.exit(f"no {EXE} found in extracted {tag}")
        c.execute("UPDATE releases SET cached_path = ? WHERE tag = ?", (exe, tag))
        c.commit()
        return exe


def resolve_compiler(name):
    row = con().execute("SELECT exe_path FROM compilers WHERE id = ?",
                        (name,)).fetchone()
    return row["exe_path"] if row else ensure_release(name)


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_init(a):
    for d in (ROOT, ISSUES, CACHE, REPORTS, os.path.join(CACHE_ROOT, "scratch")):
        os.makedirs(d, exist_ok=True)
    # The cache is derived and bulky; keep it out of the repo without relying
    # on anyone remembering to update a .gitignore three directories up.
    with open(os.path.join(CACHE_ROOT, ".gitignore"), "w") as f:
        f.write("# Downloaded compilers and the derived index. Rebuild the\n"
                "# database with: triage.py reindex\n*\n")
    c = con()
    c.executescript(SCHEMA)
    c.commit()
    print(f"artifacts: {ROOT}\ncache:     {CACHE_ROOT} (gitignored)")


def cmd_catalog(a):
    """Populate the release table.

    Ordering uses the asset *build date* encoded in the zip name, not the
    publish date: servicing patches ship long after the snapshot they were
    built from, so publish order does not match source order.
    """
    rels = json.loads(gh("release", "list", "--repo", REPO, "--limit", "200",
                         "--json", "tagName,publishedAt,isPrerelease"))
    c = con()
    for r in rels:
        tag = r["tagName"]
        # A release with no tag is not addressable by any other command and
        # shows up in the catalogue as a nameless duplicate of whatever shares
        # its build date. Noticed on #8725 next to v1.9.2607.
        if not tag:
            continue
        assets = json.loads(gh("release", "view", tag, "--repo", REPO,
                               "--json", "assets"))["assets"]
        dxc = next((x["name"] for x in assets
                    if x["name"].startswith("dxc_") and x["name"].endswith(".zip")), None)
        m = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", dxc or "")
        # Preview releases are excluded so the bisection sequence stays linear.
        bisectable = 1 if (dxc and not r["isPrerelease"]) else 0
        c.execute(
            "INSERT INTO releases (tag, published_at, build_date, asset_name,"
            " bisectable, prerelease) VALUES (?,?,?,?,?,?)"
            " ON CONFLICT(tag) DO UPDATE SET published_at=excluded.published_at,"
            " build_date=excluded.build_date, asset_name=excluded.asset_name,"
            " bisectable=excluded.bisectable, prerelease=excluded.prerelease",
            (tag, r["publishedAt"], "-".join(m.groups()) if m else None, dxc,
             bisectable, int(r["isPrerelease"])))
    c.commit()
    if a.seed_from:
        seed_local(a.seed_from)
    show_releases()


def seed_local(path):
    """Adopt release trees the DXC test infrastructure already downloaded.

    Typically <repo>/build/tools/clang/test/dxc_releases.
    """
    if not os.path.isdir(path):
        print(f"no local release cache at {path}", file=sys.stderr)
        return
    c = con()
    tags = {r["tag"] for r in c.execute("SELECT tag FROM releases")}
    for name in os.listdir(path):
        if name in tags:
            exe = find_dxc(os.path.join(path, name))
            if exe:
                c.execute("UPDATE releases SET cached_path = ? WHERE tag = ?",
                          (exe, name))
                print(f"seeded {name}")
    c.commit()


def show_releases():
    print("bisection sequence (oldest -> newest):")
    for r in con().execute("SELECT tag, build_date, cached_path FROM releases"
                           " WHERE bisectable = 1 ORDER BY build_date"):
        print(f"  {r['build_date']}  {r['tag']:<14} "
              f"{'cached' if r['cached_path'] else '-'}")


def cmd_compiler(a):
    ver = subprocess.run([a.exe, "--version"], capture_output=True,
                         text=True, encoding="utf-8",
                         errors="replace").stdout.strip().replace("\n", " ")
    c = con()
    c.execute("INSERT OR REPLACE INTO compilers (id, exe_path, git_commit,"
              " version, built_at) VALUES (?,?,?,?,?)",
              (a.id, a.exe, a.commit, ver, now()))
    c.commit()
    print(f"{a.id}: {a.exe}\n  version: {ver}\n  commit:  {a.commit}")

    # The registry file used to be maintained by hand and read by nobody, which
    # is exactly how it came to describe a previous binary for five batches.
    # Write it here so it cannot drift from the row above.
    reg_dir = os.path.join(CACHE_ROOT, "compilers")
    os.makedirs(reg_dir, exist_ok=True)
    reg_path = os.path.join(reg_dir, f"{a.id}.json")
    reg = {}
    if os.path.exists(reg_path):
        try:
            reg = json.load(open(reg_path, encoding="utf-8"))
        except ValueError:
            reg = {}
    reg.update({"id": a.id, "exe_path": a.exe, "git_commit": a.commit,
                "version": ver, "built_at": now()})
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
        f.write("\n")
    print(f"  registry: {reg_path}")

    short = (a.commit or "")[:8]
    if a.commit and short not in ver:
        print(f"\nWARNING: --commit {short} does not appear in the version "
              f"string ({ver}).", file=sys.stderr)
        if "dirty" in ver:
            print("The build looks stale or dirty. DXC caches the generated "
                  "version headers; delete build/utils/version/version.inc and "
                  "dxcversion.inc (and their .gen files) and rebuild, or triage "
                  "provenance will be wrong.", file=sys.stderr)
        else:
            # The case that went undetected: a mismatch with no `dirty` marker,
            # because the binary was built from a fork-local commit.
            print("If the binary was built from a fork-local commit, or from one "
                  "a later history rewrite orphaned, record the PUBLIC upstream "
                  "commit here and prove the equivalence with a controlled "
                  "`git diff --name-only` against both that commit and an older "
                  "one. A SHA that resolves only on this machine is not a "
                  "citation. See reports/provenance-correction.md.",
                  file=sys.stderr)


ISSUE_FETCH_FIELDS = (
    "number,title,url,createdAt,author,labels,body,comments,state"
)


def cmd_fetch(a):
    d = issue_dir(a.issue)
    os.makedirs(d, exist_ok=True)
    raw = gh("issue", "view", str(a.issue), "--repo", REPO, "--json",
             ISSUE_FETCH_FIELDS)
    with open(os.path.join(d, "issue.json"), "w", encoding="utf-8") as f:
        f.write(raw)
    j = json.loads(raw)
    c = con()
    c.execute("INSERT OR IGNORE INTO issues (number) VALUES (?)", (a.issue,))
    c.execute("UPDATE issues SET title=?, url=?, created_at=?, labels=?,"
              " batch=COALESCE(?, batch) WHERE number=?",
              (j["title"], j["url"], j["createdAt"],
               ",".join(l["name"] for l in j["labels"]), a.batch, a.issue))
    c.commit()
    print(f"#{j['number']} {j['title']}")
    print(f"  labels: {','.join(l['name'] for l in j['labels']) or '(none)'}")
    print(f"  comments: {len(j['comments'])}  -> {d}")


# Options that consume following argv tokens. Keep this in sync with every
# JoinedOrSeparate, Separate and MultiArg entry in HLSLOptions.td, plus the
# Clang options DXC forwards. `retarget_cmd`, `ce_args`, the spelling re-probe
# control and probe-input protection all use the same table; an omission can
# turn an option value into a source file. #3044 exposed the missing `-Fi`.
VALUE_FLAG_ARITY = {
    "-d": 1, "-i": 1, "-import-binding-table": 1,
    "-binding-table-define": 1, "-memdep-block-scan-limit": 1,
    "-opt-disable": 1, "-opt-enable": 1, "-opt-select": 2,
    "-mf": 1, "-external": 1, "-external-fn": 1, "-hv": 1,
    "-rootsig-define": 1, "-auto-binding-space": 1, "-exports": 1,
    "-default-linkage": 1, "-precise-output": 1, "-encoding": 1,
    "-validator-version": 1, "-print-before": 1, "-print-after": 1,
    "-ignore-semdef": 1, "-override-semdef": 1,
    "-fvk-b-shift": 2, "-fvk-t-shift": 2, "-fvk-s-shift": 2,
    "-fvk-u-shift": 2, "-fvk-bind-globals": 2,
    "-fvk-bind-register": 4, "-vkbr": 4, "-fspv-max-id": 1,
    "-fvk-bind-resource-heap": 2, "-fvk-bind-sampler-heap": 2,
    "-fvk-bind-counter-heap": 2,
    "-t": 1, "-e": 1, "-denorm": 1,
    "-fo": 1, "-fc": 1, "-fh": 1, "-fe": 1, "-fd": 1,
    "-fre": 1, "-frs": 1, "-fsh": 1, "-fi": 1, "-vn": 1,
    "-setrootsignature": 1, "-verifyrootsignature": 1,
    "-force-rootsig-ver": 1, "-force_rootsig_ver": 1,
    "-setprivate": 1, "-getprivate": 1,
    # Forwarded Clang/common options not defined by HLSLOptions.td.
    "-x": 1, "-include": 1,
}
VALUE_FLAGS = set(VALUE_FLAG_ARITY)

# Existing files named by these options are expected to change. Everything
# else named on the command line is evidence and is protected from mutation.
OUTPUT_VALUE_FLAGS = {
    "-mf", "-fo", "-fc", "-fh", "-fe", "-fd", "-fre", "-frs", "-fsh",
    "-fi", "-setprivate", "-getprivate",
}


def option_key(token):
    """Canonicalise one complete option token for the argv tables above."""
    token = token.lower().rstrip(":=")
    if token.startswith("/") and len(token) > 1:
        token = "-" + token[1:]
    return token


def option_arity(token):
    """Number of following argv tokens consumed by this separate spelling."""
    key = option_key(token)
    # `-Foo=bar` and joined spellings consume no following token.
    if "=" in token or ":" in token:
        return 0
    return VALUE_FLAG_ARITY.get(key, 0)


def command_token_roles(line):
    """Return argv plus indexes consumed as option values."""
    toks = split_cmd(line)
    values = set()
    i = 0
    while i < len(toks):
        arity = option_arity(toks[i])
        for j in range(1, arity + 1):
            if i + j < len(toks):
                values.add(i + j)
        i += 1 + arity
    return toks, values


def split_cmd(line):
    """Split a cmd.txt line into argv, treating `\\` as a path separator.

    `shlex.split` runs in POSIX mode, where a backslash is an escape: it turns
    `-I inc\\sub` into `-I incsub` and `-Fo out\\a.dxo` into `-Fo outa.dxo`,
    silently, with no error to notice. Every path DXC is given on Windows is
    spelled that way, so the failure mode is a probe that compiles the wrong
    thing or writes to the wrong place and still looks fine in the capture.

    Quoting still works -- `"a b.hlsl"` is one token -- because only the escape
    character is disabled, not the quote characters. Nothing in the current
    corpus was affected (no committed cmd.txt contains a backslash); this is a
    trap removed before it is stepped on rather than a repair.
    """
    lex = shlex.shlex(line, posix=True)
    lex.whitespace_split = True
    lex.escape = ""
    return list(lex)


def retarget_cmd(line, shader):
    """Point one cmd.txt line at a different source file.

    Only the source operand changes, so a control is run with byte-identical
    arguments to the repro. A flag's *value* is a separate token -- `-I` takes
    a path, `-Fo` a filename -- and must survive untouched, or the control
    stops differing from the repro in exactly one way. Lines with no HLSL
    source are preserved: a multi-invocation chain may preprocess a `.hlsl`
    and then consume the generated `.i` or `.bc` on a later line.
    """
    toks, values = command_token_roles(line)
    out, replaced = [], False
    for i, tok in enumerate(toks):
        is_source = (not replaced
                     and tok.lower().endswith(".hlsl")
                     and not tok.startswith(("-", "/"))
                     and i not in values)
        out.append(shader if is_source else tok)
        replaced = replaced or is_source
    if not replaced:
        return line
    return subprocess.list2cmdline(out)


def retarget_cmds(lines, shader):
    """Retarget every HLSL-bearing line, requiring at least one such line."""
    rewritten = []
    found_source = False
    for line in lines:
        toks, values = command_token_roles(line)
        found_source = found_source or any(
            tok.lower().endswith(".hlsl")
            and not tok.startswith(("-", "/"))
            and i not in values
            for i, tok in enumerate(toks)
        )
        rewritten.append(retarget_cmd(line, shader))
    if not found_source:
        raise SystemExit("no source file to replace in command list")
    return rewritten


UNKNOWN_ARGUMENT_RE = re.compile(
    r"(?i)(?:unknown|unrecognized)\s+(?:argument|option)\s*:?\s*"
    r"(?:'([^']+)'|\"([^\"]+)\"|([/-][^\s,;]+))"
)


def unknown_argument_token(text):
    """Return the flag named by an Unknown/Unrecognized argument diagnostic."""
    hit = UNKNOWN_ARGUMENT_RE.search(text)
    if not hit:
        return None
    return next((g for g in hit.groups() if g), None)


def invalid_option_range_warning(text):
    """Warn when an unsupported option, rather than the subject, trims history."""
    token = unknown_argument_token(text)
    if not token:
        return None
    return (
        f"warning: this release rejected option {token}. An unrelated option "
        "can make a valid repro look unprobeable and silently shorten the "
        "history range; verify the option is load-bearing for the symptom, "
        "or compare and drop it before accepting the range."
    )


def argument_spelling_variants(arg):
    """Plausible legacy spellings for one rejected dxc option.

    Old dxc releases sometimes use `_` where current releases use `-`, or
    accept the `/` prefix but not the `-` prefix. Treating the first spelling
    rejection as feature absence fabricated history for #3362.
    """
    if not arg or arg[0] not in "-/":
        return []
    if arg.startswith("--"):
        prefix, body = "--", arg[2:]
    else:
        prefix, body = arg[0], arg[1:]
    if not body:
        return []

    bodies = [body]
    for candidate in (body.replace("-", "_"), body.replace("_", "-")):
        if candidate not in bodies:
            bodies.append(candidate)
    prefixes = [prefix]
    for candidate in ("-", "/"):
        if candidate not in prefixes:
            prefixes.append(candidate)

    variants = []
    # Try the same prefix with the separator transposed before changing prefix.
    for candidate_body in bodies[1:]:
        variants.append(prefix + candidate_body)
    for candidate_prefix in prefixes[1:]:
        for candidate_body in bodies:
            variants.append(candidate_prefix + candidate_body)
    return [v for i, v in enumerate(variants)
            if v.lower() != arg.lower()
            and v.lower() not in {x.lower() for x in variants[:i]}]


def replace_argument_spelling(cmds, old, new):
    """Replace one complete argv token in every command line."""
    rewritten, changed = [], False
    for line in cmds:
        toks = split_cmd(line)
        line_changed = any(tok.lower() == old.lower() for tok in toks)
        out = [new if tok.lower() == old.lower() else tok for tok in toks]
        changed = changed or line_changed
        rewritten.append(subprocess.list2cmdline(out) if line_changed else line)
    return rewritten if changed else None


def remove_argument(cmds, arg):
    """Remove one option and its separate value tokens from every command."""
    rewritten, changed = [], False
    for line in cmds:
        toks = split_cmd(line)
        out, i, line_changed = [], 0, False
        while i < len(toks):
            if toks[i].lower() == arg.lower():
                i += 1 + option_arity(toks[i])
                changed = line_changed = True
                continue
            out.append(toks[i])
            i += 1
        rewritten.append(subprocess.list2cmdline(out) if line_changed else line)
    return rewritten if changed else None


def command_option_tokens(cmds):
    """Distinct option tokens, excluding values that happen to start with `/`."""
    result = []
    for line in cmds:
        toks, values = command_token_roles(line)
        for i, tok in enumerate(toks):
            if i in values or not tok.startswith(("-", "/")):
                continue
            if tok not in result:
                result.append(tok)
    return result


def classify(issue, text, rc, timed_out, match_file="match.json", explain=False):
    """Score one probe: repro | no-repro | invalid-probe | unscored.

    With `explain=True`, returns `(verdict, reason)` -- the reason is the
    sentence `execute` stamps into the capture header, so a demotion is
    self-explaining on disk instead of only reconstructable by re-reading this
    function against the captured text.

    Kept as a free function rather than inlined into `execute` so that
    `reindex` scores committed evidence with *exactly* the code that scored it
    live. If the two could drift, a rebuild could silently disagree with the
    run that produced the file, and the disagreement would look like a finding.

    Not every issue has a symptom predicate. #3150 is a specification gap with
    nothing to reproduce, and #2427's evidence is four command lines rather
    than compiler output -- but both still make compiler-measurable claims
    worth capturing. Returning `unscored` keeps that evidence first-class
    instead of forcing a meaningless verdict onto it.
    """
    def out(verdict, reason=None):
        return (verdict, reason) if explain else verdict

    if not os.path.isfile(os.path.join(issue_dir(issue), match_file)):
        return out("unscored")

    verdict = "repro" if matches(issue, text, rc, timed_out, match_file) \
        else "no-repro"

    # A "no-repro" is only meaningful if the compiler actually compiled the
    # repro. An older release that rejects the *target profile* or a flag never
    # reaches the code under test, yet fails in a way no symptom predicate
    # matches -- so it scores as no-repro and, during a history search, fakes a
    # regression. Measured on #3873: every release up to v1.6.2112 "fixed" it
    # purely because ps_6_7 did not exist yet; retested at ps_6_0 the oldest
    # release hangs, so it had in fact always reproduced.
    #
    # The same trap also fires one level up, in the *front end*: a release that
    # predates a language FEATURE (a type, an intrinsic, an attribute) rejects
    # the repro with an ordinary semantic diagnostic rather than a profile
    # error. Measured on #3038: v1.4.1907 answers "use of undeclared identifier
    # 'RayQuery'" because DXR 1.1 did not exist yet. That is not a clean run --
    # the compiler never reached the code under test -- but it looks exactly
    # like one, so a linear scan reports a transition that never happened and a
    # binary search invents a regression.
    # The same trap also fires FORWARDS in time, which every marker above
    # misses because they all mean "you used something that does not exist
    # yet". A *newer* compiler can reject an *older* repro because the default
    # language version moved under it. Measured on #2202, filed in 2019 with no
    # -HV: at today's default -HV 2021 the front end rejects `bool3 ? a : b`
    # before codegen, so the DXIL validator the issue is about never runs --
    # and the probe scores as a clean run, faking a fix in whichever release
    # changed the default. Only diagnostics that have actually been observed
    # doing this belong here; guessing at them would silently discard evidence.
    #
    # Each marker must name something the compiler does not HAVE. A bare "is
    # not supported" does not: DXC emits that phrase from ~25 distinct
    # diagnostics about present-day code ("operator is not supported", "signed
    # integer division is not supported on minimum-precision types", PR #8517's
    # own "mixing bound and descriptor heap resources ... is not supported"),
    # so unqualified it demotes ordinary errors. It is anchored to the
    # target/profile forms that really do mean "this build cannot express your
    # input". Noticed independently on #8732; it fired on no archived capture,
    # so the anchoring changes no existing verdict.
    hit = re.search(
        r"(?i)invalid profile|unsupported profile|unrecognized (?:argument|option)|"
        r"unknown argument|unknown HLSL version(?::\s*[^\r\n]+)?|"
        r"requires shader model|"
        r"is not supported (?:for|on|in|with) "
        r"(?:the current |this |target )*(?:target|profile|shader model|stage)|"
        r"CodeGen not available|recompile with -D|"
        r"use of undeclared identifier|unknown type name|"
        r"no member named|no matching function for call to|"
        r"for non-scalar types use 'select'", text)
    marker = hit.group(0) if hit else None
    # ...unless the issue under triage is ABOUT that diagnostic, in which case
    # the marker is measuring the symptom rather than feature absence. See
    # `_predicate_quotes`.
    quoted = _predicate_quotes(issue, match_file, marker)
    unsupported = bool(marker) and not quoted

    if verdict == "no-repro" and unsupported:
        return out("invalid-probe",
                   f'output matched the feature-absence marker "{marker}", so '
                   f'this build did not reach the code under test')

    # A probe that CRASHED measured nothing about the reported symptom, and
    # scoring it as a clean run is the most dangerous direction of error: it
    # erases a defect rather than inventing one, at exactly the point where the
    # output is a release boundary someone will act on. Measured on #2202:
    # v1.8.2403 access-violates (0xC0000005) on the repro instead of diagnosing
    # it, and scored `no-repro` -- the one release strictly worse than the
    # reported symptom, recorded as the absence of a problem. A `--linear` scan
    # duly reported a fix window that does not exist.
    #
    # Note this cannot fire when the crash IS the symptom: an internal_failure
    # predicate scores that probe `repro`, never `no-repro`.
    if verdict == "no-repro" and is_internal_failure(text, rc, timed_out):
        return out("invalid-probe",
                   "the probe failed internally, so it measured nothing about "
                   "the reported symptom")

    # Absence-based predicates ("the symptom is that X is MISSING") are
    # satisfied for free by any compile that never got far enough to emit X.
    # #1877's predicate is `not_contains fptosi`; a release that failed to
    # parse the repro emits no fptosi either, and would score as a textbook
    # reproduction. Those probes were checked by hand and did compile, but the
    # hazard is structural, so flag it rather than silently trusting it.
    if verdict == "repro" and _is_absence_predicate(issue, match_file) \
            and (unsupported or is_internal_failure(text, rc, timed_out)):
        return out("invalid-probe",
                   f'an absence clause of this predicate can be satisfied for '
                   f'free by a run that failed early '
                   + (f'(matched "{marker}")' if unsupported
                      else "(the probe failed internally)"))
    return out(verdict)


def classify_capture(issue, meta, text, match_file=None, explain=False):
    """Score archived output, including proof attached to spelling re-probes."""
    mf = match_file or meta.get("match", "match.json")
    rc = None if meta.get("exit") in (None, "None", "TIMEOUT") \
        else int(meta["exit"])
    verdict, reason = classify(
        issue, text, rc, meta.get("timed_out") == "1", mf, explain=True)
    if meta.get("argument-spelling-reprobe") \
            and not meta.get("argument-spelling-evidence"):
        verdict = "invalid-probe"
        reason = ("legacy spelling re-probe has no behavioural control proving "
                  "the accepted spelling changed compiler output")
    return (verdict, reason) if explain else verdict


def probe_path(d, compiler, match_file="match.json", label=None):
    """Where a probe's output is filed.

    The predicate is part of the identity of a probe, not just of its header.
    SKILL.md step 4 tells you to add a second `match-*.json` and bisect each
    separately -- but with the name derived from the compiler alone, the second
    bisection silently overwrote the first predicate's entire release history,
    file for file, with no warning and nothing left in the tree to say it had
    happened. Measured on #2191, where 20 of 21 primary probes were replaced;
    #2188 declined to run a second predicate at all because of it, and #2202
    worked around it with labels. Three of five workers in one batch hit the
    same edge, so it is not an exotic path.

    The default predicate keeps the bare name, so nothing already committed
    moves; a non-default one gets its own slot and cannot collide.
    """
    stem = os.path.splitext(os.path.basename(match_file))[0]
    suffix = "" if match_file == "match.json" else f"--{stem}"
    base = f"variant-{label}-{compiler}" if label else f"out-{compiler}"
    return os.path.join(d, f"{base}{suffix}.txt")


def stamp_repeat(path, attempts, hits):
    """Record a --repeat aggregate in the surviving capture's header.

    Without this the only record of "2 of 3 runs showed it" is a `runs` row
    whose `cmd` is `(see single runs)` and which has no backing file, so
    `reindex` -- which rebuilds runs from captures -- destroys it permanently.
    For an intermittent defect that aggregate is the whole finding.
    """
    if attempts <= 1 or not (path and os.path.isfile(path)):
        return
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    lines = [ln for ln in lines if not ln.startswith(("# attempts:", "# hits:"))]
    for i, ln in enumerate(lines):
        if ln.startswith("# verdict:"):
            lines[i + 1:i + 1] = [f"# attempts: {attempts}\n", f"# hits: {hits}\n"]
            break
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def stamp_reason(path, reason):
    """Record WHY a probe was demoted, in the capture itself.

    An `invalid-probe` line is the one verdict that says "ignore this
    measurement", and `bisect` acts on it by trimming the release from the
    history. Reconstructing which of three independent rules fired, and on what
    text, meant re-reading `classify` against the whole capture -- so the most
    consequential verdict was the least self-explaining one on disk. Raised on
    #3055 after exactly that exercise.
    """
    if not (path and os.path.isfile(path)):
        return
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    lines = [ln for ln in lines if not ln.startswith("# invalid-probe-reason:")]
    if reason:
        for i, ln in enumerate(lines):
            if ln.startswith("# verdict:"):
                lines[i + 1:i + 1] = [f"# invalid-probe-reason: {reason}\n"]
                break
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)


def _file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_hashes(root):
    result = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            path = os.path.join(base, name)
            if os.path.islink(path):
                continue
            result[os.path.relpath(path, root)] = _file_hash(path)
    return result


def _local_file_token(root, token):
    """Resolve a command-line file token only when it is inside the issue."""
    if token.startswith("@"):
        token = token[1:]
    path = token if os.path.isabs(token) else os.path.join(root, token)
    path = os.path.abspath(path)
    try:
        if os.path.commonpath((root, path)) != os.path.abspath(root):
            return None
    except ValueError:
        return None
    return os.path.relpath(path, root) if os.path.isfile(path) else None


def probe_input_paths(root, cmds):
    """Files named by the command that are evidence, not declared outputs."""
    referenced, outputs = set(), set()
    for line in cmds:
        toks, _ = command_token_roles(line)
        i = 0
        while i < len(toks):
            arity = option_arity(toks[i])
            key = option_key(toks[i])
            for j in range(1, arity + 1):
                if i + j >= len(toks):
                    break
                rel = _local_file_token(root, toks[i + j])
                if rel:
                    referenced.add(rel)
                    if key in OUTPUT_VALUE_FLAGS:
                        outputs.add(rel)
            if arity == 0:
                rel = _local_file_token(root, toks[i])
                if rel:
                    referenced.add(rel)
            i += 1 + arity
    return referenced - outputs


def _sync_probe_outputs(source, scratch, before, after, protected):
    """Copy compiler-created output back, never a protected input."""
    for rel, digest in after.items():
        if rel in protected or before.get(rel) == digest:
            continue
        src = os.path.join(scratch, rel)
        dst = os.path.join(source, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def _run_probe_command_list(exe, d, cmds, protect_cmds=None,
                            sync_outputs=False):
    """Run one probe in an isolated copy and reject input mutation.

    A spelling retry can change an option's grammar. #3044's `/Fi` retry made
    an old `-P` treat the repro as its output and silently overwrote it at exit
    zero. Every attempt now runs in a fresh copy, and every file named as an
    input by the requested command is hashed before and after. Only generated
    outputs are copied back after a safe run.
    """
    scratch_root = os.path.join(CACHE_ROOT, "scratch")
    os.makedirs(scratch_root, exist_ok=True)
    scratch = os.path.join(
        scratch_root,
        f"probe-{os.path.basename(d)}-{os.getpid()}-{time.time_ns()}")
    protected = probe_input_paths(d, protect_cmds or cmds)
    shutil.copytree(d, scratch)
    before = _tree_hashes(scratch)
    try:
        rc, timed_out, text, observations = _run_command_list(exe, scratch, cmds)
        after = _tree_hashes(scratch)
        mutated = [rel for rel in sorted(protected)
                   if before.get(rel) != after.get(rel)]
        if mutated:
            raise SystemExit(
                "probe modified its own input evidence: "
                + ", ".join(mutated)
                + ". The run was isolated and no issue artifact was changed.")
        if sync_outputs:
            _sync_probe_outputs(d, scratch, before, after, protected)
        return {"rc": rc, "timed_out": timed_out, "text": text,
                "observations": observations}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _run_command_list(exe, d, cmds):
    """Run one or more dxc command lines and return their combined capture."""
    chunks, observations, worst_rc, timed_out = [], [], 0, False
    for line in cmds:
        try:
            p = subprocess.run([exe] + split_cmd(line), cwd=d,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=TIMEOUT)
            rc, out, err, to = p.returncode, p.stdout, p.stderr, False
        except subprocess.TimeoutExpired as e:
            rc, out, err, to = None, e.stdout or "", e.stderr or "", True
        out, err = redact_paths(out), redact_paths(err)
        timed_out = timed_out or to
        if rc not in (0, None) and worst_rc == 0:
            worst_rc = rc
        observations.append((rc, to, out, err))
        chunks.append(f"$ dxc {line}\n[exe] {display_exe(exe)}\n"
                      f"[exit] {'TIMEOUT' if to else rc}\n"
                      f"--- stdout ---\n{out}\n--- stderr ---\n{err}\n")
    return worst_rc, timed_out, "\n".join(chunks), tuple(observations)


def execute(issue, compiler, match_file="match.json", record=True, repeat=1,
            shader=None, label=None, args=None, expect=None, force=False,
            hypothesis=False):
    """Run an issue's repro and classify the result.

    `repeat` runs the whole command list several times and reports the symptom
    if *any* attempt shows it. Some defects are nondeterministic and a single
    run then decides the verdict by luck. Measured on #3768, whose heap
    corruption fires on roughly 68% of runs at v1.6.2104 and 82% at v1.6.2106:
    a one-shot probe calls a reproducing release clean about a third of the
    time. Repeats cut that exponentially -- at a 68% rate, 30 clean runs happen
    with probability ~2e-15, which is what turns "we saw no crash" into
    evidence rather than an absence of it.
    """
    if hypothesis and not expect:
        sys.exit("--hypothesis requires --expect: the expectation is the "
                 "prediction being tested")
    if repeat > 1:
        attempts, seen = [], []
        for i in range(repeat):
            r = execute(issue, compiler, match_file, record=False, repeat=1,
                        shader=shader, label=label, args=args, expect=expect,
                        force=True, hypothesis=hypothesis)
            attempts.append(r)
            seen.append(r["verdict"])
            if r["verdict"] == "repro":
                break           # one confirmed sighting is enough
        hits = seen.count("repro")
        # Prefer a positive sighting; otherwise keep the first result, but an
        # invalid-probe anywhere means the compiler never ran the repro at all.
        best = next((x for x in attempts if x["verdict"] == "repro"), None) \
            or next((x for x in attempts if x["verdict"] == "invalid-probe"),
                    attempts[0])
        best = dict(best)
        best["attempts"], best["hits"] = len(attempts), hits
        # The hit rate IS the evidence for a nondeterministic bug, and until
        # now it lived only in the `runs` row -- which `reindex` rebuilds from
        # files and therefore cannot restore. Stamp it into the surviving
        # capture's header so a rebuild is lossless and a stranger reading the
        # file can see how many attempts stand behind it.
        stamp_repeat(best["output"], len(attempts), hits)
        if record:
            c = con()
            c.execute("INSERT INTO runs (issue_number, compiler, cmd, exit_code,"
                      " timed_out, output_path, verdict, note, ran_at)"
                      " VALUES (?,?,?,?,?,?,?,?,?)",
                      (issue, compiler, "(see single runs)", best["exit"],
                       int(best["timed_out"]), best["output"], best["verdict"],
                       f"{match_file} ({hits}/{len(attempts)} runs)", now()))
            c.commit()
        return best

    d = issue_dir(issue)
    out_path = probe_path(d, compiler, match_file, label)
    # Refuse to replace a capture that measured a different question, and do it
    # before running anything: the check is a header read, and a guard that
    # only fires after a two-minute Debug compile is one people learn to skip.
    # The filename now carries the predicate, so this can only fire when a
    # predicate is renamed or a label is reused across predicates -- but that
    # is exactly the case where the overwrite is silent and unrecoverable,
    # because the two probes may not even share a command line.
    if os.path.isfile(out_path) and not force:
        prior = read_out(out_path)[0].get("match", "match.json")
        if prior != match_file:
            sys.exit(
                f"refusing to overwrite {os.path.basename(out_path)}: it was "
                f"captured under {prior}, this run scores {match_file}. "
                f"A probe of a different predicate is a different measurement "
                f"-- give it its own --label, or pass --force if you really "
                f"mean to discard the old one.")
    exe = resolve_compiler(compiler)
    cmd_path = os.path.join(d, "cmd.txt")
    if args:
        # A translated variant changes the shader stage, so it cannot reuse the
        # repro's arguments -- #1702's compute translation of a pixel repro
        # needs -T cs_6_0. The header records exactly what ran, so provenance
        # survives the arguments differing.
        cmds = [args]
        # ...but --args supersedes cmd.txt silently, and an unlabelled --args
        # run overwrites the PRIMARY capture with a command cmd.txt does not
        # specify. `reindex` catches the resulting mismatch, and `reindex` is a
        # collation-only command, so on #3259 the primary capture sat stale for
        # the length of the triage. Say it at capture time instead.
        if not label and os.path.isfile(cmd_path):
            with open(cmd_path) as f:
                current = " ; ".join(ln.strip() for ln in f
                                     if ln.strip() and not ln.startswith("#"))
            if current and current != args:
                print(f"  warning: --args differs from cmd.txt and this run "
                      f"has no --label, so it replaces the primary capture "
                      f"with a command cmd.txt does not specify. Update "
                      f"cmd.txt, or give this probe its own --label.",
                      file=sys.stderr)
    else:
        with open(cmd_path) as f:
            cmds = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    # A control is the same command pointed at a different shader, so that the
    # only thing differing between it and the repro is the thing under test.
    # Making this a flag rather than a manual invocation is deliberate: #3038's
    # control was run by hand, its result was published in a draft comment, and
    # the output was never captured -- the claim survived only in the
    # operator's head. A control nobody can re-run is not a control.
    if shader:
        cmds = retarget_cmds(cmds, shader)

    requested_cmds = list(cmds)
    reject_windows_dash_fc(cmds)
    probe = _run_probe_command_list(
        exe, d, cmds, protect_cmds=requested_cmds, sync_outputs=True)
    worst_rc, timed_out, text = (
        probe["rc"], probe["timed_out"], probe["text"])
    observations = probe["observations"]
    verdict, reason = classify(issue, text, worst_rc, timed_out, match_file,
                               explain=True)
    spelling_reprobes = []
    spelling_evidence = []
    # "Unknown argument" is not yet evidence that the feature is absent. Older
    # releases may accept an underscore or slash spelling of the same option.
    # A failed old driver can also be completely silent, so the diagnostic is
    # not the trigger of record: for a silent failure, try each option token.
    #
    # Acceptance is behavioural. The candidate must change the issue's own
    # predicate relative to the same command with that option removed, and at
    # least one positive anchor must hold. This rejects the Windows `/` trap,
    # where an unknown option exits zero because it was silently ignored.
    for _ in range(8):
        rejected = unknown_argument_token(text) \
            if verdict == "invalid-probe" else None
        silent_failure = (
            worst_rc not in (0, None)
            and not timed_out
            and all(not str(out).strip() and not str(err).strip()
                    for _rc, _to, out, err in observations)
            and not is_internal_failure(text, worst_rc, timed_out)
        )
        targets = [rejected] if rejected else (
            command_option_tokens(cmds)
            if silent_failure and _has_positive_clause(issue, match_file)
            else [])
        if not targets:
            break
        accepted = None
        for target in targets:
            baseline_cmds = remove_argument(cmds, target)
            if not baseline_cmds:
                continue
            baseline = _run_probe_command_list(
                exe, d, baseline_cmds, protect_cmds=requested_cmds)
            for candidate in argument_spelling_variants(target):
                candidate_cmds = replace_argument_spelling(
                    cmds, target, candidate)
                if not candidate_cmds:
                    continue
                trial = _run_probe_command_list(
                    exe, d, candidate_cmds, protect_cmds=requested_cmds)
                candidate_rejected = unknown_argument_token(trial["text"])
                if candidate_rejected \
                        and candidate_rejected.lower() == candidate.lower():
                    continue
                candidate_verdict = classify(
                    issue, trial["text"], trial["rc"], trial["timed_out"],
                    match_file)
                evidence = spelling_reprobe_evidence(
                    issue, match_file, trial, baseline)
                if candidate_verdict == "invalid-probe" or not evidence:
                    continue
                # Run once more to preserve the accepted spelling's generated
                # outputs. It is still isolated, and must show the same proof.
                final = _run_probe_command_list(
                    exe, d, candidate_cmds, protect_cmds=requested_cmds,
                    sync_outputs=True)
                final_evidence = spelling_reprobe_evidence(
                    issue, match_file, final, baseline)
                final_verdict = classify(
                    issue, final["text"], final["rc"], final["timed_out"],
                    match_file)
                if final_verdict == "invalid-probe" \
                        or final_evidence != evidence:
                    continue
                accepted = (target, candidate, candidate_cmds, final,
                            final_evidence)
                break
            if accepted:
                break
        if not accepted:
            if silent_failure and verdict == "no-repro":
                verdict = "invalid-probe"
                reason = ("the compiler failed with no output and no spelling "
                          "variant produced the predicate's positive anchor")
            break
        rejected, candidate, cmds, probe, evidence = accepted
        worst_rc, timed_out, text = (
            probe["rc"], probe["timed_out"], probe["text"])
        observations = probe["observations"]
        spelling_reprobes.append((rejected, candidate))
        spelling_evidence.append(evidence)
        verdict, reason = classify(issue, text, worst_rc, timed_out, match_file,
                                   explain=True)
    if spelling_reprobes:
        print("  spelling re-probe accepted: " + ", ".join(
            f"{old} -> {new}" for old, new in spelling_reprobes),
            file=sys.stderr)

    # `classify`'s absence guard cannot demote this case (see
    # `_has_positive_clause`), so warn instead of silently recording a
    # reproduction that measured nothing. Narrow on purpose: only when the
    # predicate is absence-only AND the compile actually failed.
    if verdict == "repro" and (worst_rc or timed_out) \
            and _is_absence_predicate(issue, match_file) \
            and not _has_positive_clause(issue, match_file):
        print(f"  warning: {match_file} defines the symptom only by absence, "
              f"and this probe failed (exit 0x{(worst_rc or 0) & 0xFFFFFFFF:08X})"
              f" -- an absence clause is satisfied for free by a run that never "
              f"reached the code under test, and an ordinary diagnosed error "
              f"trips neither of classify()'s demotion arms. Anchor the "
              f"predicate with a positive clause before scanning releases.",
              file=sys.stderr)
    # Variants are stored under a name reindex will not score against the
    # primary predicate: a control that legitimately behaves differently from
    # the repro is not a disagreement to investigate. The `variant:` header
    # names the shader so the completeness audit can tell a control that was
    # captured from one that was only ever run by hand.
    subject = shader or next(
        (t for t in cmds[0].split() if t.lower().endswith(".hlsl")), "?")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# compiler: {compiler}\n# exe: {display_exe(exe)}\n"
                f"# ran: {now()}\n# cmd: {' ; '.join(cmds)}\n"
                + (f"# requested-cmd: {' ; '.join(requested_cmds)}\n"
                   f"# argument-spelling-reprobe: "
                   + ", ".join(f"{old} -> {new}"
                               for old, new in spelling_reprobes) + "\n"
                   + "# argument-spelling-evidence: "
                   + " | ".join(spelling_evidence) + "\n"
                   if spelling_reprobes else "")
                + f"# exit: {worst_rc}\n# timed_out: {int(timed_out)}\n"
                f"# match: {match_file}\n# verdict: {verdict}\n"
                + (f"# invalid-probe-reason: {reason}\n" if reason else "")
                + (f"# variant: {label} ({subject})\n" if label else "")
                + (f"# expect: {expect}\n" if expect else "")
                + (f"# expectation-kind: hypothesis\n"
                   f"# outcome: {expectation_outcome(expect, verdict)}\n"
                   if hypothesis else "")
                + f"\n{text}")

    if record and not label:
        c = con()
        c.execute("INSERT INTO runs (issue_number, compiler, cmd, exit_code,"
                  " timed_out, output_path, verdict, note, ran_at)"
                  " VALUES (?,?,?,?,?,?,?,?,?)",
                  (issue, compiler, " ; ".join(cmds), worst_rc, int(timed_out),
                   out_path, verdict, match_file, now()))
        c.commit()
    return {"compiler": compiler, "exit": worst_rc, "timed_out": timed_out,
            "verdict": verdict, "output": out_path, "text": text}


def expectation_violated(expect, verdict):
    """True when a control did not do what it was declared to do.

    A control's value is entirely in its expected result, and that expectation
    is knowledge that otherwise lives only in prose. Recording it turns the
    control into an assertion `reindex` can re-check forever.

    Both directions are real. #3009's control must NOT match -- a predicate
    that fires on a correct shader cannot discriminate. #1803's control must
    match: it is the same shader declared column_major, so identical DXIL is
    what proves the row_major attribute is ignored. Warning on a match alone
    would call that finding a bug.

    `invalid-probe` is a third answer and satisfies neither: `no-match` claims
    the compiler ran the test and the symptom was absent, and a probe that
    never compiled the repro has not shown that. Found on #8527, where a
    deliberate `error: invalid profile cs_6_6` demonstration passed as a clean
    `no-match` -- the same "an absence predicate is satisfied by a failed
    parse" class the runner already guards elsewhere. Declare `--expect
    invalid-probe` when *that* is the claim.
    """
    if expect not in ("match", "no-match", "invalid-probe"):
        return False
    if expect == "invalid-probe" or verdict == "invalid-probe":
        return verdict != expect
    return (verdict == "repro") != (expect == "match")


def expectation_outcome(expect, verdict):
    """Classify a recorded prediction without turning it into an assertion."""
    if expect not in ("match", "no-match", "invalid-probe"):
        return None
    return "refuted" if expectation_violated(expect, verdict) else "supported"


def captured_expectation_issue(meta, verdict):
    """Return a stale-hypothesis or failed-control problem, if any."""
    expect = meta.get("expect")
    if meta.get("expectation-kind") == "hypothesis":
        wanted = expectation_outcome(expect, verdict)
        if wanted is None:
            return ("hypothesis",
                    "hypothesis capture has no valid expectation")
        if meta.get("outcome") != wanted:
            return ("hypothesis",
                    f"hypothesis outcome says {meta.get('outcome') or 'nothing'}"
                    f", re-score says {wanted}")
        return None
    if expectation_violated(expect, verdict):
        return ("control", f"expected {expect}, scored {verdict}")
    return None


def ground_truth_compiler(issue):
    """Which non-release compiler this issue's existing captures were taken with.

    Returns an id, or None if there is no unambiguous answer.

    Measured on #2923: the symptom lives in a PIX pass `dxc.exe` never runs, so
    the issue was registered against a harness compiler (`main-debug-pix`).
    A later `triage.py run --issue 2923` -- no `--compiler` -- silently fell
    back to `main-debug`, compiled the repro with plain `dxc`, scored a
    perfectly plausible `no-repro`, and wrote a DB row contradicting the two
    `repro` rows already there. Nothing in the output said which compiler had
    been chosen for you. A default that is right for most issues is exactly the
    kind that is not noticed when it is wrong.
    """
    d = issue_dir(issue)
    if not os.path.isdir(d):
        return None
    ids = set()
    for name in os.listdir(d):
        m = re.fullmatch(r"out-(.+)\.txt", name)
        if m and not m.group(1).startswith("v"):
            ids.add(m.group(1))
    return ids.pop() if len(ids) == 1 else None


def cmd_run(a):
    if a.compiler is None:
        recorded = ground_truth_compiler(a.issue)
        a.compiler = recorded or "main-debug"
        if recorded and recorded != "main-debug":
            print(f"note: no --compiler given; using {recorded}, which is what "
                  f"this issue's existing captures used. Pass --compiler "
                  f"main-debug explicitly if you really want plain dxc.",
                  file=sys.stderr)
    if a.label and not (a.shader or a.args):
        sys.exit("--label needs --shader (a control: same arguments, different "
                 "source) or --args (a translation: different stage)")
    if (a.shader or a.args) and not a.label:
        sys.exit("--shader/--args need --label, so the output is filed as a "
                 "variant rather than overwriting the repro's probe")
    if getattr(a, "hypothesis", False) and not a.label:
        sys.exit("--hypothesis needs a labelled --shader/--args variant, so "
                 "the tested prediction cannot overwrite primary evidence")
    r = execute(a.issue, a.compiler, a.match, repeat=a.repeat,
                shader=a.shader, label=a.label, args=a.args, expect=a.expect,
                force=getattr(a, "force", False),
                hypothesis=getattr(a, "hypothesis", False))
    extra = ""
    if r.get("attempts", 1) > 1:
        extra = f" [{r['hits']}/{r['attempts']} runs showed it]"
    print(f"{r['compiler']}: exit={r['exit']} timed_out={r['timed_out']}"
          f" -> {r['verdict']}{extra}")
    print(f"output: {r['output']}")
    if getattr(a, "hypothesis", False):
        print(f"hypothesis {expectation_outcome(a.expect, r['verdict'])}: "
              f"expected {a.expect}, scored {r['verdict']}")
    elif expectation_violated(a.expect, r["verdict"]):
        print(f"WARNING: control expected {a.expect} but scored {r['verdict']}."
              f" Either the predicate does not discriminate, or the control is"
              f" not what you think it is.")
    elif a.label and not a.expect:
        print("note: no --expect recorded, so nothing re-checks this control "
              "on reindex.")
    if a.show:
        print("\n" + r["text"])


# Statuses that exist only in an assert-enabled build. Every release binary is
# a Release build, where `assert` is `((void)0)` under NDEBUG, so a symptom
# that manifests only as one of these is structurally unobservable in all of
# them -- they are valid probes of a question they cannot answer.
ASSERT_ONLY_STATUS = frozenset((0x80000003, 0xE0000001))


def warn_release_blind(issue, state):
    """Warn when "no release shows it" is an artefact of NDEBUG, not a fix.

    Measured on #2191: the symptom is an `assert` in Sema, so the Debug ground
    truth exits 0xE0000001 while all 20 release binaries compile the repro
    successfully and emit correct DXIL. `bisect` duly reported
    `never-repro'd-in-releases`, which reads as "no shipped compiler ever had
    this bug" and is one short step from "it was never real".

    SKILL.md warns about NDEBUG once, in the *ground-truth build* section, and
    never carries it forward to the release axis -- where the whole bisection
    runs on Release binaries. This is the carry-forward.
    """
    if not state.startswith("never-repro"):
        return
    gt = os.path.join(issue_dir(issue), "out-main-debug.txt")
    if not os.path.isfile(gt):
        return
    meta = read_out(gt)[0]
    try:
        rc = int(meta.get("exit", "")) & 0xFFFFFFFF
    except ValueError:
        return
    if meta.get("verdict") == "repro" and rc in ASSERT_ONLY_STATUS:
        print(f"\nWARNING: the ground-truth probe failed with 0x{rc:08X}, a status "
              f"only an assert-enabled build produces. Release binaries have "
              f"asserts compiled out (NDEBUG), so they CANNOT show this symptom "
              f"and this result is not evidence of a fix. Say so in --history; "
              f"\"never-repro'd-in-releases\" alone will be read as \"never real\".",
              file=sys.stderr)


def is_dxc_binary(path):
    """Whether an executable path names the real dxc driver."""
    if not path:
        return False
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1].lower() in ("dxc", "dxc.exe")


def refuse_harness_bisect(issue):
    """Hard-error when an issue's ground truth is a harness, not dxc.

    `bisect` swaps in each release's dxc executable. That is correct only when
    the registered ground-truth executable is itself dxc; against an API or
    pass harness it silently answers a different question and has repeatedly
    produced the plausible inverse verdict.
    """
    compiler = ground_truth_compiler(issue)
    if not compiler:
        return
    row = con().execute("SELECT exe_path FROM compilers WHERE id = ?",
                        (compiler,)).fetchone()
    path = row["exe_path"] if row else None
    capture = os.path.join(issue_dir(issue), f"out-{compiler}.txt")
    if not path and os.path.isfile(capture):
        path = read_out(capture)[0].get("exe")
    if path and not is_dxc_binary(path):
        sys.exit(
            f"refusing to bisect #{issue}: its registered ground-truth "
            f"compiler {compiler!r} is a harness ({path}), not dxc. bisect "
            f"would replace it with release dxc.exe files and answer a "
            f"different question. Use an explicit release matrix that holds "
            f"the harness fixed and varies the release DLL/executable (for "
            f"example measure.py --history).")


def release_exclusion_groups(rows):
    """Group non-bisectable catalog rows by the reason they were excluded."""
    groups = {"no usable dxc asset": [], "prerelease": [],
              "other non-bisectable release": []}
    for row in rows:
        if not row["asset_name"]:
            groups["no usable dxc asset"].append(row["tag"])
        elif row["prerelease"]:
            groups["prerelease"].append(row["tag"])
        else:
            groups["other non-bisectable release"].append(row["tag"])
    return {reason: tags for reason, tags in groups.items() if tags}


def release_exclusion_messages(rows):
    """Make every excluded catalog row visible, grouped by policy reason."""
    messages = []
    for reason, tags in release_exclusion_groups(rows).items():
        noun = "release" if len(tags) == 1 else "releases"
        if reason == "prerelease":
            prerelease_noun = "prerelease" if len(tags) == 1 else "prereleases"
            messages.append(
                f"skipped {len(tags)} {prerelease_noun} from search by policy: "
                f"{', '.join(tags)}")
        else:
            messages.append(
                f"skipped {len(tags)} {noun} ({reason}): {', '.join(tags)}")
    return messages


def issue_filing_names_release(issue_data, tag):
    """Whether the issue title/body explicitly names a catalog release."""
    text = "\n".join(str(issue_data.get(k) or "") for k in ("title", "body"))
    aliases = [tag]
    if tag.lower().startswith("v") and len(tag) > 1:
        aliases.append(tag[1:])
    return any(re.search(
        rf"(?<![A-Za-z0-9_.-]){re.escape(alias)}(?![A-Za-z0-9_.-])",
        text, re.IGNORECASE) for alias in aliases)


def prerelease_opt_ins(issue):
    """Read the issue's explicit, persistent prerelease-search exceptions."""
    path = os.path.join(issue_dir(issue), "release-policy.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            policy = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"cannot read {path}: {e}")
    if not isinstance(policy, dict):
        sys.exit(f"{path}: release policy must be a JSON object")
    tags = policy.get("include_prereleases", [])
    if (not isinstance(tags, list)
            or any(not isinstance(tag, str) or not tag.strip()
                   or tag != tag.strip() for tag in tags)):
        sys.exit(f"{path}: include_prereleases must be a list of release tags")
    if len(tags) != len(set(tags)):
        sys.exit(f"{path}: include_prereleases contains duplicate tags")
    return tags


def split_release_search_rows(rows, issue_data, include_prereleases=()):
    """Apply stable-release policy plus explicit, validated per-issue opt-ins."""
    by_tag = {row["tag"]: row for row in rows}
    for tag in include_prereleases:
        row = by_tag.get(tag)
        if not row:
            sys.exit(f"release-policy.json names unknown release {tag!r}")
        if not row["prerelease"]:
            sys.exit(f"release-policy.json names {tag}, which is a stable "
                     f"release and needs no prerelease opt-in")
        if not row["asset_name"]:
            sys.exit(f"release-policy.json names {tag}, but it has no usable "
                     f"dxc asset")
        if not issue_filing_names_release(issue_data, tag):
            sys.exit(f"release-policy.json names {tag}, but the issue title "
                     f"and body do not explicitly name that prerelease")

    opted_in = set(include_prereleases)
    included, excluded, included_prereleases = [], [], []
    for row in rows:
        explicit_opt_in = row["tag"] in opted_in
        if row["bisectable"] or explicit_opt_in:
            included.append(row)
            if explicit_opt_in:
                included_prereleases.append(row["tag"])
        else:
            excluded.append(row)
    return included, excluded, included_prereleases


def mid_history_window_warning(issue_data, release_rows, first_tag, last_tag,
                               state):
    """Warn when agreeing clean endpoints can hide the issue's own era."""
    if state != "never-repro'd-in-releases":
        return None
    created = str(issue_data.get("createdAt") or "")[:10]
    dates = {row["tag"]: str(row["build_date"] or "")[:10]
             for row in release_rows}
    first, last = dates.get(first_tag, ""), dates.get(last_tag, "")
    if first and created and last and first <= created <= last:
        return (
            f"warning: both endpoints are clean, but this issue was filed "
            f"{created}, inside the {first_tag}..{last_tag} release range. "
            f"Agreeing endpoints are the signature of a possible mid-history "
            f"regression window; rerun with --linear before treating "
            f"never-repro'd-in-releases as a result.")
    return None


def cmd_bisect(a):
    """Binary-search the release sequence for the behaviour transition.

    Checks both endpoints first and short-circuits when they agree, which is
    the common case and costs only two runs.

    Two assumptions are enforced rather than trusted, because both fail
    silently and both fake a regression:

    * Every probe must actually compile the repro. A release that predates the
      target profile rejects it outright, which is not a symptom verdict.
    * The symptom must be monotonic across the range. An issue that was fixed
      and later reverted violates that, and binary search over a
      non-monotonic predicate returns an arbitrary boundary. Pass --linear for
      those; it costs one run per release but cannot be fooled.
    """
    refuse_harness_bisect(a.issue)
    issue_path = os.path.join(issue_dir(a.issue), "issue.json")
    try:
        with open(issue_path, encoding="utf-8") as f:
            issue_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        issue_data = {}
    all_release_rows = list(con().execute(
        "SELECT tag, build_date, asset_name, prerelease, bisectable"
        " FROM releases WHERE tag <> '' ORDER BY build_date"))
    release_rows, excluded_rows, included_prereleases = split_release_search_rows(
        all_release_rows, issue_data, prerelease_opt_ins(a.issue))
    rels = [r["tag"] for r in release_rows]
    if not rels:
        sys.exit("no releases catalogued; run 'triage.py catalog'")
    if included_prereleases:
        print("  included prerelease(s) explicitly opted in by "
              "release-policy.json and named by the issue: "
              + ", ".join(included_prereleases))
    for message in release_exclusion_messages(excluded_rows):
        print(f"  {message}")
    probeable_prereleases = [r for r in excluded_rows
                             if r["asset_name"] and r["prerelease"]]
    excluded_note = (
        f"{len(probeable_prereleases)} probeable prerelease(s) excluded "
        f"from the search by policy"
    ) if probeable_prereleases else ""
    invalid_tags = set()
    warned_invalid_options = set()

    def probe(tag):
        r = execute(a.issue, tag, a.match, repeat=a.repeat)
        v = r["verdict"]
        if v == "invalid-probe":
            invalid_tags.add(tag)
            print(f"  {tag:<14} n/a (never compiled the repro -- profile, flag "
                  f"or feature unsupported)")
            token = unknown_argument_token(r.get("text", ""))
            key = token.lower() if token else None
            if key and key not in warned_invalid_options:
                warned_invalid_options.add(key)
                print("  " + invalid_option_range_warning(r["text"]))
            return None
        rate = f"  [{r['hits']}/{r['attempts']}]" if r.get("attempts", 1) > 1 else ""
        print(f"  {tag:<14} {v}{rate}")
        return v == "repro"

    if getattr(a, "linear", False):
        seq = [(t, probe(t)) for t in rels]
        usable = [(t, v) for t, v in seq if v is not None]
        if not usable:
            sys.exit("no release could run this repro; retarget it at a "
                     "profile/flag set the releases support")
        skipped = len(seq) - len(usable)
        runs = [usable[0]]
        for tag, v in usable[1:]:
            if v != runs[-1][1]:
                runs.append((tag, v))
        note_bits = []
        if skipped:
            note_bits.append(
                f"{skipped} release(s) in the search skipped as unprobeable")
        if excluded_note:
            note_bits.append(excluded_note)
        note = f" ({'; '.join(note_bits)})" if note_bits else ""
        if len(runs) == 1:
            state = f"{'always' if runs[0][1] else 'never'}-repro'd"
            print(f"\nresult: {state} across {usable[0][0]}..{usable[-1][0]}{note}")
            warn_release_blind(a.issue, state)
        else:
            print("\nresult: non-monotonic history" + note + ", transitions at " +
                  ", ".join(f"{t} -> {'repro' if v else 'no-repro'}"
                            for t, v in runs[1:]))
        return

    # Trim unprobeable releases off each end rather than aborting: an old build
    # that predates the feature under test is a floor on what history can show,
    # not a defect in the repro.
    while rels and probe(rels[0]) is None:
        rels.pop(0)
    while rels and probe(rels[-1]) is None:
        rels.pop()
    if len(rels) < 2:
        sys.exit("fewer than two releases can run this repro; no history "
                 "conclusion is possible")

    oldest = probe(rels[0])
    newest = probe(rels[-1])

    if oldest == newest:
        state = "always-repro'd" if oldest else "never-repro'd-in-releases"
        note_bits = []
        if invalid_tags:
            note_bits.append(
                f"{len(invalid_tags)} release(s) in the search skipped "
                f"as unprobeable")
        if excluded_note:
            note_bits.append(excluded_note)
        note = f" ({'; '.join(note_bits)})" if note_bits else ""
        print(f"\nresult: {state} across {rels[0]}..{rels[-1]}{note}")
        warning = mid_history_window_warning(
            issue_data, release_rows, rels[0], rels[-1], state)
        if warning:
            print(warning)
        warn_release_blind(a.issue, state)
        return

    # Invariant: rels[lo] behaves like `oldest`, rels[hi] like `newest`.
    lo, hi = 0, len(rels) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        v = probe(rels[mid])
        if v is None:
            sys.exit(
                f"{rels[mid]} is unprobeable inside the candidate boundary. "
                f"Binary search cannot treat an unexercised release as either "
                f"side of the transition; rerun with --linear and report the "
                f"residual interval explicitly.")
        lo, hi = (mid, hi) if v == oldest else (lo, mid)

    note_bits = []
    if invalid_tags:
        note_bits.append(
            f"{len(invalid_tags)} release(s) in the search skipped as "
            f"unprobeable")
    if excluded_note:
        note_bits.append(excluded_note)
    note = f"; {'; '.join(note_bits)}" if note_bits else ""

    if oldest and not newest:
        print(f"\nresult: fixed-in {rels[hi]} "
              f"(last repro: {rels[lo]}{note})")
    else:
        print(f"\nresult: regressed-in {rels[hi]} "
              f"(last good: {rels[lo]}{note})")


# --------------------------------------------------------------------------
# labels
# --------------------------------------------------------------------------
#
# The label taxonomy is repo state, not a constant: labels get added, renamed
# and retired. Nothing here may hardcode a label list. Proposals are always
# validated against a freshly fetched set, so a label that no longer exists
# cannot be recommended.

LABELS_MAX_AGE_HOURS = 24


def refresh_labels():
    """Fetch the live label taxonomy.

    `gh label list` goes through the GraphQL API, which has its own rate-limit
    budget: on #8732 it died with an unhandled traceback mid-triage while the
    REST budget still showed 4991/5000 remaining. The REST labels endpoint
    answers the same question from the other budget, so fall back to it rather
    than making a rate limit on one API a hard stop for the whole session.
    """
    try:
        rows = json.loads(gh("label", "list", "--repo", REPO, "--limit", "500",
                             "--json", "name,description"))
    except subprocess.CalledProcessError as e:
        print(f"  warning: 'gh label list' failed ({e}); falling back to the "
              f"REST labels endpoint (a separate rate-limit budget)",
              file=sys.stderr)
        rows = json.loads(gh("api", f"repos/{REPO}/labels", "--paginate"))
    c = con()
    c.execute("DELETE FROM labels")
    c.executemany("INSERT INTO labels (name, description, fetched_at)"
                  " VALUES (?,?,?)",
                  [(r["name"], r.get("description") or "", now())
                   for r in rows])
    c.commit()
    return rows


def known_labels(auto_refresh=True):
    """Current labels, refetched when missing or stale."""
    c = con()
    rows = list(c.execute("SELECT name, description, fetched_at FROM labels"))
    if not rows:
        if not auto_refresh:
            sys.exit("no label cache; run 'triage.py labels --refresh'")
        print("  (fetching label list)")
        refresh_labels()
        rows = list(c.execute(
            "SELECT name, description, fetched_at FROM labels"))
    else:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(
            rows[0]["fetched_at"])
        if age.total_seconds() > LABELS_MAX_AGE_HOURS * 3600:
            print(f"  warning: label cache is {age.days}d old; "
                  "re-run with --refresh before trusting proposals")
    return {r["name"]: r["description"] for r in rows}


def validate_labels(spec, known):
    """Reject anything not in the live taxonomy, suggesting near misses."""
    names = [s.strip() for s in (spec or "").split(",") if s.strip()]
    bad = [n for n in names if n not in known]
    if bad:
        for n in bad:
            lower = n.lower()
            near = [k for k in known
                    if lower in k.lower() or k.lower() in lower]
            hint = f" (did you mean: {', '.join(near[:3])}?)" if near else ""
            print(f"  unknown label: {n!r}{hint}", file=sys.stderr)
        sys.exit("label proposal rejected; taxonomy may have changed")
    return names


def cmd_labels(a):
    if a.refresh:
        rows = refresh_labels()
        print(f"refreshed: {len(rows)} labels")
    known = known_labels()
    if a.issue:
        r = con().execute("SELECT labels, labels_add, labels_remove FROM"
                          " issues WHERE number = ?", (a.issue,)).fetchone()
        if not r:
            sys.exit(f"#{a.issue} not in the index; run 'fetch' first")
        cur = [x.strip() for x in (r["labels"] or "").split(",") if x.strip()]
        print(f"#{a.issue} now:      {', '.join(cur) or '(none)'}")
        print(f"#{a.issue} proposed +{r['labels_add'] or ''} "
              f"-{r['labels_remove'] or ''}")
        gone = [x for x in cur if x not in known]
        if gone:
            print(f"  note: no longer in the taxonomy: {', '.join(gone)}")
        return
    for name, desc in sorted(known.items(), key=lambda kv: kv[0].lower()):
        print(f"{name:<30} {desc[:64]}")
    print(f"\n{len(known)} labels")


# --------------------------------------------------------------------------
# Compiler Explorer (godbolt.org)
# --------------------------------------------------------------------------
#
# Shareable repro links. Two caveats that matter for triage:
#   * CE runs Linux *Release* builds, so asserts are compiled out exactly as
#     they are in shipping releases. A Debug-only assert will look clean here.
#     CE corroborates a repro; it never overrules the local Debug build.
#   * CE's oldest DXC is 1.6.2112, newer than the local bisect floor
#     (v1.4.1907), so it cannot date a fix that predates it.

CE = "https://godbolt.org"

# Local release tag -> CE compiler id, for the releases CE also carries.
CE_COMPILERS = {
    "v1.6.2112": "dxc_1_6_2112", "v1.7.2207": "dxc_1_7_2207",
    "v1.7.2212": "dxc_1_7_2212", "v1.7.2308": "dxc_1_7_2308",
    "v1.8.2403": "dxc_1_8_2403", "v1.8.2405": "dxc_1_8_2405",
    "v1.8.2407": "dxc_1_8_2407", "v1.8.2502": "dxc_1_8_2502",
    "v1.8.2505": "dxc_1_8_2505", "v1.8.2505.1": "dxc_1_8_2505_1",
    "v1.9.2602": "dxc_1_9_2602", "v1.9.2607": "dxc_1_9_2607",
}
CE_OLDEST = "dxc_1_6_2112"
CE_TRUNK = "dxc_trunk"


def ce_post(path, payload):
    import urllib.request
    req = urllib.request.Request(
        CE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def ce_get_json(path):
    import urllib.request
    req = urllib.request.Request(
        CE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def ce_args(issue, include_count=False):
    """Turn cmd.txt into CE user arguments: drop the source file name.

    Only a *positional* source file is dropped (CE supplies the source
    itself). A filename that is the value of a flag -- `-include forced.h`,
    `-Fo out.dxil` -- is kept, otherwise the flag would be left dangling and
    the resulting error would be an artefact of this function rather than the
    behaviour under test.

    "Value of a flag" is decided by the same VALUE_FLAGS table `retarget_cmd`
    uses, not by "the previous token began with a dash". Most dxc flags take no
    value, so the dash test kept the source file after any of them -- measured
    on #8732, whose cmd.txt ends `-spirv repro.hlsl`: CE was handed a second,
    nonexistent input alongside the pane's own source, and every pane had to be
    written out by hand with an `id:<args>` override.

    Keep the historical two-value return by default for issue-local scripts;
    the built-in publisher opts into the invocation count.
    """
    d = issue_dir(issue)
    with open(os.path.join(d, "cmd.txt")) as f:
        lines = [ln.strip() for ln in f
                 if ln.strip() and not ln.startswith("#")]
    toks, values = command_token_roles(lines[0])
    keep = []
    for i, t in enumerate(toks):
        positional = i not in values
        if positional and os.path.exists(os.path.join(d, t)):
            continue
        keep.append(t)
    result = (subprocess.list2cmdline(keep), lines[0])
    return result + (len(lines),) if include_count else result


def ce_compiler_specs(spec, default_args, override_reason=None):
    """Resolve CE compiler specs, requiring explicit args when inference is unsafe."""
    compilers = []
    missing_overrides = []
    for entry in spec.split(","):
        entry = entry.strip()
        if not entry:
            continue
        cid, _, override = entry.partition(":")
        override = override.strip()
        if override_reason and not override:
            missing_overrides.append(cid)
        compilers.append((cid, override or default_args))
    if missing_overrides:
        sys.exit(
            f"{override_reason}; give explicit id:<args> overrides for every "
            f"pane (missing: {', '.join(missing_overrides)})")
    return compilers


def write_godbolt_verify(directory, content):
    """Write the latest CE verification and archive any differing predecessor."""
    path = os.path.join(directory, "manual-case-godbolt-verify.txt")
    archived = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
        if old != content:
            digest = hashlib.sha256(old.encode("utf-8")).hexdigest()[:12]
            archived = os.path.join(
                directory, f"manual-case-godbolt-verify-{digest}.txt")
            if not os.path.exists(archived):
                with open(archived, "w", encoding="utf-8", newline="\n") as f:
                    f.write(old)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return path, archived


def reject_windows_dash_fc(cmds, platform=None):
    """Refuse `-Fc -` on Windows, where `-` is a literal output filename."""
    if (platform or os.name) != "nt":
        return
    for line in cmds:
        toks = split_cmd(line)
        for i, tok in enumerate(toks):
            separate = option_key(tok) == "-fc" \
                and i + 1 < len(toks) and toks[i + 1] == "-"
            joined = re.fullmatch(r"(?i)[/-]fc(?::|=)?-", tok) is not None
            if separate or joined:
                raise SystemExit(
                    "`-Fc -` does not mean stdout on Windows: dxc creates a "
                    "literal file named `-`, so a stdout predicate sees "
                    "nothing. Use a real output filename and a harness that "
                    "reads it.")


# DXC emits the resource-binding table and signature tables as *comments* in
# its DXIL output, so CE's default "remove comment-only lines" filter throws
# away exactly the evidence a triage link needs. Keep the output faithful.
CE_FILTERS = {"execute": False, "intel": False, "demangle": False,
              "labels": False, "directives": False, "commentOnly": False,
              "trim": False, "binary": False}


def ce_compile(source, compiler, args):
    res = ce_post(f"/api/compiler/{compiler}/compile", {
        "source": source, "lang": "hlsl", "compiler": compiler,
        "options": {
            "userArguments": args,
            "compilerOptions": {"skipAsm": False, "executorRequest": False},
            "filters": dict(CE_FILTERS),
            "tools": [], "libraries": [],
        },
        "allowStoreCodeDebug": True,
    })
    text = "\n".join(x.get("text", "") for stream in ("stdout", "stderr")
                     for x in res.get(stream, []))
    asm = "\n".join(x.get("text", "") for x in res.get("asm", [])
                    if isinstance(x, dict))
    rc = res.get("code")
    # Reuse the local predicate so a repro is classified identically wherever
    # it runs. CE additionally reports crashes as shell-style signal codes
    # (139 = SIGSEGV, 134 = SIGABRT).
    crashed = is_internal_failure(text, rc, False) or \
        (isinstance(rc, int) and rc >= 128)
    return rc, (text + "\n" + asm).strip(), crashed


def annotate(issue, source):
    """Prepend the issue's 'what to look for' banner to the shared source.

    Kept in a separate godbolt-note.txt rather than in repro.hlsl so the repro
    stays exactly what was tested locally -- the annotation is presentation,
    not part of the evidence.
    """
    note_path = os.path.join(issue_dir(issue), "godbolt-note.txt")
    if not os.path.exists(note_path):
        return source
    rule = "//" + "=" * 74 + "//"
    body = open(note_path, encoding="utf-8").read().strip("\n")
    # The marker belongs to the renderer, not the note. Older issue notes
    # sometimes supplied it too, producing permanent `// //` CE banners.
    note_lines = [re.sub(r"^\s*//\s?", "", ln) for ln in body.splitlines()]
    lines = [f"// {ln}".rstrip() for ln in note_lines]
    return "\n".join([rule, *lines, rule, "", source.lstrip("\n")])


def cmd_godbolt(a):
    d = issue_dir(a.issue)
    c = con()
    if a.skip:
        c.execute("INSERT OR IGNORE INTO issues (number) VALUES (?)",
                  (a.issue,))
        c.execute("UPDATE issues SET godbolt_url = NULL, godbolt_skip = ?"
                  " WHERE number = ?", (a.skip, a.issue))
        c.commit()
        print(f"#{a.issue}: no link, deliberately — {a.skip}")
        return None

    # The published source is normally the repro that was tested locally, but
    # an issue may need a translated variant -- e.g. a compute-shader restating
    # of a pixel-shader repro, so Clang (whose stage support is uneven) can
    # answer the same question. Keep repro.hlsl as the stage-accurate local
    # evidence and record the substitution so later runs reuse it.
    name_path = os.path.join(d, "godbolt-source.txt")
    name = a.source
    if name is None:
        name = open(name_path).read().strip() \
            if os.path.exists(name_path) else "repro.hlsl"
    elif name == "repro.hlsl":
        if os.path.exists(name_path):
            os.remove(name_path)
    else:
        with open(name_path, "w", encoding="utf-8") as f:
            f.write(name + "\n")

    src_path = os.path.join(d, name)
    if not os.path.exists(src_path):
        sys.exit(f"no {name} for #{a.issue}")
    if name != "repro.hlsl":
        print(f"  publishing {name} (not repro.hlsl) for #{a.issue}")
    source = annotate(a.issue, open(src_path, encoding="utf-8").read())
    args, full, invocation_count = ce_args(a.issue, include_count=True)
    # A non-default compiler set (e.g. adding FXC for contrast) is worth
    # keeping: it is part of how the issue is demonstrated, so persist it
    # alongside the repro and reuse it on later runs.
    spec_path = os.path.join(d, "godbolt.txt")
    spec = a.compilers
    if spec is None:
        spec = open(spec_path).read().strip() if os.path.exists(spec_path) \
            else f"{CE_OLDEST},{CE_TRUNK}"
    else:
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(spec + "\n")
    # "id" uses the issue's own arguments; "id:<args>" overrides them, which
    # is how a contrasting compiler (e.g. FXC, with /T instead of -T) is put
    # side by side with DXC in one link.
    override_reasons = []
    if name != "repro.hlsl":
        override_reasons.append(
            f"--source {name} changes the source and its profile cannot be "
            "inferred")
    if invocation_count > 1:
        override_reasons.append(
            f"cmd.txt has {invocation_count} invocations and Compiler "
            "Explorer can compile only one command per pane")
    compilers = ce_compiler_specs(
        spec, args, "; ".join(override_reasons) or None)

    extra = [f for f in os.listdir(d) if f.endswith((".h", ".hlsli"))]
    if extra:
        print(f"  warning: repro references local file(s) {extra}; CE is "
              "single-file, so the link demonstrates only part of this issue")
    if not os.path.exists(os.path.join(d, "godbolt-note.txt")):
        print("  warning: no godbolt-note.txt; the link will not say what a "
              "reader should be looking at")

    print(f"#{a.issue}: dxc {full}\n  CE args: {args}")
    if not a.no_verify:
        # Print a one-line summary, but write the WHOLE pane output to disk.
        #
        # This loop used to print only each pane's first line, and that hid the
        # finding twice in one batch. On #3092 `hlsl_clang_trunk`'s first line
        # is a `-Qembed_debug` unused-argument warning; the result -- Clang
        # emitting DXC's diagnostic verbatim -- is on line 2. On #3377 the
        # first line was enough to see `SIGSEGV` but not to count Clang's 13
        # errors or confirm FXC had succeeded. Both workers ended up writing
        # their own CE client to get past it. The full text was already in
        # hand; only the printing threw it away.
        verify = [f"# Compiler Explorer panes for #{a.issue}, full output.",
                  f"# Written by `triage.py godbolt` -- rerun it to re-derive.",
                  f"# CE runs Linux Release builds: it corroborates the local",
                  f"# Debug build and never overrules it.", ""]
        for cid, cargs in compilers:
            rc, text, crashed = ce_compile(source, cid, cargs)
            first = next((ln for ln in text.splitlines() if ln.strip()), "")
            print(f"  {cid:<18} exit={rc}"
                  f"{' CRASH' if crashed else ''}  {first[:70]}")
            verify += ["=" * 74,
                       f"# compiler: {cid}",
                       f"# args:     {cargs}",
                       f"# exit:     {rc}{'  CRASH' if crashed else ''}",
                       "", text, ""]
        vpath, archived = write_godbolt_verify(d, "\n".join(verify))
        if archived:
            print(f"  archived previous panes: {os.path.basename(archived)}")
        print(f"  panes: {os.path.basename(vpath)}")

    url = ce_post("/api/shortener", {"sessions": [{
        "id": 1, "language": "hlsl", "source": source,
        "compilers": [{"id": cid, "options": ca, "filters": dict(CE_FILTERS),
                       "libs": []} for cid, ca in compilers],
    }]})["url"]

    # Read the link back before recording it. Three workers in batch 008
    # independently started doing this by hand, which is the signal that it
    # belongs in the tool: the shortener answers 200 with a URL whether or not
    # the session it stored is the one that was sent, and a link with the wrong
    # arguments or a dropped pane is worse than no link -- it is a claim a
    # reader will check.
    try:
        info = ce_get_json(f"/api/shortlinkinfo/{url.rsplit('/', 1)[-1]}")
        got = [c.get("id") for s in info.get("sessions", [])
               for c in s.get("compilers", [])]
        want = [cid for cid, _ in compilers]
        if got != want:
            print(f"  warning: link round-trips as {got}, not {want}")
        stored = (info.get("sessions") or [{}])[0].get("source", "")
        if stored.strip() != source.strip():
            print("  warning: the link's source is not the source that was "
                  "sent; do not cite this link")
    except Exception as e:
        print(f"  warning: could not verify the link ({e}); open it by hand")

    c.execute("INSERT OR IGNORE INTO issues (number) VALUES (?)", (a.issue,))
    c.execute("UPDATE issues SET godbolt_url = ?, godbolt_skip = NULL"
              " WHERE number = ?", (url, a.issue))
    c.commit()
    print(f"  link: {url}")
    return url


def write_verdict_json(number):
    """Mirror an issue's triage record next to its evidence.

    The database is a local cache, so without this the verdict fields would
    exist only on the machine that produced them -- a collaborator cloning the
    repo would get the evidence and none of the conclusions. Writing them here
    makes the tree the source of truth and gives verdict changes a reviewable
    text diff instead of an opaque binary one.
    """
    row = con().execute("SELECT * FROM issues WHERE number = ?",
                        (number,)).fetchone()
    if row is None:
        return None
    d = issue_dir(number)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "verdict.json")
    rec = {k: row[k] for k in row.keys() if row[k] is not None}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def cmd_verdict(a):
    provided = {k: v for k, v in vars(a).items()
                if k in ISSUE_FIELDS and v is not None}
    provided.setdefault("triaged_at", now())
    # Label proposals are checked against the live taxonomy at record time, so
    # a renamed or retired label is caught here rather than by a human trying
    # to apply it later.
    if provided.get("labels_add") or provided.get("labels_remove"):
        known = known_labels()
        for field in ("labels_add", "labels_remove"):
            if provided.get(field):
                names = validate_labels(provided[field], known)
                provided[field] = ", ".join(names)
    c = con()
    c.execute("INSERT OR IGNORE INTO issues (number) VALUES (?)", (a.issue,))
    c.execute(f"UPDATE issues SET {', '.join(f'{k} = ?' for k in provided)}"
              " WHERE number = ?", list(provided.values()) + [a.issue])
    c.commit()
    print(f"#{a.issue}: {len(provided)} field(s) recorded")
    write_verdict_json(a.issue)


def audit_issue(d, number, rec, collated=True):
    """Report artifacts a completed triage should have left behind.

    The other two reindex checks re-verify evidence that *exists*. This one
    looks for evidence that should exist and does not -- the failure mode that
    survives every mechanical check because there is nothing to check.

    It matters most when issues are triaged in parallel sessions, where a
    lesson learned on one issue cannot reach the others and collation is the
    only place a gap gets caught. Every entry below is a mistake already made:
    #3038 published a control result whose output was never captured, and the
    mandatory independent review ran on all three batches while leaving nothing
    on disk to prove it.

    `collated=False` is the per-issue worker's view: step 10's review is a
    *batch* step performed by a different model, so a correctly-executed worker
    session cannot satisfy it and reporting it as a gap teaches the worker that
    audit output is noise. It is listed separately there instead. Four of five
    workers in batch 004 independently reported this, and the fix is to make
    the reachable-clean state reachable, not to let anyone fill the field in.
    """
    gaps = []
    has = lambda f: os.path.isfile(os.path.join(d, f))
    files = os.listdir(d)

    if not has("expected.md"):
        gaps.append("no expected.md -- the symptom was never stated before "
                    "running (step 2)")

    # A shader that is not the repro is a control or a translated variant, and
    # exists only to be compared against it. If nothing captured its output,
    # any claim resting on it is unsupported -- exactly #3038.
    sources = set()
    if has("cmd.txt"):
        with open(os.path.join(d, "cmd.txt")) as f:
            for ln in f:
                if ln.strip() and not ln.startswith("#"):
                    prev = ""
                    for tok in ln.split():
                        if (tok.lower().endswith(".hlsl")
                                and not tok.startswith(("-", "/"))
                                and prev.lower().rstrip(":=") not in VALUE_FLAGS):
                            sources.add(tok)
                            break
                        prev = tok
    captured = set()
    for f in files:
        if f.startswith("variant-") and f.endswith(".txt"):
            meta, _ = read_out(os.path.join(d, f))
            m = re.search(r"\((.+)\)", meta.get("variant", ""))
            if m:
                captured.add(m.group(1))
    for shader in sorted(set(f for f in files if f.endswith(".hlsl"))
                         - sources - captured):
        gaps.append(f"{shader} has no captured output -- run it with "
                    f"`run --shader {shader} --label <name>`")

    # A control without a declared expectation is an observation, not an
    # assertion: nothing re-checks it, so a predicate change can quietly
    # invalidate the reasoning it supports. Only meaningful where there is a
    # predicate to assert against -- #3150 has none, and demanding one there
    # would be noise.
    for f in sorted(files):
        if f.startswith("variant-") and f.endswith(".txt"):
            meta, _ = read_out(os.path.join(d, f))
            mf = meta.get("match", "match.json")
            if os.path.isfile(os.path.join(d, mf)) and not meta.get("expect"):
                gaps.append(f"{f} has no `# expect:` -- re-run it with "
                            f"--expect match|no-match so reindex re-checks it")
            elif meta.get("expect"):
                problem = captured_expectation_issue(
                    meta, meta.get("verdict"))
                if problem:
                    kind, detail = problem
                    gaps.append(f"{f} has a failed {kind}: {detail}")

    if not rec:
        return gaps
    if not has("notes.md"):
        gaps.append("no notes.md (step 11)")
    if not has("comment.md"):
        gaps.append("no comment.md (step 9)")
    if not rec.get("reviewed_by") and collated:
        gaps.append("verdict.json has no reviewed_by -- the independent "
                    "review is mandatory and left no trace (step 10)")
    if not rec.get("triaged_by"):
        gaps.append("verdict.json has no triaged_by")
    if not (rec.get("godbolt_url") or rec.get("godbolt_skip")):
        gaps.append("neither a Compiler Explorer link nor a recorded reason "
                    "for skipping one (step 7)")
    return gaps


def cmd_audit(a):
    """Read-only completeness check for one issue, or for all of them.

    Exists because the only way to get `audit_issue` used to be `reindex`,
    which begins `DELETE FROM issues; DELETE FROM runs;` and rebuilds from
    whatever is on disk at that instant. Under the parallel per-issue model
    that is a shared-state write: in batch 004 every one of five workers ran it
    as instructed, and two had their own in-flight rows -- title, labels, and a
    published Compiler Explorer link -- deleted by a peer.

    This touches no tables at all, so a worker can run it as often as they
    like. It is the check they actually wanted.
    """
    numbers = [a.issue] if a.issue else sorted(
        int(n) for n in os.listdir(ISSUES) if n.isdigit()) \
        if os.path.isdir(ISSUES) else []
    total = 0
    for number in numbers:
        d = issue_dir(number)
        if not os.path.isdir(d):
            sys.exit(f"no evidence directory for #{number}")
        vpath = os.path.join(d, "verdict.json")
        rec = {}
        if os.path.isfile(vpath):
            with open(vpath, encoding="utf-8") as f:
                rec = json.load(f)
        gaps = audit_issue(d, number, rec, collated=a.collated)
        for g in gaps:
            print(f"#{number}: {g}")
        total += len(gaps)
        if rec and not rec.get("reviewed_by") and not a.collated:
            print(f"#{number}: pending collation -- no reviewed_by yet (step 10 "
                  f"is a batch step; do not fill it in yourself)")
    path_failures = audit_path_hygiene(a.issue)
    for failure in path_failures:
        prefix = f"#{a.issue}: " if a.issue else ""
        print(f"{prefix}path hygiene: {failure}")
    total += len(path_failures)
    if not a.issue:
        total += audit_overview()
    if not total:
        print(f"no missing evidence in {len(numbers)} issue(s)")
    return 1 if total else 0


def audit_path_hygiene(issue=None):
    """Run the canonical path gate over one issue or the whole skill tree."""
    import check_paths
    failures, _, _, _ = check_paths.scan(issue=issue)
    return failures


def audit_overview():
    """Report a `reports/overview.md` older than the evidence it summarises.

    The overview is the cross-batch answer to "what do we do next?", and it is
    generated, so the only way it goes wrong is by not being regenerated. That
    failure is invisible -- a stale overview is a well-formed document that
    quietly omits the newest batch. Comparing mtimes catches it without
    re-rendering, and a whole-batch audit is exactly when it matters.
    """
    overview = os.path.join(REPORTS, "overview.md")
    if not os.path.isdir(ISSUES):
        return 0
    verdicts = [os.path.join(ISSUES, n, "verdict.json")
                for n in os.listdir(ISSUES) if n.isdigit()]
    verdicts = [p for p in verdicts if os.path.isfile(p)]
    if not verdicts:
        return 0
    newest = max(verdicts, key=os.path.getmtime)
    if not os.path.exists(overview):
        print("reports/overview.md is missing -- run "
              "`python scripts/render_overview.py`")
        return 1
    if os.path.getmtime(overview) < os.path.getmtime(newest):
        rel = os.path.relpath(newest, ISSUES).replace(os.sep, "/")
        print(f"reports/overview.md is older than {rel} -- regenerate it with "
              f"`python scripts/render_overview.py`")
        return 1
    return 0


def restamp(path, field, value):
    """Rewrite one derived header field in a capture, leaving the rest alone.

    `# verdict:` is not a measurement -- it is `classify()` applied to the
    text below it. When the predicate code improves, every archived header
    derived under the old code disagrees, and `reindex` says so. That report is
    the point of the command, but without a way to ACCEPT a correction it never
    clears, and a permanent list of known-stale lines is where the next real
    disagreement goes to hide.

    Only the named field moves. The command line, exit status and captured
    output are what was actually observed and are never touched here.
    """
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        if ln.startswith(f"# {field}:"):
            lines[i] = f"# {field}: {value}\n"
            break
    else:
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)
    return True


def cmd_expect(a):
    """Correct a capture's declared expectation, and nothing else.

    When a predicate improves, declarations made under the old one become
    wrong, and `reindex` reports them -- which is the system working. But the
    only way to answer used to be re-running the compiler (destroying the
    archived measurement, possibly against a different build) or hand-editing
    the header (unauditable, and one slip from editing `# exit:`).

    An expectation is an assertion by the analyst, not a measurement, so it is
    legitimate to revise it in place. This rewrites the `# expect:` line and
    refuses to touch anything else, then re-scores the untouched output so the
    correction is checked rather than asserted.
    """
    d = issue_dir(a.issue)
    path = os.path.join(d, a.capture)
    if not os.path.isfile(path):
        sys.exit(f"no such capture: {path}")
    meta, text = read_out(path)
    if "exit" not in meta:
        sys.exit(f"{a.capture} has no recorded exit status; it is not a capture")
    if meta.get("expectation-kind") == "hypothesis":
        sys.exit("refusing to rewrite a tested hypothesis after seeing its "
                 "outcome; re-run a newly labelled hypothesis instead")

    mf = meta.get("match", "match.json")
    v = classify_capture(a.issue, meta, text, mf)
    if expectation_violated(a.expect, v):
        sys.exit(f"refusing: {a.capture} scores {v!r}, so declaring "
                 f"{a.expect!r} would be false on the next reindex")

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        if ln.startswith("# expect:"):
            was = ln.split(":", 1)[1].strip()
            lines[i] = f"# expect: {a.expect}\n"
            break
    else:
        sys.exit(f"{a.capture} has no `# expect:` line; re-run it with --expect")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)
    print(f"#{a.issue} {a.capture}: expect {was} -> {a.expect} "
          f"(scores {v}; measurement untouched)")
    if a.why:
        print(f"  reason: {a.why} -- put this in notes.md too")


def cmd_reindex(a):
    """Rebuild the database from the committed tree.

    The point is not merely to restore a deleted cache. Because run verdicts
    are re-derived by re-running today's predicate code over the archived
    output, a reindex re-checks every historical probe against the current
    understanding of what counts as a reproduction -- and reports where they
    now disagree. Both wrong-verdict classes found so far (a release rejecting
    an unknown profile, and an absence predicate satisfied by a failed parse)
    would have surfaced here automatically, across every past batch, for free.
    """
    c = con()
    # The rebuild reads `issues` from verdict.json alone, so every column
    # written by another subcommand and not mirrored there -- title, url,
    # created_at and labels from `fetch`, godbolt_url from `godbolt` -- used to
    # be silently dropped. That is not hypothetical: #2191 reached collation
    # with a NULL title, and `render_comments.py` selects on `batch`, so the
    # issue would have been left out of its own batch report. Snapshot the
    # rows, and put back anything the rebuild leaves empty.
    keep = {r["number"]: {k: r[k] for k in r.keys()
                          if k != "number" and r[k] is not None}
            for r in c.execute("SELECT * FROM issues")}
    if a.reset:
        c.executescript("DELETE FROM issues; DELETE FROM runs;")
        c.commit()

    issues = runs = 0
    changed, stale, gaps, preserved, accepted = [], [], [], [], []
    for name in sorted(os.listdir(ISSUES)) if os.path.isdir(ISSUES) else []:
        d = os.path.join(ISSUES, name)
        vpath = os.path.join(d, "verdict.json")
        rec = {}
        if os.path.isfile(vpath):
            with open(vpath, encoding="utf-8") as f:
                rec = json.load(f)
            number = rec.pop("number")
            fields = {k: v for k, v in rec.items() if k in ISSUE_FIELDS}
            c.execute("INSERT OR IGNORE INTO issues (number) VALUES (?)",
                      (number,))
            if fields:
                c.execute(
                    f"UPDATE issues SET {', '.join(f'{k} = ?' for k in fields)}"
                    " WHERE number = ?", list(fields.values()) + [number])
            issues += 1
        elif not name.isdigit():
            continue
        else:
            number = int(name)

        # Put back anything the rebuild left NULL that the database had. An
        # in-flight issue with no verdict.json keeps its row instead of
        # vanishing, and a verdict.json that never captured `fetch`'s fields
        # stops silently discarding them on every rebuild.
        row = c.execute("SELECT * FROM issues WHERE number = ?",
                        (number,)).fetchone()
        restored = {k: v for k, v in keep.get(number, {}).items()
                    if row is None or row[k] is None}
        if restored:
            c.execute("INSERT OR IGNORE INTO issues (number) VALUES (?)",
                      (number,))
            c.execute(
                f"UPDATE issues SET {', '.join(f'{k} = ?' for k in restored)}"
                " WHERE number = ?", list(restored.values()) + [number])
            preserved.append(f"#{number}: {', '.join(sorted(restored))}")

        for g in audit_issue(d, number, rec):
            gaps.append(f"#{number}: {g}")

        # A control carrying a declared expectation is an assertion, so
        # re-check it here for the same reason probes are re-scored: the
        # predicate it depends on may have changed since it was captured.
        #
        # Its `# verdict:` is re-checked too. That line is derived, exactly as
        # in a primary capture, but only `out-*.txt` was ever re-scored -- so
        # after a classifier change a variant's header could disagree with
        # today's code forever, silently, with no command able to correct it.
        # Surfaced when #3055's two methodology probes were re-declared.
        for var in sorted(f for f in os.listdir(d)
                          if f.startswith("variant-") and f.endswith(".txt")):
            vpath_v = os.path.join(d, var)
            meta, text = read_out(vpath_v)
            mf = meta.get("match", "match.json")
            if "exit" not in meta or not os.path.isfile(os.path.join(d, mf)):
                continue
            v, why = classify_capture(
                number, meta, text, mf, explain=True)
            expectation_problem = captured_expectation_issue(meta, v)
            if expectation_problem:
                kind, detail = expectation_problem
                if kind == "hypothesis" and a.accept:
                    outcome = expectation_outcome(meta.get("expect"), v)
                    restamp(vpath_v, "outcome", outcome)
                    accepted.append(
                        f"#{number} {var}: hypothesis outcome -> {outcome}")
                elif kind == "hypothesis":
                    changed.append(f"#{number} {var}: {detail}")
                else:
                    changed.append(f"#{number} {var}: control declared "
                                   f"{meta.get('expect')} but now scores {v}")
            if a.verify and meta.get("verdict") and meta["verdict"] != v:
                if a.accept:
                    restamp(vpath_v, "verdict", v)
                    stamp_reason(vpath_v, why)
                    accepted.append(f"#{number} {var}: "
                                    f"{meta['verdict']} -> {v}")
                else:
                    changed.append(f"#{number} {var}: header says "
                                   f"{meta['verdict']}, today's code scores {v}")

        for out in sorted(f for f in os.listdir(d)
                          if f.startswith("out-") and f.endswith(".txt")):
            path = os.path.join(d, out)
            meta, text = read_out(path)
            if "exit" not in meta:
                print(f"  skipped {name}/{out}: pre-reindex header", file=sys.stderr)
                continue

            # Correcting a repro does not delete the outputs captured from the
            # old one, and a superseded probe looks exactly as authoritative as
            # a current one. Measured on #3873: the profile was corrected from
            # ps_6_7 to ps_6_0, but `bisect` short-circuits once both endpoints
            # agree, so three mid-range releases kept outputs from a command
            # that no longer matches cmd.txt -- each one an "invalid profile"
            # rejection that had already produced a false "fixed" verdict once.
            cmd_path = os.path.join(d, "cmd.txt")
            if os.path.isfile(cmd_path) and meta.get("cmd"):
                with open(cmd_path) as f:
                    current = " ; ".join(ln.strip() for ln in f
                                         if ln.strip() and not ln.startswith("#"))
                captured_request = meta.get("requested-cmd", meta["cmd"])
                if current and captured_request != current:
                    stale.append(f"#{number} {meta.get('compiler', out)}: "
                                 f"captured {captured_request!r}, cmd.txt now "
                                 f"{current!r}")
            rc = None if meta["exit"] in ("None", "TIMEOUT") else int(meta["exit"])
            to = meta.get("timed_out") == "1"
            match_file = meta.get("match", "match.json")
            # An issue can have captured output but no symptom predicate --
            # #2427's verdict came from reading four command lines, not from
            # matching a pattern. Re-scoring is impossible without a predicate,
            # so carry the recorded verdict forward rather than inventing one.
            if not os.path.isfile(os.path.join(d, match_file)):
                verdict = meta.get("verdict") or "unscored"
            else:
                verdict = classify_capture(number, meta, text, match_file)
                if a.verify and meta.get("verdict") and meta["verdict"] != verdict:
                    if a.accept:
                        restamp(path, "verdict", verdict)
                        # Keep the demotion's explanation with the verdict it
                        # explains; a restamp that left the old reason behind
                        # would be worse than no reason at all.
                        stamp_reason(path, classify_capture(
                            number, meta, text, match_file,
                            explain=True)[1])
                        accepted.append(f"#{number} {meta['compiler']}: "
                                        f"{meta['verdict']} -> {verdict}")
                    else:
                        changed.append(f"#{number} {meta['compiler']}: "
                                       f"{meta['verdict']} -> {verdict}")
            # A --repeat aggregate is stamped into the header (see
            # stamp_repeat), so the hit rate survives a rebuild instead of
            # living only in a row no file backs.
            note = match_file
            if meta.get("attempts"):
                note = (f"{match_file} ({meta.get('hits', '?')}/"
                        f"{meta['attempts']} runs)")
            c.execute("INSERT INTO runs (issue_number, compiler, cmd, exit_code,"
                      " timed_out, output_path, verdict, note, ran_at)"
                      " VALUES (?,?,?,?,?,?,?,?,?)",
                      (number, meta.get("compiler", out[4:-4]),
                       meta.get("cmd", ""), rc, int(to), path, verdict,
                       note, meta.get("ran", "")))
            runs += 1
    c.commit()
    print(f"reindexed {issues} issue(s) and {runs} run(s) from {ROOT}")
    if preserved:
        print("\nfields kept from the database because verdict.json does not "
              "carry them (record them with `verdict --<field> ...` or the "
              "next rebuild on a fresh clone will not have them):")
        for line in preserved:
            print(f"  {line}")
    if stale:
        print("\nprobes captured with a command cmd.txt no longer specifies:")
        for line in stale:
            print(f"  {line}")
    if changed:
        print("\nverdicts that today's predicate code scores differently:")
        for line in changed:
            print(f"  {line}")
        print("  (investigate each one; re-run with --accept to restamp the "
              "headers once you are satisfied the new scoring is right)")
    if accepted:
        print("\nheaders restamped to today's scoring (measurements untouched; "
              "say why in the batch report):")
        for line in accepted:
            print(f"  {line}")
    if gaps:
        print("\nevidence a completed triage should have left behind:")
        for line in gaps:
            print(f"  {line}")
    if not (stale or changed or gaps or preserved):
        print("every probe re-scores as captured, none are stale, and no "
              "issue is missing required evidence")


def cmd_status(a):
    c = con()
    rows = list(c.execute(
        "SELECT number, status, repro_quality, history, suggested_action"
        " FROM issues ORDER BY number"))
    done = [r for r in rows if r["status"]]
    print(f"{len(done)}/{len(rows)} issues triaged\n")
    for r in rows:
        print(f"  #{r['number']:<6} {r['status'] or 'PENDING':<24}"
              f" {r['repro_quality'] or '':<18} {r['history'] or ''}")
    n = c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    print(f"\n{n} compiler run(s) recorded")


def cmd_sql(a):
    c = con()
    cur = c.execute(a.query)
    rows = cur.fetchall()
    c.commit()
    print(json.dumps([dict(r) for r in rows], indent=2)
          if cur.description else f"{cur.rowcount} row(s) affected")


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    s = sub.add_parser("reindex", help="rebuild the local database from the "
                                       "committed evidence tree. COLLATION "
                                       "ONLY: it rewrites shared state, so it "
                                       "is unsafe while other sessions are "
                                       "writing -- use `audit` per issue")
    # `--reset` used to be declared `action="store_true", default=True`, which
    # is a flag that cannot be turned off by its own name: a bare `reindex`
    # always took the destructive path. Every worker in batch 004 ran it as
    # instructed and two lost in-flight rows to a peer. The rebuild is still
    # the default -- re-scoring every probe is the point of the command -- but
    # it no longer pretends to be optional, and it no longer discards columns
    # verdict.json does not carry.
    s.add_argument("--reset", action="store_true", default=True,
                   help=argparse.SUPPRESS)
    s.add_argument("--no-reset", dest="reset", action="store_false",
                   help="add to the existing rows instead of rebuilding them; "
                        "duplicates run rows, so rarely what you want")
    s.add_argument("--verify", action="store_true", default=True,
                   help="report probes today's predicate code scores "
                        "differently than the run that captured them (default)")
    s.add_argument("--accept", action="store_true",
                   help="restamp those `# verdict:` headers to today's "
                        "scoring. The verdict is derived from the captured "
                        "text, so this loses nothing -- but do it only after "
                        "checking each change, and record it in the report")
    s.set_defaults(func=cmd_reindex)

    s = sub.add_parser("audit", help="read-only completeness check over the "
                                     "evidence tree; touches no tables, so it "
                                     "is safe to run while other sessions are "
                                     "working")
    s.add_argument("--issue", type=int, help="check one issue (default: all)")
    s.add_argument("--collated", action="store_true",
                   help="also require reviewed_by -- step 10 is a batch step, "
                        "so this is collation's view, not a worker's")
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("expect", help="revise a capture's declared expectation "
                                      "after a predicate change; refuses if "
                                      "the new declaration would be false")
    s.add_argument("--issue", type=int, required=True)
    s.add_argument("--capture", required=True,
                   help="the out-*.txt or variant-*.txt file to correct")
    s.add_argument("--expect", required=True,
                   choices=["match", "no-match", "invalid-probe"])
    s.add_argument("--why", help="one line on why the old declaration was wrong")
    s.set_defaults(func=cmd_expect)

    s = sub.add_parser("catalog")
    s.add_argument("--seed-from", help="path to an existing dxc_releases tree")
    s.set_defaults(func=cmd_catalog)

    s = sub.add_parser("compiler")
    s.add_argument("--id", default="main-debug")
    s.add_argument("--exe", required=True)
    s.add_argument("--commit")
    s.set_defaults(func=cmd_compiler)

    s = sub.add_parser("fetch")
    s.add_argument("--issue", type=int, required=True)
    s.add_argument("--batch")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("run")
    s.add_argument("--issue", type=int, required=True)
    s.add_argument("--compiler", default=None,
                   help="compiler id from `triage.py compiler` (default: "
                        "main-debug, unless this issue's existing captures "
                        "were all taken with a different one)")
    s.add_argument("--match", default="match.json")
    s.add_argument("--repeat", type=int, default=1,
                   help="run the repro up to N times and report the symptom if "
                        "any run shows it; use for nondeterministic failures "
                        "such as heap corruption, races or uninitialised reads")
    s.add_argument("--show", action="store_true")
    s.add_argument("--shader", help="run this file instead of the repro, with "
                                    "the same arguments -- for controls and "
                                    "translated variants")
    s.add_argument("--label", help="name the variant; output is written to "
                                   "variant-<label>-<compiler>.txt and is not "
                                   "scored as a probe of the primary repro")
    s.add_argument("--args", help="replace the arguments entirely, for a "
                                  "variant that changes shader stage and so "
                                  "cannot reuse the repro's command")
    s.add_argument("--expect", choices=["match", "no-match", "invalid-probe"],
                   help="what this control must do. Recorded in the output "
                        "header and re-checked on every reindex. "
                        "`invalid-probe` is for a control that is expected to "
                        "be rejected before it reaches the code under test")
    s.add_argument(
        "--hypothesis", action="store_true",
        help="record --expect as a prediction whose supported/refuted outcome "
             "is evidence, rather than as a control assertion")
    s.add_argument("--force", action="store_true",
                   help="overwrite a capture that was scored with a different "
                        "predicate; prefer --label, which keeps both")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("bisect")
    s.add_argument("--issue", type=int, required=True)
    s.add_argument("--match", default="match.json")
    s.add_argument("--repeat", type=int, default=1,
                   help="probe each release up to N times (see 'run --repeat'); "
                        "a one-shot probe of a nondeterministic bug invents "
                        "release boundaries that are not there")
    s.add_argument("--linear", action="store_true",
                   help="probe every release instead of binary searching; "
                        "required when the symptom is non-monotonic, e.g. an "
                        "issue that was fixed and later reverted")
    s.set_defaults(func=cmd_bisect)

    s = sub.add_parser("godbolt")
    s.add_argument("--issue", type=int, required=True)
    s.add_argument("--compilers", default=None,
                   help="comma-separated Compiler Explorer compiler ids; "
                        "'id:<args>' overrides the arguments for that "
                        "compiler. Saved to the issue's godbolt.txt and "
                        "reused when omitted. Default: "
                        f"{CE_OLDEST},{CE_TRUNK}")
    s.add_argument("--no-verify", action="store_true",
                   help="skip compiling on CE before shortening")
    s.add_argument("--source", default=None, metavar="FILE",
                   help="publish this file from the issue directory instead "
                        "of repro.hlsl -- for a translated variant (e.g. a "
                        "compute restating of a pixel repro) that a "
                        "comparison compiler can actually run. Remembered "
                        "in godbolt-source.txt.")
    s.add_argument("--skip", metavar="REASON",
                   help="record that this issue deliberately gets no link "
                        "(e.g. a pure feature request), with the reason")
    s.set_defaults(func=cmd_godbolt)

    s = sub.add_parser("labels")
    s.add_argument("--refresh", action="store_true",
                   help="re-fetch the taxonomy from the repo before listing")
    s.add_argument("--issue", type=int,
                   help="show current vs proposed labels for one issue")
    s.set_defaults(func=cmd_labels)

    s = sub.add_parser("verdict")
    s.add_argument("--issue", type=int, required=True)
    for f in ISSUE_FIELDS:
        s.add_argument(f"--{f.replace('_', '-')}", dest=f)
    s.set_defaults(func=cmd_verdict)

    sub.add_parser("status").set_defaults(func=cmd_status)

    s = sub.add_parser("sql")
    s.add_argument("query")
    s.set_defaults(func=cmd_sql)

    a = p.parse_args()
    # `reindex` is exempt: rebuilding the database when it is missing is
    # precisely its job, and after a fresh clone that is the normal state.
    if a.cmd not in ("init", "reindex") and not os.path.exists(DB):
        sys.exit(f"no workspace at {ROOT}; run 'triage.py init' first")
    # A command's return value becomes the process exit status, so a check can
    # be used as a gate. `audit` is the one that needs it: it reports missing
    # evidence and a stale overview, and a reviewer wiring it into a script
    # would otherwise see a clean exit no matter what it printed. Bools are
    # excluded deliberately -- `True` is an int and would exit 1.
    rc = a.func(a)
    sys.exit(rc if isinstance(rc, int) and not isinstance(rc, bool) else 0)


if __name__ == "__main__":
    main()
