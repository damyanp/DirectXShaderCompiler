# Method notes -- #5165

**A predicate anchored to the newest release's wording missed the same defect at the oldest
release, and produced a false regression finding.** `match.json`'s first draft required the
literal substring "I8 can only be used as immediate value for intrinsic" (with "be") plus a
regex anchoring the `trunc iN ... to i8` instruction note. Both clauses are absent from
v1.4.1907's diagnostic for the exact same TypesI8 defect on the identical repro:

- v1.4.1907: `at 0x... inside block switch.hole_check of function ShaderDomain_Cs I8 can only
  used as immediate value for intrinsic` -- no "be", no source line, no `note:`/`trunc` text,
  pointer-address + block-name format instead.
- v1.5.2010 onward (including main-debug): `repro.hlsl:8:5: error: I8 can only be used as
  immediate value for intrinsic or as i8* via bitcast by lifetime intrinsics.` / `note: at
  '%10 = trunc i32 %3 to i8' in block '#2' of function 'ShaderDomain_Cs'.`

Under the stricter predicate, `bisect` (binary search) reported `regressed-in v1.5.2010`.
Re-running with `--linear` after loosening the regex to
`I8 can only\s+(?:be\s+)?used as immediate value for intrinsic` (dropping the trunc-instruction
clause entirely, since the oldest release's diagnostic never prints that shape) rescored
v1.4.1907 as `repro`, and confirmed all 20 stable releases from v1.4.1907 through v1.9.2607
reproduce: `always-repro'd`, not a regression.

This is the skill's documented "message text is not portable ... especially at the oldest
release" trap, encountered here for the *literal diagnostic wording* itself (the "be" and the
trailing clause were added to the validator's own error string at some point between
v1.4.1907 and v1.5.2010), not just for IR register spellings. Two reinforcing observations for
future batches:

- Binary search silently trusts both endpoints once they agree/disagree in a way that forms a
  monotonic story; it will not warn that the *oldest* endpoint's diagnostic wording differs
  from every other release probed. Always eyeball the oldest release's raw capture text before
  accepting a `regressed-in <second-oldest release>` result -- that specific shape (only the
  floor release disagrees) is exactly what a wording change produces.
- For an issue whose reported symptom IS a diagnostic, prefer the loosest wording-stable regex
  that still uniquely identifies the validation rule in question, and push instruction-shape
  specificity into a *secondary*, non-blocking predicate (or drop it) rather than an `all_of`
  clause -- an `all_of` conjunction fails outright the moment either side's wording drifts,
  which is worse than a slightly looser single clause for diagnostic-quality issues.

No change proposed to `SKILL.md`/`triage.py`; the "message text is not portable" guidance
already covers this, it just was not applied rigorously enough on the first pass. Recording
here per the per-issue/no-shared-edit constraint for this session.
