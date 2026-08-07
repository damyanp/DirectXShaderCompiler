"""#2604 -- what does the compile API do with `-Fc`, and has it ever done
anything else?

Two questions, two outputs.

`--contrast` writes manual-case-cmdline-vs-api.txt: the SAME arguments run
through dxc.exe and through the compile API, side by side. That is the whole
subject of the issue -- `-Fc` is `Flags<[DriverOption]>` and dxc.exe parses
with `DxcFlags = CoreOption | DriverOption` while the library parses with
`CompilerFlags = CoreOption`, so the two take different paths through the same
option table. The command line writes the listing; the API rejects the flag.
The `variant-cmdline-main-debug.txt` capture cannot show this on its own,
because dxc.exe succeeds silently and the evidence is a FILE it created, which
is not in any captured stdout.

`--history` writes manual-case-release-history.txt: the same probe against
every cached release's own dxcompiler.dll.

    set DXC_FC_DLL=<release>/dxcompiler.dll
    fc2604.exe -T ps_6_0 -E main -Fc repro-fc.asm repro.hlsl

`triage.py bisect` cannot produce that table. It resolves a release tag to
that release's **dxc.exe** and builds its command line from `cmd.txt`, and
dxc.exe is the one caller that DOES handle `-Fc` -- so every release would
score `no-repro` and the run would report a confident
"never-repro'd-in-releases", the exact opposite of the truth. The same
limitation was recorded on #2923 and #3237. It was deliberately not run.

What makes the history measurable anyway is that the option parsing and both
compile entry points live inside **dxcompiler.dll**, which every release
ships, so each row drives THAT RELEASE's own argument handling. No GPU,
driver or D3D runtime is involved.

`--source` writes manual-case-source-evidence.txt: the `git grep` and
`git log` commands behind every source claim in notes.md, each echoed and
each with its output. Two of them are ABSENCE claims -- "-Fc has no consumer
inside dxcompiler" and "no Compile path produces DXC_OUT_DISASSEMBLY" -- and
an absence is only worth anything if the search that found nothing is shown
to find something when something is there. Each therefore runs a
known-positive control first, in the same directory with the same tool, and
prints it. A bare "0 results" is not evidence; "this pattern finds 10 hits
repo-wide and 0 under dxcompiler/" is.

Usage:
    python measure-2604.py --contrast
    python measure-2604.py --history
    python measure-2604.py --source
    python measure-2604.py --contrast --history --source

Paths come from the triage database and from DXC_BUILD_BIN, falling back to
the repo's Debug build. Nothing absolute is hardcoded: every path is derived
from this file's own location, and every path written into an artifact is
redacted to the same <cache>/<triage>/<repo> placeholders triage.py uses.
"""

import argparse
import os
import re
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
DB = os.path.join(SKILL, ".cache", "triage.db")

BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")
HARNESS = os.path.join(HERE, "bin", "fc2604.exe")

# Exactly cmd.txt. Kept as a literal rather than parsed out of cmd.txt so that
# a reader of this file can see what ran; `reindex` checks cmd.txt against the
# tool-made captures, and manual-case-*.txt echoes every command it runs.
ARGS = ["-T", "ps_6_0", "-E", "main", "-Fc", "repro-fc.asm", "repro.hlsl"]
FC_FILE = "repro-fc.asm"

RE_RESULT = re.compile(
    r"^RESULT case=(\S+) call=(0x[0-9A-F]{8}) status=(\S+) object=(\S+) "
    r"disasm=(\S+) fcfile=(\S+)$", re.M)
RE_INCOMPLETE = re.compile(r"^fc2604: PROBE-INCOMPLETE: (.*)$", re.M)
RE_C3 = re.compile(r"^IDxcCompiler3: (.*)$", re.M)
RE_SPIRV = re.compile(r"^SELFCHECK: spirv-codegen=(\S+)$", re.M)


def redact(path):
    """Absolute path -> the placeholders triage.py writes in capture headers.

    Same tokens and same most-specific-first order as scripts/triage.py:
    <cache>, <triage>, <repo>, forward slashes. These files are committed, so
    an absolute path would ship one machine's directory layout to everyone and
    leave an artifact nobody else can re-run. fc2604.cpp has the same function
    for the lines it prints; both have to do it, because each writes its own
    output.
    """
    p = os.path.abspath(path).replace(os.sep, "/")
    for base, token in ((os.path.join(SKILL, ".cache"), "<cache>"),
                        (SKILL, "<triage>"), (REPO, "<repo>")):
        b = os.path.abspath(base).replace(os.sep, "/")
        if p.lower() == b.lower():
            return token
        if p.lower().startswith(b.lower() + "/"):
            return token + p[len(b):]
    return p


