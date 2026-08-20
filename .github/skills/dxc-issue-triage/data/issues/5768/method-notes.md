# Method notes — issue 5768

Per-issue observations only; not promoted to SKILL.md/triage.py by this worker (batch
collation's job).

- **"Sema error" control choice collides with the invalid-probe feature-absence markers.**
  My first attempt at a negative-shape control used `return UndeclaredIdentifier;` to produce
  an ordinary front-end diagnostic contrasting with the validation-stage error. `triage.py`
  auto-classified it `invalid-probe` because "use of undeclared identifier" is one of the
  documented feature-absence markers (used elsewhere to detect a release predating a
  language feature). That is correct behavior for the tool's actual purpose (release-history
  bisection), but it is a trap for *any* worker reaching for "undeclared identifier" as a
  generic stand-in for "a plain Sema error" in a same-release control — the classifier does
  not distinguish "this identifier doesn't exist because the shader typo'd it" from "this
  identifier doesn't exist because the feature postdates this release." Switched to a
  variable-redefinition error (`redefinition of 'V'`) instead, which triggers no marker.
  Worth a one-line mention in SKILL.md's marker discussion if a future batch hits it too.

- **The cross-reference timeline surfaced the actual finding, not the bisection.** All 20
  probeable stable releases repro identically — a flat line that on its own looks like
  "never attempted." `gh api .../timeline` on this issue turned up PR #3043, which is the
  closest thing to a fix this defect has ever had, merged and reverted within one week
  entirely between two stable release build dates. Nothing about running `bisect` would ever
  surface that; it only came from reading the timeline in step 1, as the skill instructs.
  Confirms the standing advice to read the timeline before touching the compiler.

- Did not consider this a candidate for `--repeat`: the symptom is a deterministic diagnosed
  E_FAIL on a type-checked shader, not a crash or anything nondeterministic.
