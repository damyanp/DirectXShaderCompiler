#!/usr/bin/env python3
"""Tooling for DXC open-issue triage.

Answers, per issue: is there a usable repro, does it still reproduce against a
current build, and which release fixed it or introduced it.

The workspace lives outside the DXC repo (set DXC_TRIAGE_ROOT, default
~/dxc-triage) and holds a SQLite index plus per-issue evidence, so a long pass
can be stopped and resumed.

  triage.py init
  triage.py catalog
  triage.py compiler --id main-debug --exe <path/to/dxc>
  triage.py fetch    --issue 1768
  triage.py run      --issue 1768 [--compiler main-debug] [--match match.json]
  triage.py bisect   --issue 1768 [--match match.json]
  triage.py verdict  --issue 1768 --status repros --repro-quality complete ...
  triage.py status
  triage.py sql "SELECT ..."

This tool is read-only with respect to GitHub: it only ever runs `gh issue
view`, `gh release list/view/download`. It never edits, labels, comments on or
closes an issue.
"""

import argparse
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
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
]

# Columns added after the first release of this script. Applied on connect so
# that workspaces created by an older version keep working.
MIGRATIONS = {"issues": {
    "godbolt_url": "TEXT", "godbolt_skip": "TEXT", "labels_now": "TEXT",
    "labels_add": "TEXT", "labels_remove": "TEXT",
}}


_READY = False


def con():
    global _READY
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
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


# Exit codes that mean dxc did not fail cleanly. Taken from dxc's own
# top-level exception filter (tools/clang/tools/dxclib/dxc.cpp), which is the
# authoritative list -- it is what turns these into the "access violation" /
# "LLVM Assert" / "Terminal Error 0x..." messages.
INTERNAL_STATUS = frozenset((
    0xC0000005,  # EXCEPTION_ACCESS_VIOLATION
    0xC00000FD,  # EXCEPTION_STACK_OVERFLOW
    0x80000003,  # breakpoint -- an assert firing with no debugger attached
    0xE0000001,  # STATUS_LLVM_ASSERT
    0xE0000002,  # STATUS_LLVM_UNREACHABLE
    0xE0000003,  # STATUS_LLVM_FATAL
))

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
    os.makedirs(dest, exist_ok=True)
    zip_path = os.path.join(dest, row["asset_name"])
    if not os.path.exists(zip_path):
        print(f"downloading {tag} ({row['asset_name']}) ...", file=sys.stderr)
        gh("release", "download", tag, "--repo", REPO,
           "--pattern", row["asset_name"], "--dir", dest, "--clobber")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest)
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
                         text=True).stdout.strip().replace("\n", " ")
    c = con()
    c.execute("INSERT OR REPLACE INTO compilers (id, exe_path, git_commit,"
              " version, built_at) VALUES (?,?,?,?,?)",
              (a.id, a.exe, a.commit, ver, now()))
    c.commit()
    print(f"{a.id}: {a.exe}\n  version: {ver}\n  commit:  {a.commit}")
    if a.commit and a.commit[:8] not in ver and "dirty" in ver:
        print("\nWARNING: version string looks stale or dirty. DXC caches the "
              "generated version headers; delete build/utils/version/version.inc "
              "and dxcversion.inc (and their .gen files) and rebuild, or triage "
              "provenance will be wrong.", file=sys.stderr)


def cmd_fetch(a):
    d = issue_dir(a.issue)
    os.makedirs(d, exist_ok=True)
    raw = gh("issue", "view", str(a.issue), "--repo", REPO, "--json",
             "number,title,url,createdAt,labels,body,comments,state")
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


def classify(issue, text, rc, timed_out, match_file="match.json"):
    """Score one probe: repro | no-repro | invalid-probe.

    Kept as a free function rather than inlined into `execute` so that
    `reindex` scores committed evidence with *exactly* the code that scored it
    live. If the two could drift, a rebuild could silently disagree with the
    run that produced the file, and the disagreement would look like a finding.
    """
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
    unsupported = re.search(
        r"(?i)invalid profile|unsupported profile|unrecognized (?:argument|option)|"
        r"unknown argument|is not supported|requires shader model|"
        r"CodeGen not available|recompile with -D|"
        r"use of undeclared identifier|unknown type name|"
        r"no member named|no matching function for call to", text)
    if verdict == "no-repro" and unsupported:
        return "invalid-probe"

    # Absence-based predicates ("the symptom is that X is MISSING") are
    # satisfied for free by any compile that never got far enough to emit X.
    # #1877's predicate is `not_contains fptosi`; a release that failed to
    # parse the repro emits no fptosi either, and would score as a textbook
    # reproduction. Those probes were checked by hand and did compile, but the
    # hazard is structural, so flag it rather than silently trusting it.
    if verdict == "repro" and _is_absence_predicate(issue, match_file) \
            and (unsupported or is_internal_failure(text, rc, timed_out)):
        return "invalid-probe"
    return verdict