def shown(argv):
    """The command as executed, not as remembered.

    SKILL.md: "Generate every manual-case-*.txt from a small script that
    echoes the command it is about to run" -- a transcribed command line is an
    assertion checked by nobody (measured on #2922).
    """
    return redact(argv[0]) + " " + subprocess.list2cmdline(argv[1:])


def run(argv, env_extra=None, cwd=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=cwd or HERE, env=env, timeout=300)
    return p.returncode, p.stdout + p.stderr


def releases():
    """(tag, build_date, dxcompiler.dll) for every cached release, oldest first.

    Non-bisectable releases are included on purpose. v1.5.2003 is flagged
    bisectable=0 (it is a GitHub prerelease), which leaves a fourteen-month
    hole in the scan; this issue was filed 2019-11 and commented on 2020-07,
    so that hole is exactly where its history lives.
    """
    if not os.path.isfile(DB):
        sys.exit(f"no triage database at {DB}; run `triage.py catalog` first")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT tag, build_date, cached_path FROM releases"
        " WHERE cached_path IS NOT NULL ORDER BY build_date").fetchall()
    con.close()
    out = []
    for tag, date, exe in rows:
        dll = os.path.join(os.path.dirname(exe), "dxcompiler.dll")
        if os.path.isfile(dll):
            out.append((tag, date, dll))
    return out


def parse(text):
    cases = {}
    for m in RE_RESULT.finditer(text):
        cases[m.group(1)] = {
            "call": m.group(2), "status": m.group(3), "object": m.group(4),
            "disasm": m.group(5), "fcfile": m.group(6)}
    return cases


def score(text):
    """Read one probe. Returns (verdict, cases, why).

    A completed probe always prints RESULT lines. Reaching the third branch
    means the output is not what this reader expects -- say so loudly rather
    than scoring it, because a reader that can return "nothing here" and
    "nothing matched" through the same channel will eventually be believed
    (SKILL.md, measured on #2923).
    """
    inc = RE_INCOMPLETE.search(text)
    cases = parse(text)
    if inc:
        return "invalid-probe", cases, inc.group(1)
    if not cases:
        return "unreadable", cases, ("PARSE-WARNING: probe completed but no "
                                     "RESULT line was found")
    need = ("c1-fc", "c1-fc-qunused", "c1-baseline", "c1-disassemble")
    missing = [n for n in need if n not in cases]
    if missing:
        return "unreadable", cases, (
            "PARSE-WARNING: missing RESULT lines for " + ", ".join(missing))
    if cases["c1-baseline"]["object"] != "present":
        return "invalid-probe", cases, "the baseline compile produced no object"
    if cases["c1-disassemble"]["disasm"] != "present":
        return "invalid-probe", cases, "this DLL could not disassemble at all"
    rejected = cases["c1-fc"]["status"] == "0x80070057"
    ignored = (cases["c1-fc-qunused"]["status"] == "0x00000000" and
               cases["c1-fc-qunused"]["disasm"] == "absent" and
               cases["c1-fc-qunused"]["fcfile"] == "absent")
    if ignored:
        return ("repro", cases,
                "-Fc rejected" if rejected else "-Fc accepted but ignored")
    return "no-repro", cases, "a listing reached the caller"


