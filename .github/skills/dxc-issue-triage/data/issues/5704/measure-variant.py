"""Issue #5704: same compile -> link -> dumpbin pipeline as measure.py, but
using repro-shader-attr.hlsl (repro.hlsl + an explicit [shader("compute")]
attribute on main). This isolates the actual reported defect (does
-Qstrip_reflect strip resource names from a lib_6_3->cs_6_3 linked target)
from the separate default-linkage/entry-recognition regression that measure.py
found blocks the literal repro from linking at all from v1.8.2403 onward.
Same fresh-scratch-directory discipline as measure.py, for the same reason.
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
REPRO = os.path.join(HERE, "repro-shader-attr.hlsl")

sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
from triage import redact_paths, display_exe  # noqa: E402  same path tokenisation the tool uses


def _cached(tag):
    return os.path.join(CACHE_RELEASES, tag, "bin", "x64", "dxc.exe")


def _seeded(tag, build_dir):
    return os.path.join(TEST_RELEASES, tag, build_dir, "bin", "x64", "dxc.exe")


RELEASES = [
    ("v1.6.2106", _cached("v1.6.2106")),
    ("v1.7.2308", _seeded("v1.7.2308", "dxc_2023_08_14")),
    ("v1.8.2403", _cached("v1.8.2403")),
    ("v1.8.2505", _cached("v1.8.2505")),
    ("v1.9.2607", _cached("v1.9.2607")),
    ("main-debug", os.path.join(REPO_ROOT, "build", "Debug", "bin", "dxc.exe")),
]


def measure_one(tag, exe, scratch):
    if os.path.isdir(scratch):
        shutil.rmtree(scratch)
    os.makedirs(scratch)
    shutil.copy(REPRO, os.path.join(scratch, "repro-shader-attr.hlsl"))
    lib_bc = os.path.join(scratch, "lib.bc")
    linked_bc = os.path.join(scratch, "linked.bc")

    lines = [f"=== {tag} ({display_exe(exe)}) ==="]

    p1 = subprocess.run([exe, "-T", "lib_6_3", "-Qstrip_reflect", "-O3", "-Fo", "lib.bc",
                          "repro-shader-attr.hlsl"], cwd=scratch, capture_output=True, text=True)
    lines.append("$ dxc -T lib_6_3 -Qstrip_reflect -O3 -Fo lib.bc repro-shader-attr.hlsl")
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
        lines.append("$ dxc -link lib.bc -T cs_6_3 -E main -Qstrip_reflect -O3 -Fo linked.bc")
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
        lines.append("$ dxc -dumpbin linked.bc")
        lines.append(f"[exit] {p3.returncode}")
        disasm = p3.stdout
        lines.append("--- stdout ---\n" + redact_paths(disasm))
    else:
        lines.append("[dumpbin skipped: link did not produce linked.bc -- invalid-probe]")

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
    out_path = os.path.join(HERE, "manual-case-shader-attr-history.txt")
    all_text = []
    summary = []
    for tag, exe in RELEASES:
        if not os.path.isfile(exe):
            all_text.append(f"=== {tag} ===\n[skipped: exe not found at {display_exe(exe)}]\n")
            summary.append((tag, "skipped (exe missing)"))
            continue
        scratch = os.path.join(HERE, "_scratch2_" + tag.replace(".", "_"))
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
