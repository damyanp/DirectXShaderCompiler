"""Release-history matrix for #5416: does "-MD -MF <dep> -Fo <obj>" produce
the object file, across every catalogued stable release plus main-debug?

triage.py's text-based match.json predicates cannot see file existence (only
captured stdout/stderr), so this issue's actual instrument is a small harness
that deletes any stale output, runs dxc, and reports PRESENT/MISSING for both
the depfile and the object file. Run from the issue directory:

    python check-output-presence.py

Writes manual-case-release-history.txt. All paths are machine-independent:
they are derived from this file's own location, not hardcoded, and displayed
with the same <repo>/<cache> tokens triage.py uses for committed captures.
"""
import os
import subprocess

ISSUE_DIR = os.path.dirname(os.path.abspath(__file__))
# .../<repo>/.github/skills/dxc-issue-triage/data/issues/5416
SKILL_DIR = os.path.abspath(os.path.join(ISSUE_DIR, "..", "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))
CACHE_ROOT = os.path.join(SKILL_DIR, ".cache")

SHADER = "repro.hlsl"
ARGS_TEMPLATE = ["-T", "lib_6_7", "-O3", "-MD", "-MF", "{dep}", "-Fo", "{obj}", SHADER]

# (tag, base kind, path relative to that base), ordered oldest to newest.
# `cache` entries live under the triage skill's release cache; `repo` entries
# are trees the DXC test infrastructure already downloaded under
# build/tools/clang/test/dxc_releases, adopted via `catalog --seed-from`.
RELEASES = [
    ("v1.4.1907", "cache", r"compilers\releases\v1.4.1907\dxc.exe"),
    ("v1.5.2003", "cache", r"compilers\releases\v1.5.2003\bin\x64\dxc.exe"),
    ("v1.5.2010", "cache", r"compilers\releases\v1.5.2010\bin\x64\dxc.exe"),
    ("v1.6.2104", "cache", r"compilers\releases\v1.6.2104\bin\x64\dxc.exe"),
    ("v1.6.2106", "cache", r"compilers\releases\v1.6.2106\bin\x64\dxc.exe"),
    ("v1.6.2112", "repo", r"build\tools\clang\test\dxc_releases\v1.6.2112\dxc_2021_12_08\bin\x64\dxc.exe"),
    ("v1.7.2207", "cache", r"compilers\releases\v1.7.2207\bin\x64\dxc.exe"),
    ("v1.7.2212", "cache", r"compilers\releases\v1.7.2212\bin\x64\dxc.exe"),
    ("v1.7.2212.1", "cache", r"compilers\releases\v1.7.2212.1\bin\x64\dxc.exe"),
    ("v1.7.2308", "repo", r"build\tools\clang\test\dxc_releases\v1.7.2308\dxc_2023_08_14\bin\x64\dxc.exe"),
    ("v1.8.2403", "cache", r"compilers\releases\v1.8.2403\bin\x64\dxc.exe"),
    ("v1.8.2403.1", "cache", r"compilers\releases\v1.8.2403.1\bin\x64\dxc.exe"),
    ("v1.8.2403.2", "cache", r"compilers\releases\v1.8.2403.2\bin\x64\dxc.exe"),
    ("v1.8.2405", "cache", r"compilers\releases\v1.8.2405\bin\x64\dxc.exe"),
    ("v1.8.2407", "cache", r"compilers\releases\v1.8.2407\bin\x64\dxc.exe"),
    ("v1.8.2502", "repo", r"build\tools\clang\test\dxc_releases\v1.8.2502\dxc_2025_02_20\bin\x64\dxc.exe"),
    ("v1.8.2505", "cache", r"compilers\releases\v1.8.2505\bin\x64\dxc.exe"),
    ("v1.8.2505.1", "repo", r"build\tools\clang\test\dxc_releases\v1.8.2505.1\dxc_2025_07_14\bin\x64\dxc.exe"),
    ("v1.9.2602", "cache", r"compilers\releases\v1.9.2602\bin\x64\dxc.exe"),
    ("v1.9.2602.24", "cache", r"compilers\releases\v1.9.2602.24\bin\x64\dxc.exe"),
    ("v1.9.2607", "cache", r"compilers\releases\v1.9.2607\bin\x64\dxc.exe"),
    ("main-debug", "repo", r"build\Debug\bin\dxc.exe"),
]


def resolve(base_kind, rel):
    base = CACHE_ROOT if base_kind == "cache" else REPO_ROOT
    return os.path.join(base, rel)


def display(path):
    """Machine-independent spelling, matching triage.py's display_exe/<cache>
    and <repo> tokens so this committed report never bakes in a local path."""
    for base, token in ((CACHE_ROOT, "<cache>"), (REPO_ROOT, "<repo>")):
        try:
            rel = os.path.relpath(path, base)
        except ValueError:
            continue
        if not rel.startswith(".."):
            return f"{token}/{rel.replace(os.sep, '/')}"
    return path


def present(path):
    if os.path.isfile(path):
        return f"PRESENT ({os.path.getsize(path)} bytes)"
    return "MISSING"


def run_one(tag, exe):
    dep = f"hist-{tag}.d"
    obj = f"hist-{tag}.cso"
    for f in (dep, obj):
        p = os.path.join(ISSUE_DIR, f)
        if os.path.isfile(p):
            os.remove(p)
    args = [exe] + [a.format(dep=dep, obj=obj) for a in ARGS_TEMPLATE]
    lines = [f"=== {tag} ==="]
    lines.append(f"[exe] {display(exe)}")
    lines.append(f"$ dxc {' '.join(args[1:])}")
    try:
        proc = subprocess.run(args, cwd=ISSUE_DIR, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=120)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        rc, out, err = None, "", "TIMEOUT"
    dep_path = os.path.join(ISSUE_DIR, dep)
    obj_path = os.path.join(ISSUE_DIR, obj)
    lines.append(f"[exit] {rc}")
    lines.append(f"[stdout] {out.strip()!r}")
    lines.append(f"[stderr] {err.strip()!r}")
    lines.append(f"[{dep}] {present(dep_path)}")
    lines.append(f"[{obj}] {present(obj_path)}")
    lines.append("")
    # Clean up generated files so the directory doesn't accumulate 22 pairs
    # of near-duplicate artifacts; the report above is the durable evidence.
    for f in (dep_path, obj_path):
        if os.path.isfile(f):
            os.remove(f)
    return "\n".join(lines)


def main():
    report = [
        "# manual-case-release-history.txt for #5416",
        "# Generated by check-output-presence.py -- do not hand-edit.",
        "# Question: with an ordinary valid lib_6_7 shader, does "
        "'-MD -MF <dep> -Fo <obj>' produce <obj>?",
        "# Each release's OWN dxc.exe is invoked with the exact argv shown.",
        "",
    ]
    for tag, base_kind, rel in RELEASES:
        exe = resolve(base_kind, rel)
        if not os.path.isfile(exe):
            report.append(f"=== {tag} ===\nSKIPPED: exe not found at {display(exe)}\n")
            continue
        report.append(run_one(tag, exe))
    text = "\n".join(report)
    out_path = os.path.join(ISSUE_DIR, "manual-case-release-history.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