def contrast():
    dll = os.path.join(BUILD_BIN, "dxcompiler.dll")
    exe = os.path.join(BUILD_BIN, "dxc.exe")
    out = [
        "#2604 -- the same arguments through dxc.exe and through the compile",
        "API",
        "",
        "Produced by `python measure-2604.py --contrast`. Every command below",
        "is echoed exactly as executed (subprocess.list2cmdline), and every",
        "path is redacted to the placeholders triage.py uses.",
        "",
        "WHY THIS FILE EXISTS. `variant-cmdline-main-debug.txt` records the",
        "dxc.exe run, but dxc.exe succeeds SILENTLY here: the whole effect of",
        "-Fc is a file it writes, and a file is not in anyone's stdout. The",
        "capture therefore shows an empty successful run, which reads as",
        "'nothing happened'. This file records the file.",
        "",
    ]

    fc = os.path.join(HERE, FC_FILE)
    if os.path.exists(fc):
        os.remove(fc)
    argv = [exe] + ARGS
    rc, text = run(argv)
    out += ["=" * 72, "A. dxc.exe -- the driver, which parses with DxcFlags =",
            "   CoreOption | DriverOption", "=" * 72, "",
            "$ " + shown(argv), f"[exit] {rc}", "--- output ---",
            text.rstrip("\n") if text.strip() else "(no output)", ""]
    if os.path.exists(fc):
        data = open(fc, "r", errors="replace").read()
        lines = data.splitlines()
        out += [f'file "{FC_FILE}": CREATED, {os.path.getsize(fc)} bytes,'
                f" {len(lines)} lines", "first 6 lines:"]
        out += ["    " + ln for ln in lines[:6]]
    else:
        out += [f'file "{FC_FILE}": NOT created']
    out += [""]

    # The same thing again with -spirv, because docs/SPIR-V.rst makes its
    # "also recognized by the library API calls" claim about exactly this
    # list. On the command line the promise is kept; the API side is case B.
    if os.path.exists(fc):
        os.remove(fc)
    argv = [exe] + ARGS[:4] + ["-spirv"] + ARGS[4:]
    rc, text = run(argv)
    out += ["=" * 72, "A2. dxc.exe again, with -spirv", "=" * 72, "",
            "$ " + shown(argv), f"[exit] {rc}", "--- output ---",
            text.rstrip("\n") if text.strip() else "(no output)", ""]
    if os.path.exists(fc):
        lines = open(fc, "r", errors="replace").read().splitlines()
        out += [f'file "{FC_FILE}": CREATED, {os.path.getsize(fc)} bytes,'
                f" {len(lines)} lines -- SPIR-V assembly, a different artifact",
                "first 4 lines:"] + ["    " + ln for ln in lines[:4]]
    else:
        out += [f'file "{FC_FILE}": NOT created']
    out += [""]

    if os.path.exists(fc):
        os.remove(fc)
    argv = [HARNESS] + ARGS
    rc, text = run(argv, {"DXC_FC_DLL": dll})
    verdict, cases, why = score(text)
    sv = RE_SPIRV.search(text)
    out += ["=" * 72,
            "B. the compile API -- IDxcCompiler::Compile and",
            "   IDxcCompiler3::Compile, which parse with CompilerFlags =",
            "   CoreOption alone", "=" * 72, "",
            f"$ set DXC_FC_DLL={redact(dll)}",
            "$ " + shown(argv), f"[exit] {rc}", "--- output ---",
            text.rstrip("\n"), "",
            f"scored: {verdict} ({why})",
            f"SPIR-V codegen in this DLL: {sv.group(1) if sv else 'not-probed'}",
            f'file "{FC_FILE}" after the API run:'
            f' {"CREATED" if os.path.exists(fc) else "NOT created"}', ""]
    if os.path.exists(fc):
        os.remove(fc)

    out += [
        "=" * 72, "READING IT", "=" * 72, "",
        "dxc.exe writes the listing. Neither compile entry point in the same",
        "dxcompiler.dll will: both answer E_INVALIDARG with",
        "\"Unknown argument: '-Fc'\", and with -Qunused-arguments (a",
        "CoreOption, so the library does see it) they compile successfully",
        "and drop -Fc on the floor -- no DXC_OUT_DISASSEMBLY, no file.",
        "",
        "The disassembly itself is not missing from the library; it is one",
        "more call away. IDxcCompiler::Disassemble on the object returns it",
        "(the c1-disassemble row). What the issue asks for is that ONE",
        "Compile call produce both.",
        "",
        "The c1-spirv-* rows answer a written claim rather than the issue.",
        "docs/SPIR-V.rst:4211 lists '``-Fc``: outputs SPIR-V disassembly to",
        "the given file', and :4197-4198 says those options 'are also",
        "recognized by the library API calls'. They are not: with -spirv the",
        "API rejects -Fc identically, and tolerating it with",
        "-Qunused-arguments still yields no listing. The -spirv baseline in",
        "the same run compiles successfully, so this is not a build without",
        "SPIR-V.",
        "",
    ]
    path = os.path.join(HERE, "manual-case-cmdline-vs-api.txt")
    open(path, "w", newline="\n").write("\n".join(out) + "\n")
    print("wrote", redact(path))


