"""#3237 -- does ID3D12FunctionParameterReflection::GetDesc return E_FAIL on
every DXC release, and did it ever return anything else?

`triage.py bisect` cannot answer this. It resolves a release tag to that
release's **dxc.exe** and builds its command line from `cmd.txt`, and the
defect is in an interface dxc.exe never calls -- so every release would score
`no-repro` and the run would report a confident "never repro'd in releases",
which is the exact opposite of the truth. The same limitation was recorded on
#2923.

What makes the history measurable anyway is that the whole reflection
implementation lives inside **dxcompiler.dll**, which every release ships:

    set DXC_REFLECT_DLL=<release>/dxcompiler.dll
    refl3237.exe -T lib_6_3 repro.hlsl

so each row below drives THAT RELEASE's own reflection code, in the same way
#2922 drove each release's own PIX passes through `dxopt -external`. No GPU,
driver or D3D runtime is involved; `IDxcContainerReflection` and
`ID3D12LibraryReflection` need no device.

Two shaders are run against every release, not one:

  repro.hlsl           `export float3 Apply(float3 input)` -- the probe.
  repro-as-filed.hlsl  the issue body's source, with no `export`.

The second is the per-release feature-presence control that SKILL.md requires
("Run the feature-presence control on every probed release, not only on ground
truth"). It also settles a claim the write-up would otherwise have to assume:
that the source exactly as filed reflects zero functions. If some old release
*did* reflect it, the reporter's own source is a valid probe there and the
history has to say so.

The observable is the HRESULT from `ID3D12FunctionParameterReflection::GetDesc`
on parameter 0. `0x80004005` (E_FAIL) is the reported symptom. Note that this
is an API return value and NOT the harness's process exit code -- dxc.exe
returns the same number for ordinary diagnosed errors, and conflating the two
is the specific trap this issue sets.

Usage:
    python measure.py            # local Debug build only
    python measure.py --history  # every cached release, then the local build

Paths come from the triage database and from DXC_BUILD_BIN, falling back to the
repo's Debug build.
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
HARNESS = os.path.join(HERE, "bin", "refl3237.exe")

ARGS = ["-T", "lib_6_3"]
SHADERS = [("repro", "repro.hlsl"), ("as-filed", "repro-as-filed.hlsl")]

RE_HR = re.compile(r"^(.*) -> (0x[0-9A-F]{8}) \(([A-Z_]+|\(other\))\)$", re.M)
RE_FNCOUNT = re.compile(r"D3D12_LIBRARY_DESC\.FunctionCount=(\d+)")
RE_PARAMCOUNT = re.compile(r"D3D12_FUNCTION_DESC\.FunctionParameterCount=(-?\d+)")
RE_RESULT = re.compile(r"^RESULT: PARAM0-GETDESC=(0x[0-9A-F]+) "
                       r"RETURN-GETDESC=(0x[0-9A-F]+) PARAMCOUNT=(-?\d+)$", re.M)
RE_INCOMPLETE = re.compile(r"^refl3237: WALK-INCOMPLETE: (.*)$", re.M)


def redact(path):
    """Absolute path -> the placeholders triage.py writes in capture headers.

    Same tokens and same most-specific-first order as scripts/triage.py:
    <cache>, <triage>, <repo>, forward slashes. These files are committed, so
    an absolute path would ship one machine's directory layout to everyone and
    leave an artifact nobody else can re-run. refl3237.cpp has the same
    function for the lines it prints; both have to do it, because each writes
    its own output.
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
    bisectable=0 (it is a GitHub prerelease), which leaves a fourteen-month
    hole in the scan exactly where 2020 issues live -- and this issue was filed
    in November 2020. SKILL.md says to run it by hand and say so; running it
    here is cheaper than remembering to.
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
    # Store the redacted forms only. The command is echoed through
    # list2cmdline first so quoting is faithful, then the executable path is
    # collapsed -- what lands in measure.json is still exactly what ran, just
    # expressed in the placeholders every other artifact here uses.
    r = {"label": label, "shader": shader_label, "dll": redact(dll),
         "cmd": redact(argv[0]) + " " + subprocess.list2cmdline(argv[1:]),
         "exit": p.returncode, "output": text}

    inc = RE_INCOMPLETE.search(text)
    fc = RE_FNCOUNT.search(text)
    r["function_count"] = int(fc.group(1)) if fc else None
    res = RE_RESULT.search(text)
    if res:
        r["param0_hr"] = res.group(1)
        r["return_hr"] = res.group(2)
        r["param_count"] = int(res.group(3))
    else:
        r["param0_hr"] = r["return_hr"] = None
        pc = RE_PARAMCOUNT.search(text)
        r["param_count"] = int(pc.group(1)) if pc else None

    if inc:
        # The walk stopped early. For repro.hlsl that means this release could
        # not answer the question at all and the row is evidence of nothing;
        # for repro-as-filed.hlsl a stop at "zero functions" IS the result.
        r["why"] = inc.group(1)
        r["verdict"] = "invalid-probe"
    elif r["param0_hr"] is None:
        # A completed walk always prints RESULT. Reaching here means the output
        # is not what this reader expects -- say so loudly rather than scoring
        # it, because a reader that can return "nothing here" and "nothing
        # matched" through the same channel will eventually be believed (#2923).
        r["why"] = "PARSE-WARNING: walk completed but no RESULT line was found"
        r["verdict"] = "unreadable"
    elif int(r["param0_hr"], 16) == 0x80004005:
        r["verdict"] = "repro"
    else:
        r["verdict"] = "no-repro"
    return r