def execute(issue, compiler, match_file="match.json", record=True, repeat=1):
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
    if repeat > 1:
        attempts, seen = [], []
        for i in range(repeat):
            r = execute(issue, compiler, match_file, record=False, repeat=1)
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
    exe = resolve_compiler(compiler)
    with open(os.path.join(d, "cmd.txt")) as f:
        cmds = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    chunks, worst_rc, timed_out = [], 0, False
    for line in cmds:
        try:
            p = subprocess.run([exe] + shlex.split(line), cwd=d,
                               capture_output=True, text=True,
                               errors="replace", timeout=TIMEOUT)
            rc, out, err, to = p.returncode, p.stdout, p.stderr, False
        except subprocess.TimeoutExpired as e:
            rc, out, err, to = None, e.stdout or "", e.stderr or "", True
        timed_out = timed_out or to
        if rc not in (0, None) and worst_rc == 0:
            worst_rc = rc
        chunks.append(f"$ dxc {line}\n[exe] {exe}\n"
                      f"[exit] {'TIMEOUT' if to else rc}\n"
                      f"--- stdout ---\n{out}\n--- stderr ---\n{err}\n")

    text = "\n".join(chunks)
    verdict = classify(issue, text, worst_rc, timed_out, match_file)
    out_path = os.path.join(d, f"out-{compiler}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# compiler: {compiler}\n# exe: {display_exe(exe)}\n"
                f"# ran: {now()}\n# cmd: {' ; '.join(cmds)}\n"
                f"# exit: {worst_rc}\n# timed_out: {int(timed_out)}\n"
                f"# match: {match_file}\n# verdict: {verdict}\n\n{text}")

    if record:
        c = con()
        c.execute("INSERT INTO runs (issue_number, compiler, cmd, exit_code,"
                  " timed_out, output_path, verdict, note, ran_at)"
                  " VALUES (?,?,?,?,?,?,?,?,?)",
                  (issue, compiler, " ; ".join(cmds), worst_rc, int(timed_out),
                   out_path, verdict, match_file, now()))
        c.commit()
    return {"compiler": compiler, "exit": worst_rc, "timed_out": timed_out,
            "verdict": verdict, "output": out_path, "text": text}


def cmd_run(a):
    r = execute(a.issue, a.compiler, a.match, repeat=a.repeat)
    extra = ""
    if r.get("attempts", 1) > 1:
        extra = f" [{r['hits']}/{r['attempts']} runs showed it]"
    print(f"{r['compiler']}: exit={r['exit']} timed_out={r['timed_out']}"
          f" -> {r['verdict']}{extra}")
    print(f"output: {r['output']}")
    if a.show:
        print("\n" + r["text"])


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
    rels = [r["tag"] for r in con().execute(
        "SELECT tag FROM releases WHERE bisectable = 1 ORDER BY build_date")]
    if not rels:
        sys.exit("no releases catalogued; run 'triage.py catalog'")

    def probe(tag):
        r = execute(a.issue, tag, a.match, repeat=a.repeat)
        v = r["verdict"]
        if v == "invalid-probe":
            print(f"  {tag:<14} n/a (never compiled the repro -- profile, flag "
                  f"or feature unsupported)")
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
        note = f" ({skipped} release(s) skipped as unprobeable)" if skipped else ""
        if len(runs) == 1:
            print(f"\nresult: {'always' if runs[0][1] else 'never'}-repro'd "
                  f"across {usable[0][0]}..{usable[-1][0]}{note}")
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
        print(f"\nresult: {state} across {rels[0]}..{rels[-1]}")
        return

    # Invariant: rels[lo] behaves like `oldest`, rels[hi] like `newest`.
    lo, hi = 0, len(rels) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        v = probe(rels[mid])
        lo, hi = (mid, hi) if v == oldest else (lo, mid)

    if oldest and not newest:
        print(f"\nresult: fixed-in {rels[hi]} (last repro: {rels[lo]})")
    else:
        print(f"\nresult: regressed-in {rels[hi]} (last good: {rels[lo]})")


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
    rows = json.loads(gh("label", "list", "--repo", REPO, "--limit", "500",
                         "--json", "name,description"))
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


