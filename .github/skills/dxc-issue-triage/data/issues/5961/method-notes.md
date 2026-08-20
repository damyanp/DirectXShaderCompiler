# Method notes -- #5961

- **A predicate calibrated for one HLSL language-version's literal wording does not transfer to
  another.** `-HV 202x` changes untyped-double-literal typing (conforming literals), which
  changes the numbers printed in the same diagnostic class for unrelated reasons (overflow to
  `float` range happens before the int conversion). Running that variant as an explicit
  `--hypothesis` capture rather than folding it into the primary predicate kept the "tool says
  no-repro" result (a predicate artifact) clearly separated from "manual inspection of the
  captured text shows the same defect" (the actual finding) -- worth remembering as a general
  case of "message text is not portable", one level up: it is also not portable across
  language-version modes of the *same* release, not only across releases or platforms.

- **`git blame` resolving to a repository's earliest visible (boundary/squashed) commit is a
  useful, cheap proxy for "this predates trackable history" when a full `git log -S` dig is not
  needed** -- the finding here ("always-repro'd, no invalid probes, floor release") did not need
  a specific introducing commit, so blame-to-boundary was sufficient corroboration without the
  cost of a `git log --all -S` archaeology pass.

- Widening the profile from the reporter's/CE's `-T cs_6_6` down to the oldest profile that
  still shows the symptom (`-T cs_6_0`) turned an 18-release bisectable window into the full
  20-release floor with zero invalid probes -- worth checking for any issue whose repro uses a
  newer profile than the underlying language feature actually needs, per the skill's existing
  guidance, restated here as a second confirming instance.
