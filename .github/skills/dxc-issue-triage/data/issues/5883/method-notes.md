# Method notes — #5883

**Recurrence of the "%1 vs named SSA value" anchor trap, already documented
in `SKILL.md` (step 4).** First-draft `match.json` anchored the symptom on
`%dx.types.Handle %1, i32 0, ...`. `bisect` reported `regressed-in
v1.5.2010`, which was wrong: `v1.4.1907`'s disassembly carries the
identical buggy payload (`42,43,44`/`45,46,47`) but names the handle
`%buffer_UAV_rawbuf` rather than `%1`, so the literal-`%1` anchor scored it
`no-repro` for a reason unrelated to the defect. Caught by noticing the
reported boundary (`v1.5.2010`) didn't line up with anything in the issue
thread and inspecting `out-v1.4.1907.txt` by eye rather than trusting the
bisect summary. Corrected to a structural anchor (`%[\w.]+` in place of the
literal `%1`) and re-ran every affected probe; the corrected predicate
agrees across the whole history (`always-repro'd`).

No control caught this on its own — the control (`variant-noconst.hlsl`)
was only run against `main-debug`, which already uses `%1`-style naming, so
it never exercised the older register-naming convention. Nothing here
changes the guidance already in `SKILL.md`; recording only that the trap
recurred and cost one throwaway bisection pass, in case collation wants to
note how often it still bites despite being documented.