def probe(dll):
    """One harness run against one dxcompiler.dll, read into a row."""
    rc, text = run([HARNESS] + ARGS, {"DXC_FC_DLL": dll})
    verdict, cases, why = score(text)
    c3 = RE_C3.search(text)
    sv = RE_SPIRV.search(text)
    return {"dll": redact(dll), "cmd": shown([HARNESS] + ARGS), "exit": rc,
            "verdict": verdict, "why": why, "cases": cases, "text": text,
            "c3": c3.group(1) if c3 else "(not reported)",
            "spirv": sv.group(1) if sv else "not-probed"}


def history():
    rows = []
    for tag, date, dll in releases():
        r = probe(dll)
        r.update(tag=tag, date=date)
        rows.append(r)
    r = probe(os.path.join(BUILD_BIN, "dxcompiler.dll"))
    r.update(tag="main-debug", date="(local)")
    rows.append(r)

    fc = os.path.join(HERE, FC_FILE)
    if os.path.exists(fc):
        os.remove(fc)

    out = [
        "#2604 release history -- does the compile API handle -Fc?",
        "",
        "Produced by `python measure-2604.py --history`. Each row drives THAT",
        "RELEASE's own option parsing and compile entry points, by pointing",
        "the harness at that release's dxcompiler.dll:",
        "",
        "    set DXC_FC_DLL=<release>/dxcompiler.dll",
        "    fc2604.exe " + subprocess.list2cmdline(ARGS),
        "",
        "fc2604.exe is built from fc2604.cpp in this directory and is inert",
        "plumbing: it calls IDxcCompiler::Compile, IDxcCompiler3::Compile and",
        "IDxcCompiler::Disassemble. All three are implemented inside",
        "dxcompiler.dll, so the code under test is the release's, not the",
        "harness's.",
        "",
        "triage.py bisect cannot produce this table: it resolves a release tag",
        "to that release's dxc.exe, which is the one caller that DOES handle",
        "-Fc. It would score every release no-repro.",
        "",
        "v1.5.2003 is included although it is flagged bisectable=0; the scan",
        "otherwise jumps 2019-07 -> 2020-10, and this issue was filed",
        "2019-11-26 and commented on 2020-07-30.",
        "",
        "COLUMNS",
        "  c1-fc      IDxcOperationResult::GetStatus after",
        "             IDxcCompiler::Compile with `-Fc <file>`",
        "             0x80070057 = E_INVALIDARG, the 2020 comment's report",
        "  +Qunused   the same with -Qunused-arguments, which is a CoreOption",
        "             and suppresses the unknown-argument check -- this is the",
        "             case that tests the FEATURE rather than the flag mask",
        "  listing    did anything carry a disassembly listing back to the",
        "             caller?  none/obj = an object came back but no listing",
        "  disasm     IDxcCompiler::Disassemble on that object (the anchor:",
        "             the listing IS available, one call later)",
        "  spirv-fc   the same -Fc probe with -spirv added, guarded by a",
        "             -spirv baseline that must first compile successfully.",
        "             docs/SPIR-V.rst:4197-4198 + :4211 claim -Fc is supported",
        "             by SPIR-V CodeGen and 'also recognized by the library",
        "             API calls'; this column is that claim, measured.",
        "  IDxcCompiler3  available from DXC 1.6 on; pre-1.6 rows measure the",
        "             legacy interface only, which is the one the 2019 issue",
        "             and the 2020 comment were filed against",
        "",
        f"{'release':>14} {'date':>12} {'c1-fc':>11} {'+Qunused':>11}"
        f" {'listing':>8} {'disasm':>8} {'spirv-fc':>12}  IDxcCompiler3",
        f"{'-'*14} {'-'*12} {'-'*11} {'-'*11} {'-'*8} {'-'*8} {'-'*12}"
        f"  {'-'*13}",
    ]
    for r in rows:
        c = r["cases"]
        if r["verdict"] in ("invalid-probe", "unreadable"):
            out.append(f"{r['tag']:>14} {r['date']:>12}"
                       f"  {r['verdict']} -- {r['why']}")
            continue
        listing = "none" if (c["c1-fc-qunused"]["disasm"] == "absent" and
                             c["c1-fc-qunused"]["fcfile"] == "absent") else "SOME"
        if listing == "none" and c["c1-fc-qunused"]["object"] == "present":
            listing = "none/obj"
        if r["spirv"] != "available":
            sv = "no-spirv"
        elif "c1-spirv-fc" in c:
            sv = c["c1-spirv-fc"]["status"]
        else:
            sv = "not-probed"
        out.append(
            f"{r['tag']:>14} {r['date']:>12} {c['c1-fc']['status']:>11}"
            f" {c['c1-fc-qunused']['status']:>11} {listing:>8}"
            f" {c['c1-disassemble']['disasm']:>8} {sv:>12}  {r['c3']}")

    out += ["", "VERDICT PER ROW", ""]
    for r in rows:
        out.append(f"  {r['tag']:>14}  {r['verdict']:>13}  {r['why']}")

    out += ["", "=" * 72, "FULL TRANSCRIPTS", "=" * 72]
    for r in rows:
        out += ["", "-" * 72, f"release: {r['tag']}  ({r['date']})",
                f"dll: {r['dll']}", "$ " + r["cmd"], f"[exit] {r['exit']}",
                "-" * 72, r["text"].rstrip("\n")]

    path = os.path.join(HERE, "manual-case-release-history.txt")
    open(path, "w", newline="\n").write("\n".join(out) + "\n")
    print("wrote", redact(path))