def ce_args(issue):
    """Turn cmd.txt into CE user arguments: drop the source file name.

    Only a *positional* source file is dropped (CE supplies the source
    itself). A filename that is the value of a flag -- `-include forced.h`,
    `-Fo out.dxil` -- is kept, otherwise the flag would be left dangling and
    the resulting error would be an artefact of this function rather than the
    behaviour under test.
    """
    d = issue_dir(issue)
    with open(os.path.join(d, "cmd.txt")) as f:
        lines = [ln.strip() for ln in f
                 if ln.strip() and not ln.startswith("#")]
    if len(lines) > 1:
        print("  warning: multi-invocation cmd.txt; linking the first only")
    toks, keep = shlex.split(lines[0]), []
    for i, t in enumerate(toks):
        positional = i == 0 or not toks[i - 1].startswith("-")
        if positional and os.path.exists(os.path.join(d, t)):
            continue
        keep.append(t)
    return " ".join(keep), lines[0]


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
    lines = [f"// {ln}".rstrip() for ln in body.splitlines()]
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
    args, full = ce_args(a.issue)
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
    compilers = []
    for entry in spec.split(","):
        entry = entry.strip()
        if not entry:
            continue
        cid, _, override = entry.partition(":")
        compilers.append((cid, override.strip() or args))

    extra = [f for f in os.listdir(d) if f.endswith((".h", ".hlsli"))]
    if extra:
        print(f"  warning: repro references local file(s) {extra}; CE is "
              "single-file, so the link demonstrates only part of this issue")
    if not os.path.exists(os.path.join(d, "godbolt-note.txt")):
        print("  warning: no godbolt-note.txt; the link will not say what a "
              "reader should be looking at")

    print(f"#{a.issue}: dxc {full}\n  CE args: {args}")
    if not a.no_verify:
        for cid, cargs in compilers:
            rc, text, crashed = ce_compile(source, cid, cargs)
            first = next((ln for ln in text.splitlines() if ln.strip()), "")
            print(f"  {cid:<18} exit={rc}"
                  f"{' CRASH' if crashed else ''}  {first[:70]}")

    url = ce_post("/api/shortener", {"sessions": [{
        "id": 1, "language": "hlsl", "source": source,
        "compilers": [{"id": cid, "options": ca, "filters": dict(CE_FILTERS),
                       "libs": []} for cid, ca in compilers],
    }]})["url"]

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
    if a.reset:
        c.executescript("DELETE FROM issues; DELETE FROM runs;")
        c.commit()

    issues = runs = 0
    changed, stale = [], []
    for name in sorted(os.listdir(ISSUES)) if os.path.isdir(ISSUES) else []:
        d = os.path.join(ISSUES, name)
        vpath = os.path.join(d, "verdict.json")
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
                if current and meta["cmd"] != current:
                    stale.append(f"#{number} {meta.get('compiler', out)}: "
                                 f"captured {meta['cmd']!r}, cmd.txt now "
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
                verdict = classify(number, text, rc, to, match_file)
                if a.verify and meta.get("verdict") and meta["verdict"] != verdict:
                    changed.append(f"#{number} {meta['compiler']}: "
                                   f"{meta['verdict']} -> {verdict}")
            c.execute("INSERT INTO runs (issue_number, compiler, cmd, exit_code,"
                      " timed_out, output_path, verdict, note, ran_at)"
                      " VALUES (?,?,?,?,?,?,?,?,?)",
                      (number, meta.get("compiler", out[4:-4]),
                       meta.get("cmd", ""), rc, int(to), path, verdict,
                       match_file, meta.get("ran", "")))
            runs += 1
    c.commit()
    print(f"reindexed {issues} issue(s) and {runs} run(s) from {ROOT}")
    if stale:
        print("\nprobes captured with a command cmd.txt no longer specifies:")
        for line in stale:
            print(f"  {line}")
    if changed:
        print("\nverdicts that today's predicate code scores differently:")
        for line in changed:
            print(f"  {line}")
    if not (stale or changed):
        print("every probe re-scores as captured, and none are stale")


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
                                       "committed evidence tree")
    s.add_argument("--reset", action="store_true", default=True,
                   help="clear issues and runs first (default)")
    s.add_argument("--no-reset", dest="reset", action="store_false")
    s.add_argument("--verify", action="store_true", default=True,
                   help="report probes today's predicate code scores "
                        "differently than the run that captured them (default)")
    s.set_defaults(func=cmd_reindex)

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
    s.add_argument("--compiler", default="main-debug")
    s.add_argument("--match", default="match.json")
    s.add_argument("--repeat", type=int, default=1,
                   help="run the repro up to N times and report the symptom if "
                        "any run shows it; use for nondeterministic failures "
                        "such as heap corruption, races or uninitialised reads")
    s.add_argument("--show", action="store_true")
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
    a.func(a)


if __name__ == "__main__":
    main()
