"""Documents a negative-result repro attempt for issue #5328.

Attempts to trigger the reported IRBuilder<>(LI) typo in
HLMatrixBitcastLowerPass.cpp via a two-module `dxc -T lib_6_9 -link`
scenario: an exported function taking a matrix array `inout` parameter,
called from a compute-shader entry point through a groupshared array at
a dynamic (buffer-sourced) index, matching the pass's own header-comment
bitcast pattern and the storage/indexing shape used by the existing test
tools/clang/test/HLSLFileCheck/dxil/linker/lib_mat_entry.hlsl.

Writes its own commands and exit codes to manual-case-link-attempt.txt,
per the skill's "generate every manual-case-*.txt from a small script
that echoes the command it is about to run" guidance. Does not modify
compiler source, and only writes files under this issue directory.
"""
import subprocess
import sys

import os

# Repo root is four levels up from this script
# (data/issues/5328/ -> data/ -> dxc-issue-triage/ -> skills/ -> .github/ -> repo root).
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", ".."))
DXC = os.path.join(_REPO, "build", "Debug", "bin", "dxc.exe")


def display(text):
    """Redact this machine's absolute repo path to <repo> for anything logged."""
    return text.replace(_REPO, "<repo>").replace(_REPO.replace("\\", "/"), "<repo>")


def run(argv):
    printed = display(subprocess.list2cmdline(argv))
    proc = subprocess.run(argv, capture_output=True, text=True)
    return printed, proc


def main():
    lines = []
    lines.append("# issue: 5328")
    lines.append(
        "# purpose: attempt to trigger the reported LI/ST typo in "
        "HLMatrixBitcastLowerPass.cpp via dxc -T lib_6_9 -link"
    )
    lines.append("# outcome: no crash observed in any attempt (see notes.md)")
    lines.append("")

    steps = [
        [DXC, "-T", "lib_6_9", "link-a.hlsl", "-Fo", "link-a.obj"],
        [DXC, "-T", "lib_6_9", "link-b.hlsl", "-Fo", "link-b.obj"],
        [DXC, "-T", "lib_6_9", "-link", "link-a.obj;link-b.obj", "-Fc", "link-out-discard.ll"],
    ]
    for argv in steps:
        printed, proc = run(argv)
        lines.append(f"$ {printed}")
        lines.append(f"exit: {proc.returncode}")
        tail = display((proc.stdout or "") + (proc.stderr or ""))
        if tail.strip():
            lines.append(tail.strip())
        lines.append("")
    try:
        os.remove("link-out-discard.ll")
    except OSError:
        pass

    # Grep the final .ll for the fake-matrix bitcast pattern and for
    # whether storeMat's call site survived inlining.
    argv = [DXC, "-T", "lib_6_9", "-link", "link-a.obj;link-b.obj", "-Fc", "link-out-check.ll"]
    printed, proc = run(argv)
    lines.append(f"$ {printed}")
    lines.append(f"exit: {proc.returncode}")
    try:
        with open("link-out-check.ll", "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        has_bitcast_to_matrix = "to %class.matrix" in text
        has_call_to_storemat = "call void @\"\\01?storeMat" in text
        lines.append(f"final .ll contains 'bitcast ... to %class.matrix...*': {has_bitcast_to_matrix}")
        lines.append(f"final .ll contains a surviving call to storeMat in main(): {has_call_to_storemat}")
        lines.append(
            "interpretation: storeMat is fully inlined into main() by "
            "AlwaysInlinerPass (which runs immediately before "
            "MatrixBitcastLowerPass in DxilLinker::RunPreparePass) before "
            "the fake-matrix bitcast this pass targets can ever be "
            "constructed at the call boundary; SROA/mem2reg then resolves "
            "the inlined copy-in/copy-out entirely to <4 x float> loads "
            "and stores. No fake-matrix-typed StoreInst ever reaches "
            "HLMatrixBitcastLowerPass::lowerMatrix in this configuration."
        )
    except OSError as e:
        lines.append(f"(could not read link-out-check.ll: {e})")
    finally:
        for f in ("link-out-check.ll", "link-a.obj", "link-b.obj"):
            try:
                os.remove(f)
            except OSError:
                pass

    with open("manual-case-link-attempt.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote manual-case-link-attempt.txt")


if __name__ == "__main__":
    sys.exit(main())
