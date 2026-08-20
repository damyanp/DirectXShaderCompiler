"""Capture the linked module's disassembly with validation disabled (-Vd).

Run manually (not through `triage.py run`) because this asks a different
question than the primary predicate: not "does it validate" but "what does
the linker actually produce" -- specifically, whether the linked module's
`target datalayout` line survives linking. `subprocess.list2cmdline` prints
exactly what ran, and paths are redacted to <repo> before being written so no
machine layout lands in the committed capture (see #3429's method-notes on
redaction -- keep the path resolution real, only the *printed* text is
redacted).

Usage: python capture-vd-disasm.py
Writes: manual-case-linked-vd-disasm.txt
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
EXE = os.path.join(REPO, "build", "Debug", "bin", "dxc.exe")


def redact(text):
    return text.replace(REPO.replace("\\", "\\\\"), "<repo>").replace(REPO, "<repo>")


def run(argv):
    p = subprocess.run(argv, capture_output=True, text=True, cwd=HERE)
    return p.returncode, p.stdout, p.stderr


def main():
    out_path = os.path.join(HERE, "manual-case-linked-vd-disasm.txt")
    lines = []
    for argv in (
        [EXE, "-T", "lib_6_x", "-Fo", "as.lib", "repro.hlsl"],
        [EXE, "-T", "as_6_6", "-link", "as.lib", "-Vd"],
    ):
        rc, out, err = run(argv)
        lines.append(f"$ {redact(subprocess.list2cmdline(argv))}")
        lines.append(f"[exit] {rc}")
        lines.append("--- stdout ---")
        lines.append(redact(out))
        lines.append("--- stderr ---")
        lines.append(redact(err))
        lines.append("")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    os.remove(os.path.join(HERE, "as.lib"))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
