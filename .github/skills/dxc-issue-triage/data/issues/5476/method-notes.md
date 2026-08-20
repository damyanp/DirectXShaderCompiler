# Method notes -- issue #5476

**A "no compiler in the toolkit can run the affected platform" case needs its
own honesty check, distinct from the documented `invalid-probe`/
`matching-clean-endpoints` traps.** Those traps are about a *release* being
unable to exercise the code under test. Here the entire *class* of available
compilers (Windows `main-debug`, and Compiler Explorer's Linux panes) turned
out to be unable to exercise the *failure condition* (a locale-dependent
*nix bug), even though one of them (CE) does run on the right operating
system family. Discovering this required actually running the CE probe
first, rather than assuming "Linux" was close enough to "reproduces the
*nix code path's failure mode." Two different things: which OS a binary
runs on, and whether that binary's specific runtime environment (locale
database contents) can trigger the bug. Worth generalising: for any bug
attributed to a locale, encoding, filesystem-case-sensitivity, or other
environment-dependent condition, running the repro on *a* machine of the
right OS family is not equivalent to running it in *the* environment where
the condition holds, and a clean CE result should be treated with the same
suspicion as clean endpoints in a `--linear` bisection -- ask whether the
instrument (CE's own container) could have shown the symptom before reading
"clean" as "fixed" or "not applicable."

**Git-log-based fix attribution needed for a defect no available compiler can
directly re-run.** `bisect` assumes there is a downloadable release binary
that can express the symptom; this issue has none (see above), so history
had to come from `git log --oneline -- <file>` over the two source files the
bug lives in, followed by reading the one relevant commit's diff and commit
message against the issue's own described failure mode. This is the same
technique used in already-known "linker output" / "reflection API" issues
where no compiler artifact exists to run, generalised one step further to
"no compiler artifact can trigger the platform condition even though the
artifact itself exists and runs."
