"""Record the #4540 verdict.

The verdict text is written here rather than on a PowerShell command line, because PowerShell
silently expands `$` and treats a backtick as an escape inside double-quoted strings, and both
have reached committed triage artifacts before. Passing argv straight to triage.py's parser
removes the shell from the path entirely.

Usage (from the skill root):  python data/issues/4540/record-verdict.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "scripts"))
import triage  # noqa: E402

SUMMARY = (
    "Reproduces on main (1.9.0.5433) and on all 20 stable releases from v1.4.1907 to "
    "v1.9.2607, so it predates the 2022 report. `static groupshared uint` lowers to "
    "`@storeTile = internal unnamed_addr addrspace(3) global i1 false`; docs/DXIL.rst:240 "
    "defines i1 memory accesses for thread-local memory only, and i32/f32/f64 for "
    "groupshared. Removing the single token `static` gives "
    "`addrspace(3) global i32` -- that is the known-good control, and across 22 builds "
    "(20 stable releases, 1 prerelease, main) the repro emits i1 on 22/22 while the control "
    "emits it on 0/22, with the predicate self-test passing 22/22. Confirms the maintainer "
    "comment about the validator and the spec contradicting each other: DXIL validation "
    "accepts the i1 module on 22/22 builds, while a 64KB-groupshared control is correctly "
    "rejected on 22/22, so the validator does police groupshared memory and still does not "
    "object. Attributed by measurement with dxopt (null-pass control emits i32): -globalopt "
    "is necessary and sufficient, matching TryToShrinkGlobalToBoolean "
    "(lib/Transforms/IPO/GlobalOpt.cpp:1595); `static` supplies the internal linkage that "
    "makes the global eligible. The shrink is value-preserving per thread (loads come back "
    "as select/zext); what it breaks is the groupshared object type. Clang trunk emits "
    "addrspace(3) global i32 for the same source at -O3. The reporter's GPU-level symptom "
    "was not verified -- it needs hardware."
)

EXPECTED_SYMPTOM = (
    "`static groupshared uint` lowers to a groupshared global of LLVM type i1 "
    "(`addrspace(3) global i1`), a type docs/DXIL.rst:240 defines for thread-local memory "
    "but not for groupshared memory. Scored as a presence, not an absence, with a "
    "self-test clause matching a groupshared global of ANY integer type and an anchor on "
    "`define void @main()` so a failed compile cannot score as a reproduction. Known-good "
    "control: the same file with the single token `static` removed, which must not match."
)

ARGV = [
    "verdict",
    "--issue", "4540",
    "--batch", "batch-016",
    "--status", "repros",
    "--repro-quality", "complete",
    "--history", "always-repro'd",
    "--confidence", "high",
    "--suggested-action", "still-valid-keep-open",
    "--summary", SUMMARY,
    "--expected-symptom", EXPECTED_SYMPTOM,
    "--notes-path", "issues/4540/notes.md",
    "--triaged-with-commit", "13730886e",
    "--triaged-by", "GitHub Copilot CLI (claude-opus-4.6)",
    "--godbolt-url", "https://godbolt.org/z/7Kexss5x8",
    "--labels-now", "bug,correctness,validation",
]

if __name__ == "__main__":
    sys.argv = ["triage.py"] + ARGV
    triage.main()
