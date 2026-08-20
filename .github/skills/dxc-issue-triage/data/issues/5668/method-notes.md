# Method notes — #5668

- **Same defect as #5269.** Both issues report the identical DXIL validation
  diagnostic, the identical numeric mismatch (payload size 4 vs declared 0),
  for an amplification shader whose payload is an empty struct passed to
  `DispatchMesh`. Independently reading `lib/DxilValidation/DxilValidation.cpp`
  for this issue landed on the exact same `ValidateAsIntrinsics` line #5269's
  notes already identified: `PayloadSize = DL.getTypeAllocSize(OperandVal->getType())`
  where `OperandVal->getType()` is the payload's *pointer* type rather than
  the dereferenced pointee struct type, so the check always compares against
  a hard-coded pointer-size constant (4, from DXIL's `p:32:32` datalayout)
  instead of the real payload size. This flags for collation whether #5668
  should be recorded as a duplicate of #5269 (filed three months earlier) —
  left as a judgement call, not asserted as fact in this issue's own verdict
  beyond noting the matching evidence in `notes.md`.
- Not a new predicate-writing lesson: the existing `internal_failure` /
  E_FAIL distinction and the `invalid profile` markers both applied cleanly
  here (`as_6_6` correctly demoted `v1.4.1907`/`v1.5.2010` as `invalid-probe`,
  no tool changes needed).
- **`reviewed_by` deliberately left pending.** A different-model review (`gpt-5.4`) was
  run against `comment.md`/`notes.md` as an internal quality check and found only minor
  concision trims (applied), no unsupported claims, and no bad quantifiers. Per SKILL.md,
  `reviewed_by` is a batch-collation field, not a per-issue one ("step 10 runs once over
  all the drafts"), so it is not stamped into `verdict.json` here — matching #5269's own
  verdict in this same batch, which also carries no `reviewed_by`. `triage.py audit`
  confirms: "pending collation -- no reviewed_by yet (step 10 is a batch step; do not
  fill it in yourself)".
- One thing worth flagging for a future SKILL.md pass, not promoted here
  (single-issue batch, no shared-file edits allowed): when an issue's root
  cause is "function A measures X's pointer type instead of X's pointee
  type", it is worth explicitly checking DXIL's declared pointer size in the
  target datalayout (`p:32:32` here) before accepting a magic constant in a
  diagnostic as evidence of anything about the actual operand — the same
  shape of bug could reappear elsewhere and always types the identical wrong
  number.
