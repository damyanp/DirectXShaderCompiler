"""Does the successor compiler already answer #4520? Compiler Explorer probe.

The 2024-07-31 maintainer comment says DXC will not be fixed and that the fix is
planned for Clang, so "what does Clang do with this today" is a question the issue
itself raises. This probes CE's `hlsl_clang_trunk` directly rather than through
`triage.py godbolt`, because the answer decides whether a Clang pane belongs in the
published link at all: a pane full of errors about unimplemented HLSL says nothing
about this issue.

Three cases, and the last two are the controls SKILL.md step 7 requires before any
cross-compiler difference is believed:

  repro            the issue's shader, -fsyntax-only (the symptom is a front-end
                   diagnostic, and Clang's DXIL backend cannot lower SV_Target)
  workaround       same shader with the subscript hoisted into a SamplerState
                   local -- the form DXC accepts. If Clang rejects this too, its
                   rejection of the repro is about descriptor heaps generally,
                   not about the call under test
  trivial          a shader with no descriptor heaps at all, proving the pane
                   runs and the arguments are accepted

Usage (from the workspace root):
    python data/issues/4520/manual-case-clang-probe.py > \
           data/issues/4520/manual-case-clang-probe.txt
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

API = "https://godbolt.org/api/compiler/{}/compile"
COMPILERS = ("hlsl_clang_trunk", "dxc_trunk")
ARGS = "-T ps_6_6 -E main -fsyntax-only"
DXC_ARGS = "-T ps_6_6 -E main"

CASES = {
    "repro": """\
float4  main(uint texIdx: TIX, uint sampIdx : SIX, float2 coord: C) : SV_Target
{
    Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
    float4 result = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
    return result;
}
""",
    "workaround": """\
float4  main(uint texIdx: TIX, uint sampIdx : SIX, float2 coord: C) : SV_Target
{
    Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
    SamplerState mySampler = SamplerDescriptorHeap[sampIdx];
    float4 result = myTexture.Sample(mySampler, coord);
    return result;
}
""",
    "trivial": """\
Texture2D<float4> myTexture;
SamplerState mySampler;

float4  main(float2 coord: C) : SV_Target
{
    return myTexture.Sample(mySampler, coord);
}
""",
}


def compile_on(compiler, source, args):
    body = json.dumps({
        "source": source,
        "options": {
            "userArguments": args,
            "filters": {"execute": False, "intel": True, "demangle": True,
                        "commentOnly": False, "directives": True,
                        "labels": True, "libraryCode": False, "trim": False},
            "compilerOptions": {},
        },
        "lang": "hlsl",
        "allowStoreCodeDebug": True,
    }).encode()
    req = urllib.request.Request(
        API.format(compiler), data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def strip_ansi(text):
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def main():
    rows = []
    for compiler in COMPILERS:
        args = ARGS if compiler.startswith("hlsl_clang") else DXC_ARGS
        for name, source in CASES.items():
            res = compile_on(compiler, source, args)
            out = "\n".join(
                strip_ansi(x.get("text", ""))
                for x in (res.get("stderr") or []) + (res.get("stdout") or []))
            out = triage.redact_paths(out)
            print(f"\n=== {compiler}   case={name}   userArguments={args!r}")
            for ln in source.splitlines():
                print(f"    | {ln}")
            print(f"    exit={res.get('code')}")
            for ln in out.splitlines():
                print(f"    {ln}")
            rows.append((compiler, name, res.get("code"), out))

    print("\n\n=== summary\n")
    head = f"{'compiler':<20} {'case':<12} {'exit':<6} {'first diagnostic':<80}"
    print(head)
    print("-" * len(head))
    for compiler, name, code, out in rows:
        first = next((ln.strip() for ln in out.splitlines()
                      if "error" in ln.lower()), "(no error line)")
        print(f"{compiler:<20} {name:<12} {str(code):<6} {first[:80]:<80}")


if __name__ == "__main__":
    main()
