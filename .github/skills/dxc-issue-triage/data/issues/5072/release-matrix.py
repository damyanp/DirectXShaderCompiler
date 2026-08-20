"""#5072 release history -- has "-Fh with no -Vn on a library profile" ever
produced a legal identifier?

`triage.py bisect` refuses this issue (it is registered against
`main-debug-fh`, a harness, not dxc -- see `refuse_harness_bisect` in
triage.py). The reason a harness is unavoidable here also determines how
history has to be measured: `-Fh`'s header-writing code
(`DxcContext::WriteHeader` in tools/clang/tools/dxclib/dxc.cpp) lives in the
**dxc.exe driver itself**, not in dxcompiler.dll, so unlike #3237's reflection
bug (fixed harness .exe, swap dxcompiler.dll) this one needs each release's
OWN dxc.exe run end-to-end. `fh-header-check.py` already supports exactly
that indirection through `DXC_FH_REAL_EXE`, so this script imports its
`find_fh_path`/`check_header` and drives them against every cached release's
dxc.exe directly, with no dependency on `triage.py compiler`/`run` at all.

Two shaders are run against every release (the per-release feature-presence
control SKILL.md requires, "run the control on every probed release, not
only on ground truth"):

  repro.hlsl  (-T lib_6_3 -Fh <tmp> repro.hlsl)             -- the probe
  repro.hlsl  (-T cs_6_0 -E CSMain -Fh <tmp> repro.hlsl)    -- non-library
                                                               control: -Fh
                                                               on the very
                                                               same source,
                                                               but not a
                                                               library
                                                               profile, so it
                                                               must produce a
                                                               VALID name on
                                                               every release
                                                               if the defect
                                                               is really
                                                               library-profile
                                                               -specific and
                                                               not just
                                                               "-Fh is always
                                                               broken here".

Usage:
    python release-matrix.py            # every cached release, then main-debug
"""
import json
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
DB = os.path.join(SKILL, ".cache", "triage.db")
BUILD_BIN = os.environ.get("DXC_BUILD_BIN") or os.path.join(
    REPO, "build", "Debug", "bin")

# fh-header-check.py has a hyphen, which is not a valid module name for a
# plain `import`; load it by file path instead of renaming/duplicating the
# checker it shares with the registered harness (one reader, one set of
# regexes, used both ways).
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "fh_header_check", os.path.join(HERE, "fh-header-check.py"))
fh_header_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fh_header_check)

CASES = [
    ("library (repro)", ["-T", "lib_6_3", "-Fh", "{out}", "repro.hlsl"]),
    ("non-library (control)",
     ["-T", "cs_6_0", "-E", "CSMain", "-Fh", "{out}", "repro.hlsl"]),
]


def redact(path):
    """Same tokens/order as scripts/triage.py's redact_paths, derived from
    this file's own location rather than a hardcoded root (SKILL.md: "never
    a token baked into an executable file")."""
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
    if not os.path.isfile(DB):
        sys.exit(f"no triage database at {DB}; run `triage.py catalog` first")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT tag, build_date, cached_path FROM releases"
        " WHERE cached_path IS NOT NULL ORDER BY build_date").fetchall()
    con.close()
    return [r for r in rows if os.path.isfile(r[2])]


def measure(label, dxc_exe, case_label, template):
    out_name = f"scratch-{label}-{case_label}.h".replace(" ", "_").replace(
        "(", "").replace(")", "")
    out_path = os.path.join(HERE, out_name)
    if os.path.isfile(out_path):
        os.remove(out_path)
    argv = [a.format(out=out_name) for a in template]
    p = subprocess.run([dxc_exe] + argv, capture_output=True, text=True,
                      encoding="utf-8", errors="replace", cwd=HERE,
                      timeout=120)
    status, name = fh_header_check.check_header(out_path)
    if os.path.isfile(out_path):
        os.remove(out_path)
    r = {"label": label, "case": case_label, "dxc": redact(dxc_exe),
         "cmd": redact(dxc_exe) + " " + subprocess.list2cmdline(argv),
         "exit": p.returncode, "status": status, "name": name,
         "stdout": p.stdout, "stderr": p.stderr}
    if status == "no-file" or status == "no-declaration":
        r["verdict"] = "invalid-probe"
    elif status == "invalid":
        r["verdict"] = "repro"
    else:  # "valid"
        r["verdict"] = "no-repro"
    return r


