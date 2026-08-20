# Method notes -- #5269

No new method lessons for `SKILL.md` / `triage.py`. Observations kept local to this issue:

- The reporter's repro link (`shader-playground.timjones.io`) is unreachable from this
  sandboxed environment (DNS failure), which is a good reminder that a third-party
  playground link is not a durable repro source -- always be ready to reconstruct from the
  issue's textual description and the repo's own nearest test pattern, and mark the result
  `agent-constructed` rather than silently treating a reconstruction as the reporter's exact
  input.
- This is a case where reading the failing validator's source paid off far more than any
  number of additional probes could have: `ValidateAsIntrinsics`'s first payload-size
  check takes `OperandVal->getType()` (the payload's pointer type) instead of stripping the
  pointer first, so `DL.getTypeAllocSize` always measures a 32-bit-pointer-sized constant
  (4 on this datalayout) rather than the real payload size. This explains, mechanically,
  why the defect is invisible on every ordinary (non-empty, >=4-byte) payload and fires
  only on the one input this issue is about. Did not promote this into `SKILL.md` because
  it is not a generalizable triage-method lesson (it doesn't change how any predicate,
  control or bisection is written) -- it's an issue-specific root-cause finding, recorded
  in `notes.md`.
- No cross-issue claim is made here (single-writer discipline); if collation independently
  notices #5269 relates to another empty-struct/zero-size-type issue in this batch, that is
  collation's call to make and record, not this worker's.