SOURCE_PROBES = [
    ("1. -Fc carries DriverOption and NOT CoreOption -- so dxc.exe sees it and\n"
     "   the library does not.",
     ["git", "grep", "-n", "-E", r'^def (Fc|Fh|Fo|Fe|Fd|Fre|Frs|Fsh|Fi) :',
      "--", "include/dxc/Support/HLSLOptions.td"], None),

    ("2. ...and it has been that way since the repo's first commit. `git log -L`\n"
     "   follows the line through renames and reindents; one commit means one\n"
     "   state, ever.",
     ["git", "--no-pager", "log", "-L", "505,505:include/dxc/Support/HLSLOptions.td",
      "--format=%h %ad %s", "--date=short", "-s"], None),

    ("3. The two flag masks, and the two callers that pick between them.",
     ["git", "grep", "-n", "-E",
      r"(CompilerFlags|DxcFlags|RewriterFlags) =|ReadDxcOpts\(", "--",
      "include/dxc/Support/HLSLOptions.h",
      "tools/clang/tools/dxcompiler/dxcutil.cpp",
      "tools/clang/tools/dxclib/dxc.cpp"], None),

    ("4. What an unrecognised option does: it lands in OPT_UNKNOWN, and unless\n"
     "   -Qunused-arguments is present, ReadDxcOpts fails the whole parse.",
     ["git", "grep", "-n", "-A", "6", "Args.filtered(OPT_UNKNOWN)", "--",
      "lib/DxcSupport/HLSLOptions.cpp"], None),

    ("5. ...and -Qunused-arguments IS a CoreOption, which is why it is available\n"
     "   to the library and can switch the failure off.",
     ["git", "grep", "-n", "Qunused_arguments", "--",
      "include/dxc/Support/HLSLOptions.td"], None),

    ("6. ABSENCE: opts.AssemblyCode -- the field -Fc feeds -- has no consumer\n"
     "   anywhere inside dxcompiler/. Only the driver and a test tool act on\n"
     "   it (the third hit, HLSLOptions.cpp:1336, only rejects a non-empty\n"
     "   AssemblyCode when Metal codegen is on). This is why adding CoreOption\n"
     "   to -Fc would not, on its own, implement the feature: nothing in the\n"
     "   library would then act on the value.",
     ["git", "grep", "-n", "AssemblyCode", "--",
      "tools/clang/tools/dxcompiler/"],
     (["git", "grep", "-n", "AssemblyCode", "--", "*.cpp", "*.h"],
      "the same pattern, same tool, repo-wide -- it does match things, and\n"
      "this listing is also the complete set of readers")),

    ("7. ABSENCE: no Compile path produces DXC_OUT_DISASSEMBLY. The only\n"
     "   producer is DxcCompiler::Disassemble; dxcapi.h documents exactly that.",
     ["git", "grep", "-n", "DXC_OUT_DISASSEMBLY", "--",
      "tools/clang/tools/dxcompiler/dxcompilerobj.cpp", "include/dxc/dxcapi.h"],
     (["git", "grep", "-c", "-E", r"DXC_OUT_(OBJECT|ERRORS)", "--",
       "tools/clang/tools/dxcompiler/dxcompilerobj.cpp"],
      "sibling DXC_OUT_* kinds in the same file, to show the file is searched")),

    ("8. Where E_INVALIDARG is manufactured, and why the CALL still returns\n"
     "   S_OK: dxcutil::ReadOptsAndValidate builds an already-finished\n"
     "   DxcResult carrying E_INVALIDARG and sets finished=true; Compile then\n"
     "   hands that result back and returns S_OK. The failure is on the result\n"
     "   object, not on the call -- a caller that only checks the HRESULT of\n"
     "   Compile() sees success.",
     ["git", "grep", "-n", "-B", "6", "-A", "10", "E_INVALIDARG, DXC_OUT_NONE",
      "--", "tools/clang/tools/dxcompiler/dxcutil.cpp"], None),

    ("9. ...and both compile entry points do exactly that: DxcCompiler::Compile\n"
     "   (IDxcCompiler3, line ~562) and DxcCompilerAdapter::WrapCompile (the\n"
     "   legacy IDxcCompiler, line ~1908). Both `return S_OK` with the failed\n"
     "   result. This is why the harness reports call= and status= separately.",
     ["git", "grep", "-n", "-A", "4", "if (finished) {", "--",
      "tools/clang/tools/dxcompiler/dxcompilerobj.cpp"], None),

    ("10. The documentation the 2020 comment relied on. docs/SPIR-V.rst says\n"
     "    the listed options 'are also recognized by the library API calls',\n"
     "    and -Fc is on that list. The measurement says otherwise -- see the\n"
     "    c1-spirv-* rows in manual-case-release-history.txt. This is a real\n"
     "    documentation defect and it is a sufficient explanation for the\n"
     "    2020 reporter's surprise.",
     ["git", "grep", "-n", "-E", r"also recognized by the library|``-Fc``",
      "--", "docs/SPIR-V.rst"],
     (["git", "grep", "-c", "-E", r"``-Fo``", "--", "docs/SPIR-V.rst"],
      "a sibling entry in the same list, to show the list is being searched")),

    ("11. ...and that documentation has said so since before the issue was\n"
     "    filed: the -Fc bullet since 2017, the 'also recognized' sentence\n"
     "    since 2018. The issue is from 2019-11 and the comment from 2020-07.",
     ["git", "--no-pager", "log", "-L", "4211,4211:docs/SPIR-V.rst",
      "-L", "4197,4198:docs/SPIR-V.rst", "--format=%h %ad %s",
      "--date=short", "-s"], None),
]


