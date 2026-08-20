# Method notes — #5686

## Cross-issue observation (for collation, not asserted in the draft)

This issue's root-cause read of `ValidateAsIntrinsics` in `DxilValidation.cpp` — the
amplification-shader payload-size check measures `DispatchMesh`'s payload **pointer** type via
`OperandVal->getType()` instead of dereferencing to the pointee struct, unlike the neighbouring
mesh-shader branch three lines above — was derived independently, before I looked at any other
issue in this batch. Having finished it, `data/issues/5668/verdict.json` and
`data/issues/5269/verdict.json` (both already triaged, both in batch-019) record the *same*
source-level finding, in nearly the same words, for the same file and the same lines. All three
are one validator defect wearing different faces:

- #5269 and #5668: an **empty** (0-byte) struct payload, direct-compiled with no linking
  involved. The pointer's DXIL size is a constant 4 bytes, so the check `declared(0) <
  computed(4)` fires only because the struct is empty.
- #5686 (this issue): a **non-empty** 4-byte struct, reproducing only through `-Fo as.lib`
  then `-link`. Direct-compiling the identical source does *not* trip the check, because the
  computed size (still just the pointer's DXIL size, 4 bytes) equals the declared size (4). It
  only fires once linked, because `DxilLinker.cpp`'s `DxilLinkJob::Link` never calls
  `setDataLayout` on the module it constructs (confirmed via `git log -S DataLayout` on that
  file: zero matches, ever), so the linked module's pointer size silently changes to LLVM's
  default of 8 bytes and the same vacuous check starts firing on payloads under 8 bytes.

So #5686 is not a duplicate of #5269/#5668 in the sense of "identical repro" — its trigger
condition (linking) and its second contributing defect (linker drops the data layout) are both
new to this issue — but all three share one validator defect as a common cause, and a fix to
`ValidateAsIntrinsics` alone would resolve #5269 and #5668 while a fix to *either* defect (the
validator's type dereference, or the linker's missing `setDataLayout`) would resolve #5686.
Per SKILL.md this cross-issue linkage is left here rather than asserted in `comment.md`, since
that judgement is collation's to make, not a single per-issue worker's.

## Tooling notes

- Multi-invocation `cmd.txt` (`-T lib_6_x -Fo as.lib repro.hlsl` then `-T as_6_6 -link
  as.lib`) worked exactly as documented: `run`, `bisect` and the isolated-scratch-copy
  machinery all handled the two-line pipeline with no surprises. `bisect`'s auto spelling-retry
  correctly identified `-link` as genuinely absent (not misspelled) on the three oldest
  releases by checking `--help` output directly, rather than trusting a demotion; that matched
  independent manual confirmation.
- `godbolt --skip` was the right call and cost nothing: CE cannot express a two-invocation
  lib-then-link pipeline (one command per pane, no way to hand pane A's artifact to pane B).
  Recorded with a specific reason per SKILL.md's guidance to record the decision rather than
  force a link.
- Manual capture of the linked module's disassembly (`-Vd`, to see past the validation
  failure) needed a small standalone script rather than `triage.py run --args`, because
  `--args` represents exactly one invocation and cannot express the lib-then-link pipeline with
  an extra flag appended to only the second line. Wrote `capture-vd-disasm.py` following the
  #5703-style convention (`HERE`/`REPO` resolved from `__file__`, output text redacted to
  `<repo>` before being written) so `check_paths.py`'s machine-path gate stays clean; a first
  draft with a bare absolute Windows path literal failed that gate immediately and was
  corrected before committing.
- Manually running `dxc.exe` directly (outside `triage.py run`) to explore the failure before
  writing `match.json`, per SKILL.md's "explore output before finalising a regex" guidance, left
  a stray `as.lib` binary in the issue directory — not produced by the tool's scratch-copy
  mechanism, so nothing cleaned it up automatically. Deleted by hand before finishing; worth
  remembering that manual exploration runs need their own cleanup.
