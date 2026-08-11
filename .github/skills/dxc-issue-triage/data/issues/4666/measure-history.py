"""Per-release matrix for issue 4666.

Why this exists rather than a second `bisect`:

* `bisect` answers one question -- does `cmd.txt` reproduce `match.json` -- and
  it does that well for the primary DXIL symptom. What it cannot do is run a
  DIFFERENT shader on each release, and this issue needs exactly that twice
  over:

  1. The reported symptom IS a diagnostic. `classify`'s feature-absence markers
     do not include `variable has incomplete type`, so a release that never
     supported sampler-array parameters would emit its own error and score as a
     textbook reproduction with nothing anywhere saying so. The only defence is
     a positive control, run on EVERY probed release, proving the construct was
     supported there: `control-struct-first.hlsl` is byte-identical to
     `repro.hlsl` apart from an unreferenced struct declaration that the issue
     body says makes the error disappear.

  2. The issue's second symptom is a SPIR-V validation failure on a different
     shader with a different command line.

* Every command is printed with `subprocess.list2cmdline`, i.e. exactly what was
  executed, so no line in the output is a transcription.

Machine paths are pushed through `triage.redact_paths` before anything is
written.

Usage, from the skill directory:

    python data/issues/4666/measure-history.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import triage  # noqa: E402

OUT = os.path.join(HERE, "manual-case-release-matrix.txt")

# (label, argv-tail). The source file is always last, as dxc expects.
CASES = [
    ("repro-dxil", ["-T", "ps_6_0", "-E", "main", "repro.hlsl"]),
    ("ctl-struct-first",
     ["-T", "ps_6_0", "-E", "main", "control-struct-first.hlsl"]),
    ("ctl-global-sampler-array",
     ["-T", "ps_6_0", "-E", "main", "control-global-sampler-array.hlsl"]),
    ("ctl-texture-array-param",
     ["-T", "ps_6_0", "-E", "main", "control-texture-array-param.hlsl"]),
    ("ctl-no-sampler-array",
     ["-T", "ps_6_0", "-E", "main", "control-no-sampler-array.hlsl"]),
    ("repro-spirv-struct",
     ["-T", "ps_6_0", "-E", "main", "-spirv", "repro-spirv-struct.hlsl"]),
    ("repro-spirv-struct-Vd",
     ["-T", "ps_6_0", "-E", "main", "-spirv", "-Vd",
      "repro-spirv-struct.hlsl"]),
    ("ctl-spirv-struct-inlined",
     ["-T", "ps_6_0", "-E", "main", "-spirv",
      "control-spirv-struct-inlined.hlsl"]),
    ("ctl-spirv-noinline-plain",
     ["-T", "ps_6_0", "-E", "main", "-spirv",
      "control-spirv-noinline-plain.hlsl"]),
    ("ctl-spirv-noinline-plain-Vd",
     ["-T", "ps_6_0", "-E", "main", "-spirv", "-Vd",
      "control-spirv-noinline-plain.hlsl"]),
    ("ctl-spirv-hello",
     ["-T", "ps_6_0", "-E", "main", "-spirv", "control-spirv-hello.hlsl"]),
]

# The two diagnostics the issue is about, quoted from the issue body. Wording
# drifted under us and the matrix has to see through that: the SPIR-V validator
# says "must not contain an opaque type" up to v1.8.2505.1 and "must not
# contain an invalid opaque type" from v1.9.2602 on, which is a SPIRV-Tools
# change, not a DXC one.
SYMPTOM_A = "variable has incomplete type 'SamplerState [2]'"
SYMPTOM_B_PARTS = ("OpTypeStruct must not contain an", "opaque type")

# Symptom B has TWO separable halves, and conflating them mis-dates the defect.
# The validator's complaint is the reported symptom; DXC emitting a struct type
# with a sampler-array member is the defect. `-Vd` skips validation, so it shows
# what DXC produced regardless of which SPIRV-Tools that release bundled.
# Measured: v1.6.2104 emits `%Test = OpTypeStruct %_arr_type_sampler_uint_2` --
# byte-identical to the operand the reporter quotes -- and compiles clean,
# because its validator predates VUID-StandaloneSpirv-None-04667. Reading that
# as "the shader worked here" would invent a fix boundary out of a SPIRV-Tools
# upgrade.
BAD_IR = "OpTypeStruct %_arr_type_sampler"

# ...and the materialisation self-test. The struct type only reaches codegen if
# the release honours [noinline]; v1.5.2010 does not, inlines the helper, and
# emits no OpTypeStruct at all -- so its clean result measures nothing about
# opaque members. A control that only asked "did it compile" would have passed
# there and quietly licensed a wrong history. This requires the control to prove
# it produced the very construct under test.
MATERIALISED = "%Test = OpTypeStruct"


def classify_line(label, out, rc):
    if label.startswith("repro-dxil"):
        return "SYMPTOM-A" if SYMPTOM_A in out else (
            "ok" if rc == 0 else "OTHER-FAILURE")
    if label == "repro-spirv-struct-Vd":
        if BAD_IR in out:
            return "BAD-IR-EMITTED"
        return "no-bad-ir" if rc == 0 else "OTHER-FAILURE"
    if label.startswith("repro-spirv"):
        hit = all(p in out for p in SYMPTOM_B_PARTS)
        return "SYMPTOM-B" if hit else ("ok" if rc == 0 else "OTHER-FAILURE")
    if label == "ctl-spirv-noinline-plain-Vd":
        if rc != 0:
            return "CONTROL-FAILED"
        return "ok" if MATERIALISED in out else "CONTROL-NOT-MATERIALISED"
    return "ok" if rc == 0 else "CONTROL-FAILED"


def first_diag(out):
    for line in out.splitlines():
        s = line.strip()
        if s and not s.startswith(";") and "note: please file a bug" not in s:
            return s
    return ""


def releases():
    rows = triage.con().execute(
        "SELECT tag, cached_path, prerelease, asset_name FROM releases"
        " ORDER BY rowid").fetchall()
    out = []
    for r in rows:
        if not r["cached_path"] or r["prerelease"]:
            continue
        out.append((r["tag"], r["cached_path"]))
    return out


def main():
    lines = []
    w = lines.append
    w("Issue 4666 -- per-release matrix.")
    w("")
    w("Generated by measure-history.py, which is committed beside this file.")
    w("Every '$' line is subprocess.list2cmdline(argv) for the process that was")
    w("actually launched, not a transcription. cwd is the issue directory.")
    w("")
    w("Columns: <case> <status> exit=<hex> | first diagnostic line")
    w("")
    w("A release is valid evidence about symptom A only if ctl-struct-first is")
    w("'ok' on it: that control is repro.hlsl plus an unreferenced")
    w("'struct Resources { SamplerState Samplers[2]; };'. If both fail, the")
    w("release does not support sampler-array parameters in any form and its")
    w("error is not the reported defect. Likewise ctl-spirv-noinline-plain-Vd")
    w("gates symptom B: it must not merely compile, it must show")
    w("'%Test = OpTypeStruct', proving the release materialises the struct type")
    w("at all.")
    w("")

    targets = [("main-debug",
                triage.con().execute(
                    "SELECT exe_path FROM compilers WHERE id='main-debug'"
                ).fetchone()["exe_path"])] + releases()

    counts = {}
    selftest_seen = {"a": 0, "b": 0, "badir": 0, "ctl_fail": 0}
    for tag, exe in targets:
        w("=" * 78)
        ver = subprocess.run([exe, "--version"], capture_output=True, text=True,
                             cwd=HERE)
        w(f"release: {tag}")
        w(f"exe: {triage.display_exe(exe)}")
        w(f"--version: {(ver.stdout + ver.stderr).strip() or '(no output)'}")
        w("")
        for label, tail in CASES:
            argv = [exe] + tail
            p = subprocess.run(argv, capture_output=True, text=True, cwd=HERE,
                               timeout=300)
            out = (p.stdout or "") + (p.stderr or "")
            rc = p.returncode & 0xFFFFFFFF
            status = classify_line(label, out, p.returncode)
            counts[status] = counts.get(status, 0) + 1
            if status == "SYMPTOM-A":
                selftest_seen["a"] += 1
            if status == "SYMPTOM-B":
                selftest_seen["b"] += 1
            if status == "BAD-IR-EMITTED":
                selftest_seen["badir"] += 1
            if status.startswith("CONTROL-"):
                selftest_seen["ctl_fail"] += 1
            printable = subprocess.list2cmdline(
                [triage.display_exe(exe)] + tail)
            w(f"$ {printable}")
            w(f"  {label:28s} {status:24s} exit=0x{rc:08X} | {first_diag(out)}")
        w("")

    w("=" * 78)
    w("SELF-TEST")
    w("")
    w("The matrix reads its own output, so it has to be able to say 'nothing")
    w("matched' distinctly from 'nothing to match'. These counters make a")
    w("broken reader loud instead of quietly clean:")
    w("")
    for k in sorted(counts):
        w(f"  {k:26s} {counts[k]}")
    w("")
    w(f"  symptom-A detector fired on {selftest_seen['a']} release(s)")
    w(f"  symptom-B detector fired on {selftest_seen['b']} release(s)")
    w(f"  bad-IR detector fired on {selftest_seen['badir']} release(s)")
    w(f"  control failures / non-materialisations: {selftest_seen['ctl_fail']}")
    w("")
    if not selftest_seen["a"]:
        w("  MATRIX-4666: PARSE-WARNING: symptom-A detector never fired. Either")
        w("  no release reproduces, or the quoted diagnostic changed wording.")
    if not selftest_seen["b"]:
        w("  MATRIX-4666: PARSE-WARNING: symptom-B detector never fired. Either")
        w("  no release reproduces, or the validator changed wording.")
    if not selftest_seen["badir"]:
        w("  MATRIX-4666: PARSE-WARNING: bad-IR detector never fired, so the")
        w("  -Vd arm proves nothing about what DXC emitted.")

    text = triage.redact_paths("\n".join(lines) + "\n")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {os.path.basename(OUT)}: " +
          ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
