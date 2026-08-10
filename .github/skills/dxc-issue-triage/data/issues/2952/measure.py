"""#2952 -- release matrix for "can a reflection container report a DXR entry's
ray payload size and shader kind?"

`triage.py bisect` CANNOT answer this, and running it anyway is worse than
useless. It resolves a release tag to that release's **dxc.exe** and builds its
command line from `cmd.txt`; dxc.exe never calls ID3D12LibraryReflection, so
every release would score `no-repro` and the run would report a confident
"never repro'd in releases" -- the exact inverse of the truth. The same
limitation has now been recorded on #2918, #2922, #2923, #3237 and #2604.

What makes the history measurable anyway is that the whole reflection
implementation lives inside **dxcompiler.dll**, which every release ships:

    set DXC_REFLECT_DLL=<release>/dxcompiler.dll
    refl2952.exe -T lib_6_3 repro.hlsl

so each row below drives THAT RELEASE's own reflection code, in the same way
#2922/#2923 drove each release's own PIX passes through `dxopt -external`. No
GPU, driver or D3D runtime is involved: IDxcContainerReflection and
ID3D12LibraryReflection need no device.

Three columns are measured per release, and they are three different claims:

  api-kind      does D3D12_FUNCTION_DESC.Version decode to the entry's DXIL
                shader kind, agreeing with what the container recorded?
  api-payload   does ANY numeric field of D3D12_FUNCTION_DESC hold the payload
                size the container recorded for that entry?
  rdat-payload  did this release record PayloadSizeInBytes in the RDAT part at
                all? This is the load-bearing one: if the data were not in the
                container, no reflection-API change alone could expose it.

Two shaders are run against every release, not one:

  repro.hlsl             one entry of every DXR 1.0 shader kind, 28-byte payload
  control-nonrt-lib.hlsl a library with no raytracing entries

The second is the per-release feature-presence control SKILL.md requires ("Run
the feature-presence control on every probed release, not only on ground
truth"). It separates "this release cannot compile a library at all" from "this
release cannot compile a *raytracing* library" from "this release compiled it
and the answer is genuinely no".

A caveat about provenance for the rdat-* columns, stated because it is easy to
miss: the harness parses RDAT with THIS REPO's reader, while the container is
produced by the release under test. That is the right arrangement for the
question being asked -- did this release WRITE the field -- but it is not a test
of that release's ability to read it back. `--history` therefore also emits an
independent second witness: each release's own dxc.exe compiles repro.hlsl to a
container, and the ground-truth `dxa -dumprdat` reports what is in it.

Usage:
    python measure.py            # local Debug build only
    python measure.py --history  # every cached release, then the local build

Paths come from the triage database and from DXC_BUILD_BIN, falling back to the
repo's Debug build. Every command echoed into the report is reconstructed with
subprocess.list2cmdline from the argv that actually ran, so the transcript is
derived rather than transcribed (SKILL.md, measured on #2922).
"""

import argparse
import json
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
HARNESS = os.path.join(HERE, "bin", "refl2952.exe")
OUTDIR = os.path.join(HERE, "out")

ARGS = ["-T", "lib_6_3"]
SHADERS = [("repro", "repro.hlsl"), ("nonrt", "control-nonrt-lib.hlsl")]

RE_RESULT = re.compile(
    r"^RESULT: API-SHADER-KIND=(\S+) API-PAYLOAD-SIZE=(\S+) "
    r"RDAT-SHADER-KIND=(\S+) RDAT-PAYLOAD-SIZE=(\S+)$", re.M)
RE_SUMMARY = re.compile(
    r"^SUMMARY: payload-carrying-entries=(\d+) api-payload-found=(\d+) "
    r"kind-checked=(\d+) kind-agrees=(\d+)$", re.M)
RE_SELFTEST = re.compile(r"^SELFCHECK: field-search-selftest=(\S+)$", re.M)
RE_INCOMPLETE = re.compile(r"^refl2952: WALK-INCOMPLETE: (.*)$", re.M)
RE_RDAT_PAYLOAD = re.compile(r"PayloadSizeInBytes: (\d+)")
RE_RDAT_KIND = re.compile(r"ShaderKind: (\w+)")


