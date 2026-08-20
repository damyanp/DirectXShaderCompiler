"""Issue #5704 release-history matrix.

Runs the compile -> link -> dumpbin pipeline for each release, in a FRESH
per-release scratch subdirectory, to avoid the stale-intermediate-file trap
discovered while triaging this issue: dxc's -link step writes -Fo output only
on success, so if two releases share a working directory and a later release's
link fails, dumpbin silently re-disassembles the earlier release's leftover
linked.bc and manufactures a false "repro" for the failing release.

Usage: python measure.py
Writes manual-case-release-history.txt next to this script.
"""
import os
import shutil
import subprocess
import sys

# Anchor on this file's location rather than a hardcoded machine path, per
# the skill's path-hygiene guidance: repo-root-relative paths are portable
# and are not a machine-specific leak the way an absolute `C:\...` is.
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # .../dxc-issue-triage
REPO_ROOT = os.path.abspath(os.path.join(SKILL_ROOT, "..", "..", ".."))  # repo root
CACHE_RELEASES = os.path.join(SKILL_ROOT, ".cache", "compilers", "releases")
TEST_RELEASES = os.path.join(REPO_ROOT, "build", "tools", "clang", "test", "dxc_releases")
REPRO = os.path.join(HERE, "repro.hlsl")

sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
from triage import redact_paths, display_exe  # noqa: E402  same path tokenisation the tool uses


def _cached(tag):
    return os.path.join(CACHE_RELEASES, tag, "bin", "x64", "dxc.exe")


def _seeded(tag, build_dir):
    return os.path.join(TEST_RELEASES, tag, build_dir, "bin", "x64", "dxc.exe")


# (tag, dxc.exe path) - stable releases that accept the -link CLI option,
# oldest to newest, plus main-debug (the ground-truth build under triage).
RELEASES = [
    ("v1.6.2106", _cached("v1.6.2106")),
    ("v1.6.2112", _seeded("v1.6.2112", "dxc_2021_12_08")),
    ("v1.7.2207", _cached("v1.7.2207")),
    ("v1.7.2212", _cached("v1.7.2212")),
    ("v1.7.2212.1", _cached("v1.7.2212.1")),
    ("v1.7.2308", _seeded("v1.7.2308", "dxc_2023_08_14")),
    ("v1.8.2403", _cached("v1.8.2403")),
    ("v1.8.2403.1", _cached("v1.8.2403.1")),
    ("v1.8.2403.2", _cached("v1.8.2403.2")),
    ("v1.8.2405", _cached("v1.8.2405")),
    ("v1.8.2407", _cached("v1.8.2407")),
    ("v1.8.2502", _seeded("v1.8.2502", "dxc_2025_02_20")),
    ("v1.8.2505", _cached("v1.8.2505")),
    ("v1.8.2505.1", _seeded("v1.8.2505.1", "dxc_2025_07_14")),
    ("v1.9.2602", _cached("v1.9.2602")),
    ("v1.9.2602.24", _cached("v1.9.2602.24")),
    ("v1.9.2607", _cached("v1.9.2607")),
    ("main-debug", os.path.join(REPO_ROOT, "build", "Debug", "bin", "dxc.exe")),
]


def measure_one(tag, exe, scratch):
    if os.path.isdir(scratch):
        shutil.rmtree(scratch)
    os.makedirs(scratch)
    shutil.copy(REPRO, os.path.join(scratch, "repro.hlsl"))
    lib_bc = os.path.join(scratch, "lib.bc")
    linked_bc = os.path.join(scratch, "linked.bc")

    lines = []
    lines.append(f"=== {tag} ({display_exe(exe)}) ===")

    # Run with cwd=scratch so the relative repro.hlsl resolves there.
    p1 = subprocess.run([exe, "-T", "lib_6_3", "-Qstrip_reflect", "-O3", "-Fo", "lib.bc", "repro.hlsl"],
                         cwd=scratch, capture_output=True, text=True)
    lines.append(f"$ dxc -T lib_6_3 -Qstrip_reflect -O3 -Fo lib.bc repro.hlsl")
    lines.append(f"[exit] {p1.returncode}")
    if p1.stdout.strip():
        lines.append("--- stdout ---\n" + redact_paths(p1.stdout))
    if p1.stderr.strip():
        lines.append("--- stderr ---\n" + redact_paths(p1.stderr))

    compiled = os.path.isfile(lib_bc)
    lines.append(f"[lib.bc written] {compiled}")

    link_ok = False
    linked_written = False
    if compiled:
        p2 = subprocess.run([exe, "-link", "lib.bc", "-T", "cs_6_3", "-E", "main",
                              "-Qstrip_reflect", "-O3", "-Fo", "linked.bc"],
                             cwd=scratch, capture_output=True, text=True)
        lines.append(f"$ dxc -link lib.bc -T cs_6_3 -E main -Qstrip_reflect -O3 -Fo linked.bc")
        lines.append(f"[exit] {p2.returncode}")
        if p2.stdout.strip():
            lines.append("--- stdout ---\n" + redact_paths(p2.stdout))
        if p2.stderr.strip():
            lines.append("--- stderr ---\n" + redact_paths(p2.stderr))
        link_ok = (p2.returncode == 0)
        linked_written = os.path.isfile(linked_bc)
        lines.append(f"[linked.bc written] {linked_written}")

    disasm = ""
    if link_ok and linked_written:
        p3 = subprocess.run([exe, "-dumpbin", "linked.bc"], cwd=scratch, capture_output=True, text=True)
        lines.append(f"$ dxc -dumpbin linked.bc")
        lines.append(f"[exit] {p3.returncode}")
        disasm = p3.stdout
        lines.append("--- stdout ---\n" + redact_paths(disasm))
        if p3.stderr.strip():
            lines.append("--- stderr ---\n" + redact_paths(p3.stderr))
    else:
        lines.append("[dumpbin skipped: link did not produce linked.bc -- invalid-probe, not a clean result]")

    has_names = ("texResource" in disasm) or ("rwTexResource" in disasm)
    if not (link_ok and linked_written):
        verdict = "invalid-probe (link never produced output)"
    elif has_names:
        verdict = "repro (names leaked through -Qstrip_reflect)"
    else:
        verdict = "no-repro (names stripped)"
    lines.append(f"VERDICT: {verdict}")
    lines.append("")
    return "\n".join(lines), verdict


def main():
    out_path = os.path.join(HERE, "manual-case-release-history.txt")
    all_text = []
    summary = []
    for tag, exe in RELEASES:
        if not os.path.isfile(exe):
            all_text.append(f"=== {tag} ===\n[skipped: exe not found at {display_exe(exe)}]\n")
            summary.append((tag, "skipped (exe missing)"))
            continue
        scratch = os.path.join(HERE, "_scratch_" + tag.replace(".", "_"))
        text, verdict = measure_one(tag, exe, scratch)
        all_text.append(text)
        summary.append((tag, verdict))
        shutil.rmtree(scratch, ignore_errors=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_text))
        f.write("\n\n=== SUMMARY ===\n")
        for tag, verdict in summary:
            f.write(f"{tag}: {verdict}\n")

    print(f"wrote {out_path}")
    for tag, verdict in summary:
        print(f"{tag}: {verdict}")


if __name__ == "__main__":
    main()
