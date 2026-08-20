# Method notes — #5338

Observations for collation to consider promoting; not applied to SKILL.md or
triage.py from this per-issue session.

1. **A CE control compiler needs a profile it can actually accept, not just
   the profile named in the repro's own command.** `godbolt --compilers
   "fxc_10_0_19041:/T vs_6_0 ..."` (reusing the repro's own `-T vs_6_0`)
   fails with `Unsupported shader model specified "vs_6_0"` before it ever
   reaches the construct under test — FXC has no SM6 profile family at all.
   Re-run with `/T vs_5_0` (still an entry point FXC supports) to actually
   test the claim "compilers 5.1 and lower accept this". Worth a line in
   SKILL.md's godbolt section: when adding an FXC contrast pane, use an
   FXC-supported profile, not the repro's own `-T`, and treat FXC's
   rejection of an SM6-only profile as an FXC-profile-mismatch, not a
   finding about the construct.

2. **A single-predicate `bisect --linear` can report a "fix" that a second
   predicate shows is really a third failure mode.** Here `match.json`
   (`internal_failure`) alone would say v1.5.2010..v1.6.2112 "fixed" it. A
   second predicate on the exact validation-error text
   (`match-diagnostic.json`) shows those releases still reject the input —
   just with a diagnosed DXIL-validation error instead of a crash. SKILL.md
   already has "An `all_of` result hides which clause moved" for a
   conjunction inside one predicate; the same caution applies across
   *independent* predicate files for one issue when the reported symptom is
   crash-shaped but the compiler's behaviour has more than two states
   (crash / clean / diagnosed-reject). Might be worth a short addition
   generalising the `all_of` warning to "a clean result under one predicate
   is not evidence of a correct compile; check whether a second predicate
   would call the same release a reproduction of something else."

3. **A 60-second default timeout is worth re-confirming by hand before
   trusting it as a real hang**, especially for the *oldest* release in a
   scan, where "the tool it timed out against is unusually slow to start"
   is a live alternative hypothesis. Re-running v1.4.1907 directly with a
   240-second wall clock (4x default) still did not return, which is strong
   enough to call it a genuine hang rather than a marginal timeout. This
   cost about 4 minutes and settled a question that would otherwise have
   been guessed at.
