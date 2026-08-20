"""Per-release history matrix for DXC issue #5268.

Generates `manual-case-release-history.txt`: for every catalogued stable
release that has a usable local `dxr.exe` (cached under
`.cache/rw4273/<tag>/dxr.exe`, one directory per stable release from
v1.4.1907 through v1.9.2607) and a catalogued `dxc.exe`
(`triage.py`'s `releases.cached_path`), runs the release's OWN dxr.exe on the
issue's repro with the exact reported arguments, then recompiles the
rewritten output with that SAME release's OWN dxc.exe. Both binaries are
release-paired deliberately: dxr.exe is not shipped in the downloadable
release zips (only dxc.exe/dxcompiler.dll/dxil.dll/dxv.exe are), so pairing a
stable release's dxr.exe with a DIFFERENT release's dxc.exe would not be
testing "did this release have the bug", the way `triage.py bisect` pairs a
single command against one release's own dxc.exe.

This does not go through `triage.py bisect`: that command hard-errors on a
harness-registered compiler (SKILL.md's "refuse_harness_bisect"), because it
would substitute each release's dxc.exe for the *harness itself*, not for the
dxr.exe the harness wraps -- exactly the #2918/#2922/#2923 trap. This script
is the sanctioned manual release-matrix replacement for that case.

Every attempt is captured verbatim (command, exit code, output) so the
history claim is reproducible from this file, not from memory.
"""
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DXR_CACHE = os.path.join(SKILL_ROOT, ".cache", "rw4273")

sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
import triage  # noqa: E402

REPRO_ARGS = ["-E", "VSMain", "-remove-unused-globals", "repro.hlsl"]
RECOMPILE_PROFILE = "vs_6_0"


def classify(rc):
    if rc is None:
        return "timeout"
    code = rc & 0xFFFFFFFF
    if code == 0:
        return "success"
    if triage.is_internal_failure("", rc, False):
        return "internal-failure"
    if code == 0x80004005:
        return "diagnosed-error"
    return "other:0x%08X" % code


def run(argv, cwd):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    con = triage.con()
    rows = con.execute(
        "SELECT tag, cached_path FROM releases WHERE cached_path IS NOT NULL "
        "ORDER BY build_date").fetchall()

    lines = []
    matrix = []
    for tag, dxc_path in rows:
        dxr_path = os.path.join(DXR_CACHE, tag, "dxr.exe")
        if not os.path.isfile(dxr_path):
            lines.append(f"=== {tag}: no cached dxr.exe, skipped ===\n")
            matrix.append((tag, "no-dxr", "-"))
            continue
        if not os.path.isfile(dxc_path):
            lines.append(f"=== {tag}: cached_path does not exist, skipped ===\n")
            matrix.append((tag, "no-dxc", "-"))
            continue

        lines.append(f"=== {tag} ===")
        rw_argv = [dxr_path] + REPRO_ARGS
        lines.append("$ " + subprocess.list2cmdline(rw_argv))
        rw_rc, rw_out = run(rw_argv, SCRIPT_DIR)
        lines.append(f"# dxr exit-hex: 0x{rw_rc & 0xFFFFFFFF:08X}"
                      if rw_rc is not None else "# dxr exit: None")
        lines.append(rw_out.rstrip())

        if rw_rc != 0:
            lines.append("# dxr itself failed -- invalid-probe "
                          "(this release cannot express -remove-unused-globals "
                          "on this input)")
            matrix.append((tag, "invalid-probe", rw_out.strip().splitlines()[0]
                            if rw_out.strip() else "(no output)"))
            lines.append("")
            continue

        rewritten_path = os.path.join(SCRIPT_DIR, f"manual-rewritten-{tag}.hlsl")
        with open(rewritten_path, "w") as f:
            f.write(rw_out)

        rc_argv = [dxc_path, "-T", RECOMPILE_PROFILE, "-E", "VSMain",
                   os.path.basename(rewritten_path)]
        lines.append("$ " + subprocess.list2cmdline(rc_argv))
        rc_rc, rc_out = run(rc_argv, SCRIPT_DIR)
        label = classify(rc_rc)
        lines.append(f"# dxc (recompile) exit-hex: 0x{rc_rc & 0xFFFFFFFF:08X}"
                      if rc_rc is not None else "# dxc (recompile) exit: None")
        lines.append(f"# dxc (recompile) classification: {label}")
        # Keep only the first diagnostic line in the matrix row; the full
        # text is above.
        first_out_line = rc_out.strip().splitlines()[0] if rc_out.strip() else ""
        lines.append(rc_out.rstrip())
        lines.append("")
        os.remove(rewritten_path)

        verdict = ("repro" if label == "diagnosed-error"
                   and "POINT_SIZE'" in rc_out else "no-repro")
        matrix.append((tag, verdict, first_out_line))

    lines.append("=== summary ===")
    for tag, verdict, note in matrix:
        lines.append(f"{tag:14s} {verdict:14s} {note}")

    out_path = os.path.join(SCRIPT_DIR, "manual-case-release-history.txt")
    text = triage.redact_paths("\n".join(lines) + "\n")
    with open(out_path, "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
