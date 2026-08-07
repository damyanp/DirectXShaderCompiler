"""Compiler Explorer controls for issue 3811's Clang pane.

The published link shows `hlsl_clang_trunk` compiling the loop repro with no
uninitialised-value diagnostic. SKILL.md step 7: "A Clang error is not evidence
until you have a control" -- and the mirror, a Clang *silence*, needs one too.
Silence has two innocent explanations, so this asks both questions:

  straightline  the same uninitialised read written straight-line. DXC rejects
                this at DXIL validation. If Clang is silent here as well, the
                honest finding is "Clang has no uninitialised-out-parameter
                diagnostic at all", not "Clang misses the loop case".
  initialized   correct code. Proves the pane is not simply broken and that a
                clean result is capable of being produced.

Every command is echoed into the capture, so the file can be re-derived rather
than trusted. Paths come from __file__; there are no machine-specific paths.

    python ce-clang-control.py          # writes manual-case-clang-control.txt
"""
import json
import os
import urllib.request

CE = "https://godbolt.org"
COMPILER = "hlsl_clang_trunk"
ARGS = "-T cs_6_0"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "manual-case-clang-control.txt")

CASES = [
    ("repro-loop", "variant-compute.hlsl", None),
    ("straightline", "variant-compute.hlsl",
     ("\t\t\tresult += values[i];", "\tresult += values[0];")),
    ("initialized", "variant-compute.hlsl",
     ("void Accumulate(int count, out float result)\n{",
      "void Accumulate(int count, out float result)\n{\n\tresult = 0.0;")),
]


def body(name, src):
    """Derive one case's source from variant-compute.hlsl."""
    text = open(os.path.join(HERE, src), encoding="utf-8").read()
    if name == "straightline":
        # Drop the loop entirely, leaving one unconditional accumulation.
        text = text.replace(
            "\tfor (int i = 0; i < count; i++)\n"
            "\t\tresult += values[i];  // <-- loop spelling: accepted\n",
            "\tresult += values[0];  // <-- straight-line spelling\n")
    elif name == "initialized":
        text = text.replace("void Accumulate(int count, out float result)\n{\n",
                            "void Accumulate(int count, out float result)\n{\n"
                            "\tresult = 0.0;\n")
    return text


def compile_ce(source):
    payload = {
        "source": source, "lang": "hlsl", "compiler": COMPILER,
        "options": {
            "userArguments": ARGS,
            "compilerOptions": {"skipAsm": False, "executorRequest": False},
            "filters": {"binary": False, "commentOnly": False,
                        "demangle": True, "directives": False,
                        "execute": False, "intel": True, "labels": True,
                        "libraryCode": False, "trim": False},
            "tools": [], "libraries": [],
        },
        "allowStoreCodeDebug": True,
    }
    req = urllib.request.Request(
        f"{CE}/api/compiler/{COMPILER}/compile",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.load(r)
    text = "\n".join(x.get("text", "") for stream in ("stdout", "stderr")
                     for x in res.get(stream, []))
    asm = "\n".join(x.get("text", "") for x in res.get("asm", [])
                    if isinstance(x, dict))
    return res.get("code"), text, asm


def main_body(asm):
    """Extract `define void @main()` ... `}` so the capture carries the IR the
    counts above were derived from, rather than asking a reader to trust them."""
    out, inside = [], False
    for ln in asm.splitlines():
        if ln.startswith("define ") and "@main(" in ln:
            inside = True
        if inside:
            out.append(ln)
            if ln.strip() == "}":
                break
    return out


def main():
    lines = [
        "# Compiler Explorer controls for #3811's Clang pane.",
        f"# Written by {os.path.basename(__file__)} -- rerun it to re-derive.",
        f"# compiler: {COMPILER}   args: {ARGS}",
        "# CE runs Linux Release builds; it corroborates the local Debug",
        "# build and never overrules it.",
        "",
    ]
    for name, src, _ in CASES:
        source = body(name, src)
        rc, text, asm = compile_ce(source)
        diag = [ln for ln in text.splitlines()
                if ("error" in ln or "warning" in ln)
                and "-Wunused-command-line-argument" not in ln]
        phi = [ln.strip() for ln in asm.splitlines()
               if "phi" in ln and "float" in ln and "undef" in ln]
        mainir = main_body(asm)
        # Self-consistency: a reader must be able to tell "nothing matched"
        # from "nothing was read". SKILL.md: a harness that can return both
        # through the same channel will eventually be believed.
        lines += [
            "=" * 74,
            f"# case: {name}   (derived from {src})",
            f"# POST {CE}/api/compiler/{COMPILER}/compile",
            f"# exit: {rc}",
            f"# asm lines read: {len(asm.splitlines())}"
            + ("   PARSE-WARNING: no asm returned"
               if not asm.strip() else ""),
            f"# main() body lines extracted: {len(mainir)}"
            + ("   PARSE-WARNING: define void @main() not found"
               if not mainir else ""),
            f"# diagnostics (excluding CE's own -Qembed_debug note): "
            f"{len(diag)}",
            *([f"    {ln}" for ln in diag] or ["    (none)"]),
            f"# undef-seeded float phi nodes: {len(phi)}",
            *([f"    {ln}" for ln in phi] or ["    (none)"]),
            "",
            "--- source ---",
            source.rstrip(),
            "",
            "--- full compiler output ---",
            text.rstrip(),
            "",
            "--- define void @main() ---",
            *(mainir or ["(not found)"]),
            "",
        ]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
