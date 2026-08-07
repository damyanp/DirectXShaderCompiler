"""#3695: search for a smaller shader that still crashes.

The reporter's stated hypothesis is that the crash is about "assigning one
RWTexture2D<float4> global variable to another". Two hand-written minimisations
(minimal-assign.hlsl, minimal-return.hlsl) are *diagnosed* rather than crashing,
so that description is not sufficient on its own. This walks a small ladder of
candidates towards the original to find what is.

Each candidate is written to a scratch file, compiled with the issue's own
arguments, and its exit status recorded. Every command is echoed with
subprocess.list2cmdline(argv) -- what was executed, not a transcription.

Writes manual-case-minimisation.txt.  Usage:  python minimise.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# .../<repo>/.github/skills/dxc-issue-triage/data/issues/3695 -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *[os.pardir] * 6))
DXC = os.environ.get(
    "DXC_TRIAGE_DXC",
    os.path.join(REPO, "build", "Debug", "bin", "dxc.exe"))
ARGS = ["-T", "cs_6_0", "-E", "main"]
SCRATCH = os.path.join(HERE, "scratch-minimise.hlsl")

HEAD = """RWTexture2D<float4> A;
RWTexture2D<float4> B;
"""

CANDIDATES = [
    ("C1 global-to-global assignment only", HEAD + """
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  A = B;
  A[id.xy] = 1.0;
}
"""),
    ("C2 function returns a resource; local; assign to other global", HEAD + """
RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0,0)] = 1.0;
  return tex;
}
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(B);
  A = local;
}
"""),
    ("C3 as C2 but the argument is the SAME global that is assigned", HEAD + """
RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0,0)] = 1.0;
  return tex;
}
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A);
  A = local;
}
"""),
    ("C4 as C3 plus a use of A before the call (GetDimensions)", HEAD + """
RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0,0)] = 1.0;
  return tex;
}
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  float x, y;
  A.GetDimensions(x, y);
  RWTexture2D<float4> local = pick(A);
  A = local;
}
"""),
    ("C5 as C3 plus a store through the OTHER global after the call", HEAD + """
RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0,0)] = 1.0;
  return tex;
}
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A);
  B[id.xy] = 1.0;
  A = local;
}
"""),
    ("C6 as C3 but the callee also READS through the parameter", HEAD + """
RWTexture2D<float4> pick(RWTexture2D<float4> tex, uint2 uv) {
  float4 c = tex[uv];
  tex[uv] = c + 1.0;
  return tex;
}
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A, id.xy);
  A = local;
}
"""),
    ("C7 as C6 plus a store through the OTHER global after the call", HEAD + """
RWTexture2D<float4> pick(RWTexture2D<float4> tex, uint2 uv) {
  float4 c = tex[uv];
  tex[uv] = c + 1.0;
  return tex;
}
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A, id.xy);
  B[id.xy] = 1.0;
  A = local;
}
"""),
    ("C8 C3 with a loop in the callee, as in the original", HEAD + """
float k;
RWTexture2D<float4> pick(RWTexture2D<float4> tex, uint2 uv) {
  float4 c = tex[uv];
  for (float i = 0; i < 6.28; i += k)
    c.r += tex[uv + uint2(i, i)].r;
  tex[uv] = c;
  return tex;
}
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A, id.xy);
  A = local;
}
"""),
]


def run(src):
    with open(SCRATCH, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    argv = [DXC] + ARGS + [os.path.basename(SCRATCH)]
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                       timeout=300)
    return argv, p


def main():
    out = ["# #3695 minimisation ladder",
           "# dxc: " + DXC,
           "# each candidate is written to scratch-minimise.hlsl and compiled",
           "# 0xE0000001 = assert (crash), 0x80004005 = E_FAIL, an ordinary",
           "# diagnosed error -- NOT a crash",
           ""]
    verdicts = []
    for title, src in CANDIDATES:
        argv, p = run(src)
        code = p.returncode & 0xFFFFFFFF
        crashed = code in (0xE0000001, 0xC0000005, 0x80000003,
                           0xE0000002, 0xE0000003)
        verdicts.append((title, code, crashed))
        out.append("=" * 74)
        out.append(title)
        out.append("=" * 74)
        out.append("$ " + subprocess.list2cmdline(argv))
        out.append("--- source ---")
        out.append(src.rstrip())
        out.append("--- exit ---")
        out.append("0x%08X  %s" % (code, "CRASH" if crashed else "not a crash"))
        out.append("--- stdout (first 5 lines) ---")
        out.append("\n".join(p.stdout.splitlines()[:5]))
        out.append("--- stderr ---")
        out.append(p.stderr.rstrip())
        out.append("")

    out.append("=" * 74)
    out.append("SUMMARY")
    out.append("=" * 74)
    for title, code, crashed in verdicts:
        out.append("%-8s 0x%08X  %s" %
                   (title.split()[0], code, "CRASH" if crashed else "diagnosed/ok"))
    out.append("")

    if os.path.exists(SCRATCH):
        os.remove(SCRATCH)

    path = os.path.join(HERE, "manual-case-minimisation.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    sys.stdout.write("wrote %s\n" % path)
    for title, code, crashed in verdicts:
        sys.stdout.write("  %-60s 0x%08X %s\n" %
                         (title, code, "CRASH" if crashed else ""))


if __name__ == "__main__":
    main()
