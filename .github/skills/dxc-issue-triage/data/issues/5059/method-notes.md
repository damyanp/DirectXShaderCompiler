# Method notes — #5059

Observations worth the collation pass, kept out of `notes.md` because
they are about the tooling/technique rather than this issue's evidence.

## `dxc`'s default (no `-Fo`/`-Fc`) stdout is full text disassembly on a successful compile, not binary

Initially assumed that a plain `dxc <args> repro.hlsl` invocation with no
output flag would either fail to compile or dump binary garbage to
stdout, and started looking for a way to force `-Fc`-style file capture
through `triage.py run` (which only scores stdout/stderr text, not
generated files, though `_sync_probe_outputs` does copy generated files
back as artifacts). That assumption was wrong: verified by inspecting the
actual captured `out-v1.4.1907.txt` content (not just its byte length)
that dxc prints the full disassembly text to stdout on success across
every tested era, old and new. This eliminated an entire planned
workaround (`-Fc CON`, `-fcgl`, post-hoc artifact scraping) -- the plain
`cmd.txt` command alone captures both the "silent" and "caught" shapes of
this issue automatically, across the whole release history, with zero
extra flags. Worth checking early on any issue whose predicate seems to
need generated-file contents: it may already be sitting in stdout.

## Two-predicate split beats one `any_of` when the reported symptom itself is what changed shape

First pass combined both signatures (`Int type 'i33' has an invalid
width` and `\bto i33\b`) into a single `any_of` `match.json`. That
predicate is technically correct -- the defect really is present under
either reading -- but bisecting it collapses to "always-repro'd" and
hides the one fact most worth reporting: the *reported* shape (silent
success) stopped reproducing at `v1.9.2607`, while a *new* shape
(validator rejection) started there. Rewriting as two separate files
(`match.json` = the literal reported wording only, `match-caught.json` =
the new shape only) and bisecting each independently produced two exact
mirror-image linear scans that pin the transition release precisely.
General rule, matching SKILL.md's own guidance directly: the moment a
symptom's *current* observable form differs from what was *reported*,
stop reaching for `any_of` and write a second predicate file instead --
the combined predicate is still worth keeping too (it answers "is the
defect present at all," which the `changed-behavior` status needs), but
it should not be the only predicate driving the bisect.

## Source-level commit dating is a real time sink; a release-date bracket is often the honest stopping point

Spent real effort trying to pin the validator-behavior change to one
exact commit via `git log --all -S` on the validator's message string and
its helper function name. Found multiple plausible candidates (`90ae8d807`
/ PR #8207, and the registered ground-truth commit `89e2f98e2` / PR
#8762, which re-adds the whole rule table), but their merge dates don't
cleanly line up with the empirically-measured release-build-date
transition (`90ae8d807` merged 2026-03-10, over two months before
`v1.9.2602.24`'s 2026-05-27 build, which still shows the old behavior) --
most likely explained by release-branch cuts lagging `main`, but not
provable from source inspection alone without actually building at
intermediate commits, which this triage chose not to do given the time
cost relative to the value for a single issue. Stating the release-level
bracket precisely (`v1.9.2602.24` → `v1.9.2607`, two adjacent catalogued
releases, no gap) and citing the plausible source commits as "consistent
with, not proven to be" the cause is the correct, honest confidence level
here -- do not let an unresolved multi-candidate `git log -S` result
block finishing the triage; report the bracket and move on.