def source():
    out = [
        "#2604 -- the source behind the measurement",
        "",
        "Produced by `python measure-2604.py --source`, run from a checkout of",
        "the repo this file lives in. Every command is echoed exactly as",
        "executed; re-run any of them yourself.",
        "",
        "Probes 6 and 7 are ABSENCE claims. Each is preceded by a",
        "known-positive CONTROL: the same pattern and the same tool, over a",
        "scope where it is known to match. Without that, an empty result is",
        "indistinguishable from a typo, a bad path filter, or a tool that",
        "quietly declines to search -- which is a mistake this workflow has",
        "made before.",
        "",
    ]
    for title, cmd, control in SOURCE_PROBES:
        out += ["=" * 72, title, "=" * 72, ""]
        if control:
            ccmd, cwhy = control
            rc, text = run(ccmd, cwd=REPO)
            out += [f"CONTROL ({cwhy}):", "$ " + subprocess.list2cmdline(ccmd),
                    f"[exit] {rc}",
                    text.rstrip("\n") if text.strip() else "(no output)",
                    "", "CLAIM:"]
        rc, text = run(cmd, cwd=REPO)
        out += ["$ " + subprocess.list2cmdline(cmd), f"[exit] {rc}"]
        if text.strip():
            out += [text.rstrip("\n")]
        else:
            out += ["(no output -- git grep exits 1 when nothing matched)"]
        out += [""]
    path = os.path.join(HERE, "manual-case-source-evidence.txt")
    open(path, "w", newline="\n").write("\n".join(out) + "\n")
    print("wrote", redact(path))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contrast", action="store_true")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--source", action="store_true")
    a = ap.parse_args()
    if not (a.contrast or a.history or a.source):
        ap.error("pick --contrast, --history, --source, or any combination")
    if (a.contrast or a.history) and not os.path.isfile(HARNESS):
        sys.exit(f"no harness at {redact(HARNESS)}; run build-fc2604.cmd")
    if a.contrast:
        contrast()
    if a.history:
        history()
    if a.source:
        source()


if __name__ == "__main__":
    main()