def report(rows):
    out = [
        "#3237 release history -- ID3D12FunctionParameterReflection::GetDesc",
        "",
        "Produced by `python measure.py --history`. Each row drives THAT",
        "RELEASE's own reflection implementation, by pointing the harness at",
        "that release's dxcompiler.dll:",
        "",
        "    set DXC_REFLECT_DLL=<release>/dxcompiler.dll",
        "    refl3237.exe " + " ".join(ARGS) + " <shader>",
        "",
        "refl3237.exe is built from refl3237.cpp in this directory; it is inert",
        "plumbing (it calls IDxcCompiler::Compile and then walks",
        "IDxcContainerReflection -> ID3D12LibraryReflection ->",
        "ID3D12FunctionReflection -> ID3D12FunctionParameterReflection). Every",
        "one of those interfaces is implemented inside dxcompiler.dll, so the",
        "code under test is the release's, not the harness's.",
        "",
        "triage.py bisect cannot produce this table: it resolves a release tag",
        "to that release's dxc.exe, which never calls the reflection API.",
        "",
        "COLUMNS",
        "  fns    D3D12_LIBRARY_DESC.FunctionCount",
        "  pcount D3D12_FUNCTION_DESC.FunctionParameterCount",
        "  param0 HRESULT from ID3D12FunctionParameterReflection::GetDesc(0)",
        "  ret    HRESULT from GetDesc(D3D_RETURN_PARAMETER_INDEX)",
        "",
        "SHADERS",
        "  repro     export float3 Apply(float3 input) { return input * 2.0f; }",
        "  as-filed  the issue body's source verbatim, with no `export`",
        "",
    ]
    for shader_label, _ in SHADERS:
        sel = [r for r in rows if r["shader"] == shader_label]
        out += [f"--- shader: {shader_label} ---", "",
                f"{'release':>16} {'fns':>4} {'pcount':>7} {'param0':>12}"
                f" {'ret':>12}  verdict",
                f"{'-'*16} {'-'*4} {'-'*7} {'-'*12} {'-'*12}  {'-'*7}"]
        for r in sel:
            out.append(
                f"{r['label']:>16} {str(r['function_count'] if r['function_count'] is not None else '-'):>4} "
                f"{str(r['param_count'] if r['param_count'] is not None else '-'):>7} "
                f"{str(r['param0_hr'] or '-'):>12} {str(r['return_hr'] or '-'):>12}  "
                f"{r['verdict']}" + (f"  [{r['why']}]" if r.get("why") else ""))
        out.append("")

    out += ["", "VERBATIM. The oldest probeable release, the newest release, and",
            "ground truth, in full. The command lines are reconstructed with",
            "subprocess.list2cmdline from the argv that actually ran, with",
            "paths collapsed to <cache>/<triage>/<repo> placeholders so the",
            "file is portable; they are not transcriptions.", ""]
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

    with open(os.path.join(HERE, "manual-case-release-history.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true",
                    help="measure every cached release as well as the local build")
    a = ap.parse_args()

    if not os.path.isfile(HARNESS):
        sys.exit(f"missing {HARNESS}; run build-refl3237.cmd first")

    targets = []
    if a.history:
        for tag, _date, dxc in releases():
            dll = os.path.join(os.path.dirname(dxc), "dxcompiler.dll")
            if os.path.isfile(dll):
                targets.append((tag, dll))
            else:
                print(f"{tag:>16}  (no dxcompiler.dll beside dxc.exe; skipped)")
    targets.append(("main-debug", os.path.join(BUILD_BIN, "dxcompiler.dll")))

    rows = []
    for shader_label, shader in SHADERS:
        for label, dll in targets:
            r = measure(label, dll, shader_label, shader)
            rows.append(r)
            print(f"{label:>16} {shader_label:>9}  fns="
                  f"{str(r['function_count']):>4} pcount="
                  f"{str(r['param_count']):>4} param0="
                  f"{str(r['param0_hr']):>10}  {r['verdict']}"
                  + (f"  [{r['why']}]" if r.get("why") else ""))

    with open(os.path.join(HERE, "measure.json"), "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in r.items() if k != "output"} for r in rows],
                  f, indent=2)
    if a.history:
        report(rows)


if __name__ == "__main__":
    main()
