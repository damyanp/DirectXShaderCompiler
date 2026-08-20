# Method notes — #4965

- `run --shader X --label Y --expect ...` treats `match`/`no-match` as "the primary predicate
  fired / did not fire", not "the two commands produced identical output". Declaring
  `--expect match` for an identity check (same behaviour under a cosmetically different
  command spelling, e.g. `/T` vs `-T`) against a predicate whose current ground-truth verdict
  is `no-repro` prints a spurious `WARNING: control expected match but scored no-repro` even
  though the two commands are in fact identical. The fix is to declare what the predicate
  actually measures (`no-match`, since the primary already scores clean) and confirm identity
  by comparing the two captures' body text instead — `triage.py expect` handles the
  correction cleanly (`--capture ... --expect no-match`) without re-running anything. Might be
  worth a line in the skill's `--expect` guidance distinguishing "identity of two commands"
  from "predicate fired" — they are not the same kind of check.

- This issue is a second measured case (after #7300/#7033's SPIR-V debug-info family) where an
  `internal_failure`-classed issue's crash shape changes across *both* release-age and build
  configuration in ways the reporter and a maintainer had already characterised in the thread
  (access violation / bad-cast text / Debug assert / Linux SIGSEGV, four shapes for one root
  cause). Composing the predicate on `internal_failure` alone (no `any_of` needed here, since
  every shape already satisfies plain `internal_failure`'s exit-status-or-text criteria) was
  sufficient; no shape needed a bespoke sub-predicate. Worth noting as a data point that not
  every multi-shape crash needs `any_of` — only ones where a shape would otherwise fall
  outside `internal_failure`'s own criteria (e.g. a hang) need the explicit composition.