def redact(path):
    """Absolute path -> the placeholders triage.py writes in capture headers.

    Same tokens and same most-specific-first order as scripts/triage.py:
    <cache>, <triage>, <repo>, forward slashes. These files are committed, so an
    absolute path would ship one machine's directory layout to everyone and
    leave an artifact nobody else can re-run. refl2952.cpp has the same function
    for the lines it prints; both writers have to do it, because triage.py only
    redacts the header lines IT writes (#3237's method note 8).
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


def releases():
    """(tag, build_date, dxc.exe) for every cached release, oldest first.

    Non-bisectable releases are included on purpose. v1.5.2003 is flagged
    bisectable=0 (it is a GitHub prerelease), which leaves a fourteen-month hole
    between v1.4.1907 (2019-07) and v1.5.2010 (2020-10) -- and this issue was
    filed in June 2020, inside that hole. SKILL.md says to run it by hand and
    say so; running it here is cheaper than remembering to.
    """
    if not os.path.isfile(DB):
        sys.exit(f"no triage database at {DB}; run `triage.py catalog` first")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT tag, build_date, cached_path FROM releases"
        " WHERE cached_path IS NOT NULL ORDER BY build_date").fetchall()
    con.close()
    return [r for r in rows if os.path.isfile(r[2])]


def measure(label, dll, shader_label, shader):
    """Run the harness against one dxcompiler.dll and score the walk."""
    argv = [HARNESS] + ARGS + [shader]
    env = dict(os.environ, DXC_REFLECT_DLL=dll)
    p = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                       cwd=HERE, env=env, timeout=300)
    text = p.stdout + p.stderr
    r = {"label": label, "shader": shader_label, "dll": redact(dll),
         "cmd": redact(argv[0]) + " " + subprocess.list2cmdline(argv[1:]),
         "exit": p.returncode, "output": text}

    inc = RE_INCOMPLETE.search(text)
    res = RE_RESULT.search(text)
    summ = RE_SUMMARY.search(text)
    self_ = RE_SELFTEST.search(text)
    r["api_kind"] = res.group(1) if res else None
    r["api_payload"] = res.group(2) if res else None
    r["rdat_kind"] = res.group(3) if res else None
    r["rdat_payload"] = res.group(4) if res else None
    r["payload_entries"] = int(summ.group(1)) if summ else None
    r["api_payload_found"] = int(summ.group(2)) if summ else None
    r["kind_checked"] = int(summ.group(3)) if summ else None
    r["kind_agrees"] = int(summ.group(4)) if summ else None
    r["selftest"] = self_.group(1) if self_ else None

    if inc:
        # The walk stopped early: this release could not answer the question and
        # the row is evidence of nothing about the API.
        r["why"] = inc.group(1)
        r["verdict"] = "invalid-probe"
    elif res is None:
        # A completed walk always prints RESULT. Reaching here means the output
        # is not what this reader expects -- say so loudly rather than scoring
        # it, because a reader that can return "nothing here" and "nothing
        # matched" through the same channel will eventually be believed (#2923).
        r["why"] = "PARSE-WARNING: walk completed but no RESULT line was found"
        r["verdict"] = "unreadable"
    elif r["selftest"] != "pass":
        r["why"] = "PARSE-WARNING: the field search failed its own self-test"
        r["verdict"] = "unreadable"
    elif r["api_payload"] == "unavailable" and (r["payload_entries"] or 0) > 0:
        r["verdict"] = "repro"
    elif r["api_payload"] == "n/a":
        # No payload-carrying entry: nothing was asked, so nothing was answered.
        r["verdict"] = "no-payload-entries"
    else:
        r["verdict"] = "no-repro"
    return r


def dxa_witness(tag, dxc_exe):
    """Independent second witness for the rdat-* columns.

    Compile repro.hlsl with THAT RELEASE's own dxc.exe, then read the resulting
    container with the ground-truth `dxa -dumprdat`. This shares no code with
    the harness's walk, so it checks that the payload sizes reported above are a
    property of the container and not of how the harness reads it.
    """
    dxa = os.path.join(BUILD_BIN, "dxa.exe")
    if not os.path.isfile(dxa):
        return {"tag": tag, "error": "no dxa.exe in the ground-truth build"}
    os.makedirs(OUTDIR, exist_ok=True)
    dxil = os.path.join(OUTDIR, f"repro-{tag}.dxil")
    argv1 = [dxc_exe, "-T", "lib_6_3", "repro.hlsl", "-Fo", dxil]
    p1 = subprocess.run(argv1, capture_output=True, text=True,
                        errors="replace", cwd=HERE, timeout=300)
    row = {"tag": tag,
           "compile_cmd": redact(argv1[0]) + " " +
                          subprocess.list2cmdline([redact(a) for a in argv1[1:]]),
           "compile_exit": p1.returncode}
    if p1.returncode != 0 or not os.path.isfile(dxil):
        row["error"] = (p1.stdout + p1.stderr).strip()[:400]
        return row
    argv2 = [dxa, "-dumprdat", dxil]
    p2 = subprocess.run(argv2, capture_output=True, text=True,
                        errors="replace", cwd=HERE, timeout=300)
    text = p2.stdout + p2.stderr
    row["dump_cmd"] = (redact(argv2[0]) + " " +
                       subprocess.list2cmdline([redact(a) for a in argv2[1:]]))
    row["dump_exit"] = p2.returncode
    payloads = sorted({int(m) for m in RE_RDAT_PAYLOAD.findall(text)})
    kinds = sorted(set(RE_RDAT_KIND.findall(text)))
    row["payload_sizes"] = payloads
    row["shader_kinds"] = kinds
    row["has_payload_28"] = 28 in payloads
    if not payloads and not kinds:
        row["error"] = ("dxa -dumprdat reported neither a PayloadSizeInBytes "
                        "nor a ShaderKind; output was: " + text.strip()[:400])
    return row


def report(rows, witnesses):
    out = [
        "#2952 release matrix -- ray payload size / shader kind through the",
        "reflection API",
        "",
        "Produced by `python measure.py --history`. NOT by `triage.py bisect`:",
        "bisect resolves a release tag to that release's dxc.exe, which never",
        "calls ID3D12LibraryReflection, so it would score every release",
        "no-repro and report a confident \"never repro'd in releases\" -- the",
        "inverse of the truth. Each row here instead drives THAT RELEASE's own",
        "reflection implementation:",
        "",
        "    set DXC_REFLECT_DLL=<release>/dxcompiler.dll",
        "    refl2952.exe " + " ".join(ARGS) + " <shader>",
        "",
        "refl2952.exe is built from refl2952.cpp in this directory. It is inert",
        "plumbing: it calls IDxcCompiler::Compile and then walks",
        "IDxcContainerReflection -> ID3D12LibraryReflection ->",
        "ID3D12FunctionReflection, all of which are implemented inside",
        "dxcompiler.dll, so the code under test is the release's.",
        "",
        "COLUMNS",
        "  fns/pay  payload-carrying entries reported by the container",
        "  api-kind can D3D12_FUNCTION_DESC.Version be decoded to the entry's",
        "           shader kind, agreeing with the container?",
        "  api-pay  does any numeric field of D3D12_FUNCTION_DESC hold the",
        "           payload size?",
        "  rdat-pay did this release record PayloadSizeInBytes in RDAT at all?",
        "",
        "SHADERS",
        "  repro  one entry of every DXR 1.0 shader kind; 28-byte payload,",
        "         8-byte attributes, 12-byte callable parameter",
        "  nonrt  a library with no raytracing entries -- the per-release",
        "         feature-presence control",
        "",
    ]
    for shader_label, _ in SHADERS:
        sel = [r for r in rows if r["shader"] == shader_label]
        out += [f"--- shader: {shader_label} ---", "",
                f"{'release':>18} {'pay-entries':>11} {'api-kind':>10}"
                f" {'api-pay':>12} {'rdat-pay':>9}  verdict",
                f"{'-'*18} {'-'*11} {'-'*10} {'-'*12} {'-'*9}  {'-'*7}"]
        for r in sel:
            out.append(
                f"{r['label']:>18} "
                f"{str(r['payload_entries'] if r['payload_entries'] is not None else '-'):>11} "
                f"{str(r['api_kind'] or '-'):>10} "
                f"{str(r['api_payload'] or '-'):>12} "
                f"{str(r['rdat_payload'] or '-'):>9}  "
                f"{r['verdict']}" + (f"  [{r['why']}]" if r.get("why") else ""))
        out.append("")

    if witnesses:
        out += [
            "--- independent second witness: `dxa -dumprdat` ---",
            "",
            "Each release's OWN dxc.exe compiles repro.hlsl; the ground-truth",
            "dxa reads the container it produced. This shares no code with the",
            "harness's walk, so it checks that the payload sizes above are a",
            "property of the container rather than of how the harness reads it.",
            "No release package ships dxa.exe, so the reader is necessarily the",
            "local build in every row.",
            "",
            f"{'release':>18} {'compile':>8} {'payload sizes in RDAT':>26}"
            f"  shader kinds",
            f"{'-'*18} {'-'*8} {'-'*26}  {'-'*12}"]
        for w in witnesses:
            if w.get("error"):
                out.append(f"{w['tag']:>18} {w.get('compile_exit', '-'):>8} "
                           f"{'(see below)':>26}  ERROR")
                continue
            out.append(
                f"{w['tag']:>18} {w['compile_exit']:>8} "
                f"{str(w['payload_sizes']):>26}  "
                f"{','.join(w['shader_kinds'])}")
        out.append("")
        for w in witnesses:
            if w.get("error"):
                out += [f"--- {w['tag']}: error ---", f"$ {w['compile_cmd']}"
                        if w.get("compile_cmd") else "",
                        "  " + w["error"].replace("\n", "\n  "), ""]

    out += ["", "VERBATIM. The oldest probeable release, the newest release, and",
            "ground truth, in full. The command lines are reconstructed with",
            "subprocess.list2cmdline from the argv that actually ran, with paths",
            "collapsed to <cache>/<triage>/<repo> placeholders so the file is",
            "portable; they are not transcriptions.", ""]
    scored = [r for r in rows if r["shader"] == "repro"
              and r["verdict"] in ("repro", "no-repro")]
    rel = [r for r in scored if r["label"] != "main-debug"]
    show = []
    for r in ([rel[0], rel[-1]] if len(rel) > 1 else rel) + \
            [r for r in scored if r["label"] == "main-debug"]:
        if r not in show:
            show.append(r)
    for r in show:
        out += [f"--- {r['label']} ---",
                f"$ set DXC_REFLECT_DLL={r['dll']}",
                f"$ {r['cmd']}",
                f"[exit] {r['exit']}"]
        out += ["  " + ln for ln in r["output"].rstrip().splitlines()]
        out.append("")

    with open(os.path.join(HERE, "manual-case-release-matrix.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true",
                    help="measure every cached release as well as the local build")
    a = ap.parse_args()

    if not os.path.isfile(HARNESS):
        sys.exit(f"missing {HARNESS}; run build-refl2952.cmd first")

    targets = []
    witness_targets = []
    if a.history:
        for tag, _date, dxc in releases():
            dll = os.path.join(os.path.dirname(dxc), "dxcompiler.dll")
            if os.path.isfile(dll):
                targets.append((tag, dll))
                witness_targets.append((tag, dxc))
            else:
                print(f"{tag:>18}  (no dxcompiler.dll beside dxc.exe; skipped)")
    targets.append(("main-debug", os.path.join(BUILD_BIN, "dxcompiler.dll")))
    witness_targets.append(("main-debug", os.path.join(BUILD_BIN, "dxc.exe")))

    rows = []
    for shader_label, shader in SHADERS:
        for label, dll in targets:
            r = measure(label, dll, shader_label, shader)
            rows.append(r)
            print(f"{label:>18} {shader_label:>6}  pay-entries="
                  f"{str(r['payload_entries']):>4} api-kind="
                  f"{str(r['api_kind']):>10} api-pay="
                  f"{str(r['api_payload']):>12}  {r['verdict']}"
                  + (f"  [{r['why']}]" if r.get("why") else ""))

    witnesses = []
    if a.history:
        print()
        for tag, dxc in witness_targets:
            w = dxa_witness(tag, dxc)
            witnesses.append(w)
            print(f"{tag:>18} dxa -dumprdat  payloads="
                  f"{w.get('payload_sizes')}  kinds={w.get('shader_kinds')}"
                  + (f"  ERROR {w['error'][:80]}" if w.get("error") else ""))

    with open(os.path.join(HERE, "measure.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": [{k: v for k, v in r.items() if k != "output"}
                            for r in rows],
                   "dxa_witness": witnesses}, f, indent=2)
    if a.history:
        report(rows, witnesses)


if __name__ == "__main__":
    main()
