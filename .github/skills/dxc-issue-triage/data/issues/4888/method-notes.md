# Method notes — issue #4888

These are observations about the *method*, for collation to consider promoting into
`SKILL.md`/`triage.py`. Nothing here should be read as a verdict; verdicts live in
`verdict.json` and `notes.md`.

- **`reviewed_by` deliberately left blank.** Per this batch's orchestration instructions, step
  10 (a different-model review of the draft) is a batch-level activity, not a per-issue one, and
  claiming a review happened when it did not would be worse than an honest gap. `triage.py audit
  --issue 4888` (run without `--collated`) correctly treats a missing `reviewed_by` as
  informational ("pending collation -- no reviewed_by yet") rather than a failing gap, which
  matches SKILL.md's own guidance that `audit` is safe to run mid-batch and that only the
  batch-level `reindex`/collation pass enforces the reviewed-by requirement. No tooling change
  needed; this is confirmation the existing behaviour is already correct for a single-issue
  session that cannot itself perform step 10.

- **`--hypothesis` is exactly the right tool for "does a comment's old crash claim still
  hold".** #4888 had a comment reporting an `isa<>` assertion under `-spirv`; recording
  `--expect match --hypothesis` before running captured the honest "refuted" outcome
  (`variant-spirv-crash-main-debug--match-crash.txt`,
  `variant-spirv-primary-main-debug--match-crash.txt`) instead of silently discovering it was
  fixed and only asserting that after the fact. Nothing to change here; just a positive data
  point for the pattern already documented in SKILL.md.

- **An issue-local release matrix for a secondary, `--args`-only signature is cheap when the
  releases are already cached.** `bisect` cannot vary `-spirv` (it only substitutes `dxc.exe`
  against `cmd.txt`'s fixed arguments), so the SPIR-V crash needed the documented
  "per-release controls currently need an issue-local matrix" pattern
  (`measure-spirv-history.py`). Every release this touched already had a `cached_path` resolved
  in `triage.db` from earlier batches downloading them, so the whole 19-release matrix (17 after
  excluding the two `invalid-probe` floor releases) cost no network time. Nothing to change in
  the tool; recording this because it is the second or third issue (after #3414/#3044-style
  cases mentioned in SKILL.md) that needed the same manual pattern, and if a fourth one hits it
  independently, that repetition is the signal SKILL.md itself says justifies promoting it into
  `triage.py` rather than documenting it again as prose.

- **A secondary predicate found a real, well-evidenced regression-fixed transition
  (v1.8.2403.2 -> v1.8.2405) that the primary predicate's history says nothing about.** This is
  a case for SKILL.md's existing "an issue may need more than one predicate" guidance working
  exactly as intended: the primary claim (`always-repro'd`) and the secondary one (`fixed`
  between two specific releases) would have collapsed into one misleading verdict if scored
  under a single predicate, since the primary's own history never leaves the `repro` state
  across the same window.

- **An early exploratory probe that should have used `--hypothesis` was instead declared as a
  strict `--expect match` control, and `audit` correctly caught it later as a "failed control".**
  `variant-cs-array-dxil-main-debug.txt` was a probe of the `-Vd` compute-shader restatement
  where I predicted (wrongly, as it turned out) that the primary predicate would still fire even
  with validation disabled; because `-Vd` skips the validator entirely, no-repro was the only
  possible outcome and the `--expect match` declaration was simply a mistake, not something
  `--hypothesis` framing would have been ambiguous about. Fixed via `triage.py expect --capture
  ... --expect no-match --why ...` per SKILL.md's documented mechanism for correcting a stale
  *declared* expectation, rather than hand-editing the capture (the measurement itself was
  already correct). Lesson for next time: when a probe's outcome is genuinely uncertain because
  of an interacting flag like `-Vd` rather than the defect itself, reach for `--hypothesis`
  before `--expect`, even for what looks like a simple variant run.

- **`audit` requires every `.hlsl` file in the issue directory to have a tool-made capture, which
  caught a variant (`variant-cs-selected.hlsl`) that had been authored but never run.** This is a
  useful, low-cost check: a written-but-unexecuted variant file is exactly the kind of thing that
  looks like evidence in a directory listing but isn't. No tooling change needed; just confirming
  the check does what it should — I ran it with `--args "-T cs_6_6 -E main -Od
  variant-cs-selected.hlsl"` (validator enabled, mirroring `variant-cs-array-dxil-validated`'s
  convention rather than the `-Vd` command quoted in the issue comment) so the resulting
  no-repro is a genuine corroboration of tex3d's "already supported" claim and not another
  validator-bypassed no-op.

- **A custom per-issue generator script (`measure-spirv-history.py`) initially wrote raw absolute
  `cached_path` values into its output, which `audit`'s path-hygiene check correctly flagged (19
  occurrences).** Fixed by importing `triage.py`'s own `display_exe`/`redact_paths` helpers
  (`sys.path.insert` + `from triage import ...`, safe because `triage.py` guards its CLI under
  `if __name__ == "__main__":`) rather than re-deriving equivalent redaction logic, then
  regenerating the capture. Worth calling out for collation: any future issue-local matrix script
  should import these helpers from the start rather than discovering the hygiene gap after the
  fact — the helpers are already public functions in `triage.py`, so no tooling change is needed,
  just a reminder that ad hoc scripts under an issue directory are still subject to the same
  hygiene rules as `run`'s own output.