def report(rows):
    out = [
        "#5072 release history -- '-Fh' default identifier on library "
        "profiles",
        "",
        "Produced by `python release-matrix.py`. Each row runs THAT",
        "RELEASE's own dxc.exe end-to-end (the -Fh header-writing code is",
        "in the dxc.exe driver, tools/clang/tools/dxclib/dxc.cpp, not in",
        "dxcompiler.dll -- unlike #3237's reflection bug there is no DLL to",
        "swap under a fixed harness; the whole release binary has to run).",
        "",
        "`triage.py bisect` refuses this issue because its ground truth is",
        "the `main-debug-fh` harness, not dxc (see refuse_harness_bisect in",
        "scripts/triage.py).",
        "",
        "CASES",
        "  library (repro)         -T lib_6_3 -Fh <out> repro.hlsl",
        "  non-library (control)   -T cs_6_0 -E CSMain -Fh <out> repro.hlsl",
        "",
    ]
    for case_label, _ in CASES:
        sel = [r for r in rows if r["case"] == case_label]
        out += [f"--- case: {case_label} ---", "",
                f"{'release':>16}  {'identifier':<20}  verdict",
                f"{'-'*16}  {'-'*20}  {'-'*7}"]
        for r in sel:
            out.append(f"{r['label']:>16}  {str(r['name'] or '-'):<20}  "
                       f"{r['verdict']}"
                       + (f"  [{r['status']}]"
                          if r['verdict'] == "invalid-probe" else ""))
        out.append("")

    out += ["", "VERBATIM. The oldest probeable release, the newest",
            "release, and ground truth, in full, for the library case.",
            "Command lines are reconstructed with subprocess.list2cmdline",
            "from the argv that actually ran; paths are collapsed to",
            "<cache>/<triage>/<repo> placeholders.", ""]
    scored = [r for r in rows if r["case"] == "library (repro)"
              and r["verdict"] in ("repro", "no-repro")]
    rel = [r for r in scored if r["label"] != "main-debug"]
    show = []
    for r in ([rel[0], rel[-1]] if len(rel) > 1 else rel) + \
            [r for r in scored if r["label"] == "main-debug"]:
        if r not in show:
            show.append(r)
    for r in show:
        out += [f"--- {r['label']} ---", f"$ {r['cmd']}", f"[exit] {r['exit']}",
               "--- stdout ---"]
        out += ["  " + ln for ln in r["stdout"].rstrip().splitlines()]
        out += ["--- stderr ---"]
        out += ["  " + ln for ln in r["stderr"].rstrip().splitlines()]
        out.append("")

    with open(os.path.join(HERE, "manual-case-release-history.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def main():
    targets = []
    for tag, _date, dxc in releases():
        targets.append((tag, dxc))
    main_debug_dxc = os.path.join(BUILD_BIN, "dxc.exe")
    if os.path.isfile(main_debug_dxc):
        targets.append(("main-debug", main_debug_dxc))
    else:
        print(f"main-debug dxc.exe not found at {main_debug_dxc}; skipped",
              file=sys.stderr)

    rows = []
    for case_label, template in CASES:
        for label, dxc_exe in targets:
            r = measure(label, dxc_exe, case_label, template)
            rows.append(r)
            print(f"{label:>16}  {case_label:<24}  name={str(r['name']):<20}"
                 f"  {r['verdict']}"
                 + (f"  [{r['status']}]"
                    if r['verdict'] == "invalid-probe" else ""))

    with open(os.path.join(HERE, "release-matrix.json"), "w",
              encoding="utf-8") as f:
        json.dump([{k: v for k, v in r.items()
                   if k not in ("stdout", "stderr")} for r in rows],
                  f, indent=2)
    report(rows)


if __name__ == "__main__":
    main()
