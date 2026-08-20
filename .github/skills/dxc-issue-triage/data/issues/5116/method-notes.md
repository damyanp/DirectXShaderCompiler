# Method notes — #5116

Observations about the *method*, for collation to consider promoting into `SKILL.md` /
`triage.py`. Nothing here was applied to shared files from this per-issue session.

- **A two-invocation `cmd.txt` can encode a cross-profile asymmetry as a single predicate,
  cheaply.** #5116's actual defect is a *disagreement* between `-T cs_6_5` and `-T cs_6_6` on
  the identical source, not a property either profile has on its own. Putting both
  `-T cs_6_6 -E main repro.hlsl` and `-T cs_6_5 -E main repro.hlsl` as separate lines in one
  `cmd.txt` and writing `match.json` as `all_of[contains "<positive anchor only 6.6-success
  emits>", contains "<the 6.5 diagnostic>"]` scores the joint condition correctly under
  `bisect`/`reindex` without a bespoke harness: an old release lacking `-T cs_6_6` fails line 1
  with `invalid profile cs_6_6`, which `classify()`'s existing `UNSUPPORTED_MARKER_RE` check
  correctly demotes to `invalid-probe` (verified in `out-v1.4.1907.txt`, `out-v1.5.2010.txt`),
  and a release where the asymmetry has resolved (either profile starts agreeing with the
  other) makes one clause of the `all_of` false, correctly scoring `no-repro`. This seems
  general enough for any "profile/flag A silently accepts what profile/flag B (correctly)
  rejects" issue and might be worth a line in step 4 alongside the existing `any_of`/`all_of`
  guidance, which currently only illustrates *one* defect with two *symptom signatures* (e.g.
  Debug assert vs. Release access-violation), not one defect expressed as a *pairwise*
  cross-argument comparison in a single capture.

- **The naive version of this predicate (just "compiles clean at cs_6_6") fails its own
  control.** My first draft scored "present" on plain compile success at `-T cs_6_6`, anchored
  only by a positive marker that codegen was reached (`contains "dx.op.sampleGrad"`). Running
  that against a hand-built negative control (`control-single-path.hlsl`: same resource shapes,
  same `SampleGrad` call, but the array index has no `inout`/branch ambiguity) also matched,
  because *any* valid `SampleGrad`-on-a-texture-array shader satisfies "compiles clean and
  reaches SampleGrad" — the predicate wasn't anchored to the asymmetry at all, just to ordinary
  success. Only requiring the *paired* observation (6.6 succeeds **and** 6.5 emits the specific
  diagnostic, both in the same capture) made the control fail as it should. Worth restating
  step 4's "give every text-based predicate a control" rule explicitly for the cross-profile
  case: a control must be run through **every arm of the pair**, not just the one that looks
  like the primary repro, or a predicate that only tests "success" will pass a control it
  shouldn't.

- **`godbolt --compilers` accepted a duplicate compiler id across panes without complaint**
  (`dxc_trunk:-T cs_6_6 -E main,dxc_trunk:-T cs_6_5 -E main` in one `--compilers` spec), and the
  shortlink read-back confirmed both panes were stored correctly with their distinct
  `options`. That is a reasonable pattern for exactly this kind of cross-profile-only contrast
  (same compiler, only the argument changes) and might be worth naming explicitly in step 7 next
  to the existing "contrasting compiler" (`fxc` vs `dxc`) example, since right now every worked
  example there varies the compiler id, not just its arguments.
