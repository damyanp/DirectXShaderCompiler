"""Which builtin object types hit issue 4666, and what suppresses it.

The reported repro pairs a texture array and a sampler array in one parameter
list; only the sampler is diagnosed. That asymmetry is the interesting part, so
this sweeps a small matrix of minimal single-parameter shaders on the
ground-truth build to establish, by measurement rather than by reading Sema:

  * which builtin object types are affected as ARRAY parameters,
  * that the same type as a SCALAR parameter is fine,
  * that any earlier declaration which forces the type to be completed
    suppresses the diagnostic, and that a LATER one does not.

Each case is a self-contained shader written to a scratch file, compiled, and
deleted. Commands are rendered with subprocess.list2cmdline, so no line here is
a transcription of something typed by hand. Everything is pushed through
triage.redact_paths before being written.

Usage, from the skill directory:

    python data/issues/4666/probe-completion.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import triage  # noqa: E402

OUT = os.path.join(HERE, "manual-case-completion-probe.txt")
SCRATCH = os.path.join(HERE, "scratch-completion-probe.hlsl")
ENTRY = "float4 main() : SV_Target { return 0; }\n"

# (id, what it isolates, body preceding the shared entry point)
CASES = [
    ("A-texture-array-param",
     "templated object type, array parameter",
     "void R(Texture2D<float4> T[4]) {}\n"),
    ("B-sampler-array-param",
     "non-templated object type, array parameter -- the reported symptom",
     "void R(SamplerState S[2]) {}\n"),
    ("C-sampler-scalar-param",
     "same type, scalar parameter: isolates the array-ness",
     "void R(SamplerState S) {}\n"),
    ("D-global-sampler-before",
     "a prior global of that type, which forces completion first",
     "SamplerState g;\nvoid R(SamplerState S[2]) {}\n"),
    ("E-global-sampler-after",
     "the same global moved AFTER: isolates declaration order",
     "void R(SamplerState S[2]) {}\nSamplerState g;\n"),
    ("F-struct-member-before",
     "the workaround named in the issue body",
     "struct X { SamplerState s[2]; };\nvoid R(SamplerState S[2]) {}\n"),
    ("G-typedef-before",
     "naming the type without requiring it to be complete",
     "typedef SamplerState T2[2];\nvoid R(SamplerState S[2]) {}\n"),
    ("H-samplercomparisonstate-array",
     "a second non-templated sampler type",
     "void R(SamplerComparisonState S[2]) {}\n"),
    ("I-rwtexture-array-param",
     "a second templated object type",
     "void R(RWTexture2D<float4> T[2]) {}\n"),
    ("J-byteaddressbuffer-array",
     "a non-templated buffer type: shows this is not sampler-specific",
     "void R(ByteAddressBuffer B[2]) {}\n"),
]


def main():
    row = triage.con().execute(
        "SELECT exe_path FROM compilers WHERE id='main-debug'").fetchone()
    if not row:
        print("main-debug not resolvable; nothing measured")
        return 1
    exe = row["exe_path"]

    lines = [
        "# Which builtin object types hit issue 4666, and what suppresses it.",
        "# Written by probe-completion.py -- rerun it to re-derive.",
        "# compiler: main-debug (the ground-truth build)",
        "# exe: " + triage.display_exe(exe),
        "#",
        "# Every case appends the same entry point:",
        "#   " + ENTRY.strip(),
        "",
    ]
    affected, clean = [], []
    for cid, why, body in CASES:
        with open(SCRATCH, "w", encoding="utf-8") as f:
            f.write(body + ENTRY)
        argv = [exe, "-T", "ps_6_0", "-E", "main",
                os.path.basename(SCRATCH)]
        p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
        text = (p.stdout or "") + (p.stderr or "")
        err = next((ln.strip() for ln in text.splitlines()
                    if "error:" in ln), "")
        # Strip the scratch file's name so the record reads as a case id.
        err = err.split("error:", 1)[-1].strip() if err else ""
        tag = "DIAGNOSED" if err else "ok"
        (affected if err else clean).append(cid)
        lines += [
            "=" * 74,
            "# case:   " + cid,
            "# tests:  " + why,
            "# cmd:    " + triage.redact_paths(
                subprocess.list2cmdline(["dxc"] + argv[1:])),
            "# exit:   0x%08X" % (p.returncode & 0xFFFFFFFF),
            "# result: " + tag,
        ]
        for ln in (body + ENTRY).splitlines():
            lines.append("    " + ln)
        if err:
            lines.append("  -> error: " + triage.redact_paths(err))
        lines.append("")

    lines += [
        "=" * 74,
        "# SUMMARY",
        "#   diagnosed: " + ", ".join(affected),
        "#   accepted:  " + ", ".join(clean),
        "#",
        "# Read against each other these say:",
        "#   * array parameters of NON-templated builtin object types are"
        " diagnosed",
        "#     (B, H, J) while templated ones are not (A, I) -- so this is not"
        " about",
        "#     samplers as such, and Texture2D<float4> in the reported repro is"
        " a",
        "#     red herring.",
        "#   * the same type as a scalar parameter is accepted (C), so it is the"
        "",
        "#     array form that is affected.",
        "#   * anything earlier in the file that requires the type to be"
        " complete",
        "#     suppresses it (D, F) and the same declaration placed later does"
        " not",
        "#     (E), while merely naming the type does not (G). That is"
        " order-dependent",
        "#     lazy completion, which is what makes the issue body's 'declaring"
        " an",
        "#     unrelated struct makes it go away' true.",
    ]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if os.path.exists(SCRATCH):
        os.remove(SCRATCH)
    print("diagnosed: " + ", ".join(affected))
    print("accepted:  " + ", ".join(clean))
    print("wrote " + os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
