"""How wide is #4520? Ground-truth-only probe of the sampler-taking intrinsic methods.

The issue is filed against `Texture2D::Sample`. Nothing in the report says whether
that is the only affected call, and the answer changes what a fix has to cover, so
each case below is measured rather than reasoned about.

Every case is a two-line pixel shader differing in exactly one way, and each is run
twice: once passing `SamplerDescriptorHeap[i]` (or `SamplerDescriptorHeap[i]` for a
comparison sampler) straight into the intrinsic method, and once through the
reporter's workaround of assigning it to a local of the declared sampler type first.
The workaround arm is the per-case control: if it does not compile, the case says
nothing about #4520.

Sources are embedded here rather than written as `.hlsl` files so that the issue
directory keeps exactly the four controls that back `match.json`.

Usage (from the workspace root):
    python data/issues/4520/manual-case-intrinsic-scope.py > \
           data/issues/4520/manual-case-intrinsic-scope.txt
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

PROFILE = ["-T", "ps_6_6", "-E", "main"]

PREAMBLE = """\
float4 main(uint texIdx : TIX, uint sampIdx : SIX, float2 coord : C) : SV_Target
{
    Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
"""

# name -> (call written with the heap subscript inline,
#          same call with the subscript hoisted into a local of the declared
#          sampler type -- the reporter's workaround, and this case's control)
CASES = {
    "Sample": (
        "return myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);",
        "SamplerState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.Sample(s, coord);"),
    "SampleLevel": (
        "return myTexture.SampleLevel(SamplerDescriptorHeap[sampIdx], coord, 0);",
        "SamplerState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.SampleLevel(s, coord, 0);"),
    "SampleBias": (
        "return myTexture.SampleBias(SamplerDescriptorHeap[sampIdx], coord, 0);",
        "SamplerState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.SampleBias(s, coord, 0);"),
    "SampleGrad": (
        "return myTexture.SampleGrad(SamplerDescriptorHeap[sampIdx], coord, "
        "coord, coord);",
        "SamplerState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.SampleGrad(s, coord, coord, coord);"),
    "SampleCmp": (
        "return myTexture.SampleCmp(SamplerDescriptorHeap[sampIdx], coord, 0.5);",
        "SamplerComparisonState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.SampleCmp(s, coord, 0.5);"),
    "SampleCmpLevelZero": (
        "return myTexture.SampleCmpLevelZero(SamplerDescriptorHeap[sampIdx], "
        "coord, 0.5);",
        "SamplerComparisonState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.SampleCmpLevelZero(s, coord, 0.5);"),
    "GatherRed": (
        "return myTexture.GatherRed(SamplerDescriptorHeap[sampIdx], coord);",
        "SamplerState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.GatherRed(s, coord);"),
    "CalculateLevelOfDetail": (
        "return myTexture.CalculateLevelOfDetail("
        "SamplerDescriptorHeap[sampIdx], coord);",
        "SamplerState s = SamplerDescriptorHeap[sampIdx];\n"
        "    return myTexture.CalculateLevelOfDetail(s, coord);"),
}

SYMPTOM = "no matching member function for call to"


def source(body):
    return PREAMBLE + "    " + body + "\n}\n"


def run(exe, work, name, body):
    path = os.path.join(work, name + ".hlsl")
    with open(path, "w", encoding="utf-8") as f:
        f.write(source(body))
    argv = PROFILE + [name + ".hlsl"]
    p = subprocess.run([exe] + argv, cwd=work, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    text = triage.redact_paths((p.stdout or "") + (p.stderr or ""))
    print(f"    $ dxc {subprocess.list2cmdline(argv)}")
    for ln in source(body).splitlines():
        print(f"      | {ln}")
    errs = [ln for ln in text.splitlines() if ": error:" in ln]
    print(f"      exit={p.returncode}"
          + (f"  {errs[0].strip()[:120]}" if errs else "  (compiled)"))
    return p.returncode, text


def main():
    exe = triage.resolve_compiler("main-debug")
    work = tempfile.mkdtemp(prefix="scope4520-", dir=HERE)
    print(f"compiler: {triage.display_exe(exe)}")
    p = subprocess.run([exe, "--version"], capture_output=True, text=True)
    print(f"version:  {' '.join((p.stdout or p.stderr).split())}")
    print(f"profile:  {subprocess.list2cmdline(PROFILE)}\n")

    rows = []
    try:
        for name, (inline, hoisted) in CASES.items():
            print(f"\n=== {name}: heap subscript passed inline")
            irc, itext = run(exe, work, name + "-inline", inline)
            print(f"\n=== {name}: hoisted into a local first (control)")
            hrc, htext = run(exe, work, name + "-hoisted", hoisted)
            rows.append((name, irc, SYMPTOM in itext, hrc))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("\n\n=== summary\n")
    head = (f"{'intrinsic method':<24} {'inline exit':<12} "
            f"{'no-matching-member':<19} {'hoisted (control) exit':<22}")
    print(head)
    print("-" * len(head))
    for name, irc, sym, hrc in rows:
        print(f"{name:<24} {irc:<12} {str(sym):<19} {hrc:<22}")

    controls_ok = [r for r in rows if r[3] == 0]
    print(f"\ncases measured:                       {len(rows)}")
    print(f"control (hoisted) compiled:           {len(controls_ok)}/{len(rows)}")
    print("inline heap subscript rejected with "
          f"\"{SYMPTOM} ...\": "
          f"{sum(1 for r in controls_ok if r[2])}/{len(controls_ok)}")
    print("inline heap subscript compiled:       "
          f"{sum(1 for r in controls_ok if r[1] == 0)}/{len(controls_ok)}")


if __name__ == "__main__":
    main()
