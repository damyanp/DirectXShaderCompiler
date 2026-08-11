"""Per-release feature-presence matrix for issue 4520.

`triage.py bisect --linear` already scores the repro on every stable release
(out-<tag>.txt). What it cannot answer is whether a release that *reproduced*
was actually exercising SM 6.6 dynamic resources at the time, or merely running
`Sample` overload resolution over an argument it had failed to understand --
the repro declares `myTexture` explicitly as `Texture2D<float4>`, so both
symptom clauses can be produced by a build that has no descriptor heaps at all.
That ambiguity is the whole hazard of this issue, because the two releases
either side of the SM 6.6 line are exactly where a fake transition would sit.

So this holds the question fixed and varies the release, running on each
release's own dxc.exe:

  repro                repro.hlsl -- the spec's sample, the filed symptom
  feature-presence     control-workaround-local.hlsl -- the reporter's own
                       workaround. It uses BOTH ResourceDescriptorHeap and
                       SamplerDescriptorHeap and must COMPILE. A release where
                       this fails cannot answer anything about #4520, whatever
                       the repro did there. Exit 0 alone is not taken as proof
                       that the feature is real: the emitted DXIL must also
                       declare both descriptor-heap feature flags and lower the
                       subscripts through dx.op.createHandleFromHeap.
  standalone-fn        control-standalone-fn.hlsl -- the maintainer's
                       2024-07-31 case: the same subscript expression passed to
                       a user-defined function taking a SamplerState. This is
                       the test of "can an untyped descriptor-heap sampler be
                       resolved implicitly to a typed one at all".
  cast                 control-cast.hlsl -- the reporter's other workaround.

Usage (from the workspace root):
    python data/issues/4520/manual-case-release-history.py > \
           data/issues/4520/manual-case-release-history.txt
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

PROFILE = ["-T", "ps_6_6", "-E", "main"]
CASES = (
    ("repro", "repro.hlsl"),
    ("feature-presence", "control-workaround-local.hlsl"),
    ("standalone-fn", "control-standalone-fn.hlsl"),
    ("cast", "control-cast.hlsl"),
)
SHADERS = [src for _name, src in CASES]

SYMPTOM = "no matching member function for call to 'Sample'"
ARITY_NOTE = "requires 3 arguments, but 2 were provided"
HEAP_FLAGS = ("Resource descriptor heap indexing",
              "Sampler descriptor heap indexing")
HEAP_OP = "dx.op.createHandleFromHeap"
UNKNOWN = ("use of undeclared identifier", "unknown type name",
           "invalid profile", "unsupported profile")


def run(exe, work, argv):
    """Run one dxc command, echoing exactly what was executed."""
    p = subprocess.run([exe] + argv, cwd=work, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    text = triage.redact_paths((p.stdout or "") + (p.stderr or ""))
    print(f"    $ dxc {subprocess.list2cmdline(argv)}")
    first = [ln for ln in text.strip().splitlines() if ln.strip()]
    print(f"      exit={p.returncode}"
          + (f"  {first[0][:110]}" if first else "  (no output)"))
    return p.returncode, text


def measure(tag, exe):
    work = os.path.join(HERE, f"work-{tag}")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    for s in SHADERS:
        shutil.copy(os.path.join(HERE, s), work)

    print(f"\n=== {tag}   {triage.display_exe(exe)}")
    vrc, vtext = run(exe, work, ["--version"])
    row = {"tag": tag,
           "version": " ".join(vtext.split())[:80] if vrc == 0 else "n/a"}

    for name, src in CASES:
        rc, text = run(exe, work, PROFILE + [src])
        row[name + "_rc"] = rc
        row[name + "_ok"] = rc == 0
        row[name + "_unknown"] = next(
            (u for u in UNKNOWN if u in text), None)
        if name == "repro":
            row["symptom"] = SYMPTOM in text
            row["arity_note"] = ARITY_NOTE in text
        if name == "feature-presence":
            row["heap_flags"] = all(f in text for f in HEAP_FLAGS)
            row["heap_op"] = HEAP_OP in text

    shutil.rmtree(work, ignore_errors=True)
    return row


def main():
    tags = [r["tag"] for r in triage.con().execute(
        "SELECT tag FROM releases WHERE prerelease = 0 AND asset_name IS NOT"
        " NULL ORDER BY build_date")]
    rows = []
    for tag in tags:
        rows.append(measure(tag, triage.ensure_release(tag)))
    rows.append(measure("main-debug", triage.resolve_compiler("main-debug")))

    print("\n\n=== summary\n")
    print("symptom       = repro.hlsl printed "
          f"\"{SYMPTOM}\"")
    print("arity-note    = repro.hlsl printed "
          f"\"{ARITY_NOTE}\"")
    print("feature       = control-workaround-local.hlsl COMPILED (exit 0)")
    print("heap-dxil     = ...and its DXIL declares BOTH descriptor-heap")
    print("                feature flags and contains "
          f"{HEAP_OP}.")
    print("                feature+heap-dxil together mean this release really")
    print("                has SM 6.6 dynamic resources, so its repro result")
    print("                is evidence about #4520")
    print("standalone-fn = control-standalone-fn.hlsl COMPILED (exit 0)")
    print("cast          = control-cast.hlsl COMPILED (exit 0)")
    print("rejected-with = first feature-absence marker in the REPRO output,")
    print("                if any\n")
    head = (f"{'release':<16} {'symptom':<8} {'arity-note':<11} "
            f"{'feature':<8} {'heap-dxil':<10} {'standalone-fn':<14} "
            f"{'cast':<6} {'rejected-with':<26}")
    print(head)
    print("-" * len(head))
    for r in rows:
        heap_dxil = r["heap_flags"] and r["heap_op"]
        print(f"{r['tag']:<16} {str(r['symptom']):<8} "
              f"{str(r['arity_note']):<11} {str(r['feature-presence_ok']):<8} "
              f"{str(heap_dxil):<10} {str(r['standalone-fn_ok']):<14} "
              f"{str(r['cast_ok']):<6} {str(r['repro_unknown'] or '-'):<26}")

    usable = [r for r in rows
              if r["feature-presence_ok"] and r["heap_flags"] and r["heap_op"]]
    unusable = [r for r in rows if r not in usable]
    print(f"\nbuilds measured:            {len(rows)} "
          f"({len(tags)} stable releases + main-debug)")
    print(f"builds with the feature:    {len(usable)}  "
          + ", ".join(r["tag"] for r in usable))
    print("builds WITHOUT the feature: "
          + str(len(unusable)) + "  "
          + ", ".join(r["tag"] for r in unusable))
    print("symptom on a build that HAS the feature:      "
          f"{sum(1 for r in usable if r['symptom'])}/{len(usable)}")
    print("symptom on a build that LACKS the feature:    "
          f"{sum(1 for r in unusable if r['symptom'])}"
          f"/{len(unusable)}"
          "   <- these are NOT evidence about #4520")
    print("standalone-fn compiled on:  "
          f"{sum(1 for r in usable if r['standalone-fn_ok'])}/{len(usable)}"
          " builds that have the feature")
    print("cast workaround compiled on: "
          f"{sum(1 for r in usable if r['cast_ok'])}/{len(usable)}"
          " builds that have the feature")


if __name__ == "__main__":
    main()
