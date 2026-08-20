# Method notes — #4871

Observations worth the collation pass in step 10/reindex, kept out of
`notes.md` because they are about the *tooling and technique*, not this
issue's evidence.

## `match.json` predicates are entry-point-name-scoped; a cross-stage variant needs its own file

`match.json`'s codegen anchor `define void @PSMain\(` is correct and
necessary (it stops the symptom clause from matching a compile that never
reached codegen), but it silently breaks the moment the same predicate is
pointed at a differently-named entry point. Retargeting the primary
`repro.hlsl` (`PSMain`) at a compute-shader restatement (`repro-cs.hlsl`,
entry `CSMain`) for the `hlsl_clang_trunk` Compiler Explorer pane produced a
false "expect mismatch" warning against `match.json`, even though the actual
IR correctly showed the bug (`add i32 ..., -2`) — the predicate's *anchor*
clause failed, not the *symptom* clause. Fixed by writing a second file,
`match-cs.json`, identical except the anchor is `define void @CSMain\(`, and
capturing the CS variant with `--match match-cs.json` explicitly. Worth a
generic rule: any predicate with a name-specific structural anchor needs a
matching predicate file per distinct entry-point name it will ever be run
against, not a single shared predicate reused positionally.

## Profile-lowering to widen the probeable release range is a general, low-risk move when the defect is profile-independent

The reporter's exact command used `-T ps_6_7`, which does not exist before
v1.7.2207 and would have scored 6 older stable releases `invalid-probe`,
hiding whatever regression history exists below that version. Since the
defect here is in AST-level `inout` argument handling with nothing to do
with shader-model features, lowering to the oldest profile the target stage
supports (`ps_6_0`, confirmed locally to reproduce identically before
adopting) recovered the full history and surfaced a real
v1.4.1907(clean)/v1.5.2010(regressed) boundary that would otherwise have
been invisible behind six `invalid-probe` results. General rule for future
issues: before accepting an `invalid-probe` run of stable releases as the
final answer, check whether the repro's *chosen* profile/version flag is
load-bearing for the defect itself (usually easy to tell — does the bug
description mention any SM-6.x-specific feature?) or just an artifact of
whatever the reporter happened to pick, and re-probe at the oldest workable
profile if the latter.

## `bisect --linear`'s "non-monotonic history" label fires on run-count, not on actual oscillation

`triage.py`'s linear-scan output labels any scan whose collapsed run list
has `len(runs) != 1` as "non-monotonic ... transitions at ...", but a single
clean regression with no reversion also produces `len(runs) == 2` (one
`no-repro` run, one `repro` run) and gets the same label as a genuinely
oscillating history. Read the actual `runs` list before writing "the history
is non-monotonic" into a comment or `verdict.json`'s `history` field — for
this issue the correct, precise description is "one clean regression at
v1.5.2010, no reversion through v1.9.2607," and writing the tool's literal
label instead would misleadingly suggest a fix-then-revert that never
happened.

## An inert CLI flag is worth a `--expect match` identity control, not just a byte-diff

For the dropped `-fspv-target-env=universal1.5` flag, a manual byte-diff
established inertness once; capturing it a second time through
`triage.py run --args "..." --label as-filed --expect match` turns that into
a standing, re-runnable check (any future codegen change that made the flag
load-bearing would flip this control's outcome without anyone re-deriving
the byte-diff by hand). Cheap to do whenever a filed command line is
deliberately deviated from; worth doing by default rather than only when
something looks suspicious.
