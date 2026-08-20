# Method notes — issue #5328

For collation to review and (if warranted) promote into `SKILL.md` /
`triage.py`. Not a verdict; issue-specific until re-checked against
other issues.

1. **`AlwaysInlinerPass` runs immediately before `MatrixBitcastLowerPass`
   in `DxilLinker::RunPreparePass`, and defeats naive repro attempts.**
   When constructing a repro for a bug in a pass that only runs during
   `dxc -T lib_6_x -link ...`, it is not enough that the scenario uses
   `-link` at all — if the final link output resolves to a single
   shader entry point (as any ordinary compute/pixel/etc. shader must),
   every reachable function gets fully inlined into that entry point by
   `AlwaysInlinerPass` before later passes in the same pipeline run,
   regardless of `export`/`-exports` visibility. Constant-index,
   small-array and even dynamic-index/groupshared-array attempts were
   all fully inlined and resolved to plain vector loads/stores by
   `SROA`/mem2reg, leaving nothing for `MatrixBitcastLowerPass` to act
   on. The mechanism this pass targets (a bitcast from real flat/vector
   storage to a "fake" matrix-typed pointer, later reconciled by this
   pass) is real and is exercised by the existing test
   `tools/clang/test/HLSLFileCheck/dxil/linker/lib_mat_entry.hlsl` —
   but only because that test's callee is *declared but never defined*
   in the same translation unit, so there is nothing for the inliner to
   inline. A repro targeting a late-pipeline linker pass should first
   check what the *early* passes in that same pipeline do to the input
   shape, not just what flag enables the late pass to run at all.

2. **A comment posted on an issue can describe a confirmed-reproducing
   crash that is an entirely different bug from the one the issue
   reports — verify the comment's own stack trace against the issue's
   named file/line before treating it as corroborating evidence.** On
   #5328 a later comment's attached repro does crash ground truth
   (confirmed, `0xE0000001`), and the symptom *class* (a matrix-related
   internal failure) superficially matches the issue's subject area.
   But the captured stack trace names `HLMatrixLowerPass.cpp`'s
   `replaceAllVariableUses`, not `HLMatrixBitcastLowerPass.cpp`'s
   `lowerMatrix` (the function the issue actually names) — a different
   file, different function, and a different fault (`checkGEPType`
   asserting on a mismatched GEP index type, unrelated to a null
   `IRBuilder` argument). Treating "the attached repro crashes" as
   sufficient corroboration without reading the crash's own attribution
   against the issue's cited source location would have folded two
   unrelated defects into one verdict.
