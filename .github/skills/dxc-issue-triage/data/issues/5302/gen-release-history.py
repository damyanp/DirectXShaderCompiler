"""Per-release feature-presence matrix for issue #5302.

`triage.py bisect` reports `always-repro'd across v1.4.1907..v1.9.2607`, but this is
misleading: v1.4.1907 (2019-07-15) predates PR #2795 ("Conditionalize breaks to keep them in
loops", d3af7f123, 2020-03-30) entirely, so the `dx.break` mechanism does not exist yet for
ANY shader stage there -- not just VS. `match.json`'s `not_contains dx.break` clause is
satisfied at that release for a reason unrelated to the reported VS-vs-PS divergence, and
`bisect`'s generic `invalid-probe` classifier (built for rejected profiles/intrinsics) does not
catch it, because the compile itself succeeds.

This script runs the repro's VS command (-T vs_6_0 ... /DOUTPUT=Z) and the reporter's PS
command (-T ps_6_0 ... /DOUTPUT=SV_Target) against every cataloged stable release's OWN
dxc.exe (via `triage.ensure_release`), plus main-debug, and records whether `dx.break`
appears in each output. That distinguishes releases that predate the mechanism entirely
(neither VS nor PS shows it) from releases where PS/CS/Lib are protected but VS never is
(the reported bug).

Usage (from the workspace root):
    python data/issues/5302/gen-release-history.py > \
           data/issues/5302/manual-case-release-history.txt
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402


def run(exe, args):
    argv = [exe] + args
    proc = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    cmd = "dxc " + subprocess.list2cmdline(args)
    return cmd, proc.returncode, proc.stdout + proc.stderr


def classify(text, exit_code):
    if "dx.break" in text:
        return "dx.break PRESENT"
    if "storeOutput" in text and exit_code == 0:
        return "dx.break absent (compiled clean)"
    first_line = text.strip().splitlines()[0] if text.strip() else "(no output)"
    return f"COMPILE FAILED (invalid-probe): {first_line}"


def measure(tag, exe):
    lines = [f"=== {tag}   {triage.display_exe(exe)}"]
    vs_cmd, vs_exit, vs_out = run(exe, ["-T", "vs_6_0", "-E", "main", "-DOUTPUT=Z",
                                        "repro.hlsl"])
    ps_cmd, ps_exit, ps_out = run(exe, ["-T", "ps_6_0", "-E", "main", "-DOUTPUT=SV_Target",
                                        "repro.hlsl"])
    lines.append(f"$ {vs_cmd}")
    lines.append(f"  exit={vs_exit}  {classify(vs_out, vs_exit)}")
    lines.append(f"$ {ps_cmd}")
    lines.append(f"  exit={ps_exit}  {classify(ps_out, ps_exit)}")
    lines.append("")
    return "\n".join(lines)


def main():
    con = triage.con()
    tags = [r["tag"] for r in con.execute(
        "SELECT tag FROM releases WHERE prerelease = 0 AND asset_name IS NOT NULL"
        " ORDER BY build_date")]
    out_lines = []
    for tag in tags:
        out_lines.append(measure(tag, triage.ensure_release(tag)))
    out_lines.append(measure("main-debug", triage.resolve_compiler("main-debug")))
    out = "\n".join(out_lines)
    print(out)
    with open(os.path.join(HERE, "manual-case-release-history.txt"), "w",
              encoding="utf-8") as f:
        f.write(out)


if __name__ == "__main__":
    main()
