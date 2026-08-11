"""Control for the Compiler Explorer Clang pane on issue 4710.

`hlsl_clang_trunk` crashes on the repro inside
CGHLSLRuntime::emitBufferCopy. Per the skill's rule -- "a Clang error is not
evidence until you have a control" -- that crash means nothing until we know
whether Clang crashes on *any* struct-copy out of a constant buffer, resources
or not.

Three sources, same compiler, same arguments:

  A  the repro                        (struct with resources, dynamic index)
  B  same shape, NO resources         (plain struct array in a cbuffer)
  C  trivial pixel shader             (baseline: does the pane work at all?)

If B crashes too, the Clang pane is about cbuffer struct copies in general and
says nothing about this issue. If B compiles and A crashes, the crash tracks the
resource member.

Usage:  python probe-clang-control.py > manual-case-clang-control.txt
"""

import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))

import triage  # noqa: E402

COMPILER = "hlsl_clang_trunk"
ARGS = "-T ps_6_0 -E psMain"

A = open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8").read()

B = """// Control B: identical shape to the repro but with NO resource members.
struct PlainInfo
{
    float Scalar;
    float4 Values[4];
};

cbuffer cbPlain
{
    PlainInfo Plains[4];
};

float4 psMain() : SV_TARGET0
{
    float4 acc = float4( 0.0, 0.0, 0.0, 0.0 );

    [unroll]
    for( int i = 0; i < 4; ++i )
    {
        PlainInfo plain = Plains[ i ];
        acc += plain.Values[ i ] * plain.Scalar;
    }

    return acc;
}
"""

C = """// Control C: baseline. If this fails the pane is unusable for anything.
float4 psMain() : SV_TARGET0
{
    return float4( 0.0, 0.0, 0.0, 0.0 );
}
"""


def compile_on_ce(source):
    body = json.dumps({
        "source": source,
        "options": {
            "userArguments": ARGS,
            "filters": {"commentOnly": False, "trim": False},
            "compilerOptions": {"skipAsm": False},
        },
    }).encode()
    req = urllib.request.Request(
        f"https://godbolt.org/api/compiler/{COMPILER}/compile",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        j = json.load(r)
    text = "\n".join(x.get("text", "") for x in (j.get("stderr") or []) + (j.get("stdout") or []))
    return j.get("code"), triage.redact_paths(text)


def main():
    print("# issue 4710 -- control for the Compiler Explorer Clang pane")
    print("# generator: probe-clang-control.py (committed beside this file)")
    print(f"# compiler: {COMPILER}   args: {ARGS}")
    print("# Clang's HLSL support is incomplete, so a failure is only evidence")
    print("# if a closely-related shader that should be unaffected still compiles.")
    print()

    results = {}
    for label, src, expect in (
        ("A  repro (resources in cbuffer struct, dynamic index)", A, "subject"),
        ("B  same shape, no resources", B, "control, expected to compile"),
        ("C  trivial pixel shader", C, "control, expected to compile"),
    ):
        code, text = compile_on_ce(src)
        crashed = code not in (0,) and ("Stack dump" in text or "PLEASE submit a bug report" in text)
        frame = next((l.strip() for l in text.splitlines() if "emitBufferCopy" in l), "")
        results[label[0]] = (code, crashed)
        print(f"== {label}   [{expect}] ==")
        print(f"  exit={code}   clang crash: {crashed}")
        if frame:
            print(f"  crashing frame present: CGHLSLRuntime::emitBufferCopy")
        head = [l for l in text.splitlines() if l.strip()][:6]
        for l in head:
            print("    " + l)
        print()

    a_crash, b_crash, c_crash = (results[k][1] for k in "ABC")
    print("== verdict on this pane ==")
    if c_crash:
        print("  Control C failed: the Clang pane is unusable, ignore it entirely.")
    elif b_crash:
        print("  Control B crashed as well. Clang crashes on struct copies out of a")
        print("  constant buffer whether or not resources are involved, so the Clang")
        print("  pane says NOTHING about issue 4710 and must not be cited as though")
        print("  it corroborated the diagnostic. It is a separate Clang defect.")
    elif a_crash:
        print("  Control B compiled and A crashed: the crash tracks the resource member")
        print("  specifically. Worth reporting to the Clang HLSL front end as a distinct")
        print("  issue -- still not evidence about whether DXC's diagnostic is correct.")
    else:
        print("  Clang accepted the repro. That is a real datapoint for the design")
        print("  question: the new front end does not impose DXC's restriction.")


if __name__ == "__main__":
    main()
