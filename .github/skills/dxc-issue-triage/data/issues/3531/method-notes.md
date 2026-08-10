# Method observations from triaging 3531 (batch-013)

For collation to promote or discard. Nothing here was applied to `SKILL.md` or `triage.py`.

## 1. A `-Zi` issue makes the embedded source a live falsification hazard, and SKILL.md only half-covers it

SKILL.md documents the CE case ("`godbolt-note.txt` is compiled, not merely displayed... never
put a literal string in the banner that the note asserts is missing") and the control case (put
the token in a source comment and compile with `-Zi -Qembed_debug`, so the predicate must score
`no-match`). What it does not say directly is the *local* consequence: for any issue whose
symptom is "identifier X has no metadata", compiling with `-Zi` puts X into
`!dx.source.contents` in every single run, so an absence predicate written on the bare name is
false everywhere and reports `never-repro'd-in-releases`. The rule that survives is: **anchor
an absence on the metadata form, never on the identifier** — here
`!DILocalVariable\([^\n]*name: "X"` rather than `X`.

The same fact is also the strongest available anti-vacuity anchor, which is the pleasant
surprise: reading the declaration under test back out of `!dx.source.contents` proves the run
compiled a shader that really declares it. That closes #8732's "vacuously true on a shader that
never mentions the symbol" hole with a clause instead of a control. Suggest adding it to
SKILL.md's absence-predicate advice as the positive form: *when `-Zi` is in the command, the
embedded source is a free anti-vacuity clause.*

## 2. The strongest control for an absence is the same declaration with one token changed

`control-name-selftest.hlsl` differs from the repro in exactly one token: the local's type is
`uint` instead of `RWByteAddressBuffer`. Same name, same line, same column region. It produces
`!DILocalVariable(... name: "DynamicallyIndexedDynamicBuffer" ... line: 15)`, which proves the
emitter can name *this identifier at this line* and chose not to for the resource.

Run per release, it becomes something better than a control: an instrument-validity check for
every probe in the history. 19 of 21 compilers pass it. Without it, "18 releases show no
metadata" is compatible with "18 releases spell debug metadata differently than my regex". This
generalises to every absence-shaped issue and is cheap; SKILL.md's per-release control advice
is currently framed around *feature presence* (#2922, #8725) and could name
*instrument validity* as the second thing to run per release.

## 3. A dead local silently disables a self-test clause

The first draft of `control-local-bound.hlsl` left `val` unused. It was dead-code-eliminated,
its `!DILocalVariable` disappeared, and the detector's self-test clause failed — so the control
scored `no-match` and would have read as "bound locals are fine", the exact opposite of the
truth. Nothing about the capture would have said so; the score is the same as a genuine
no-match. **When a predicate's self-test clause depends on a variable, the control has to keep
that variable live**, and it is worth stating because the natural way to write a control (copy
the repro, change one thing) is exactly what kills liveness.

## 4. `-fcgl` cheaply localises a missing-metadata issue to a compiler phase

SKILL.md recommends `-fcgl` for attributing a *diagnostic* to a layer. It works just as well
for attributing an *absence*: at `-fcgl` the `llvm.dbg.declare` and `!DILocalVariable` are both
present, so the issue is a loss in DXIL lowering rather than a gap in `CGDebugInfo`. One run,
and it converts "no debug info" into "debug info is emitted and then dropped", which is a
materially more useful thing to hand a maintainer. Worth generalising in the step-4/step-11
guidance: *for a missing-artifact issue, probe the earliest stage that should contain the
artifact before concluding it is never produced.*

## 5. Tool observation: `sql` fails on some column names

`triage.py sql "SELECT ... , cached_path IS NOT NULL AS cached FROM releases"` raised
`sqlite3.OperationalError` truncated to `n` in the traceback. Plain column selects work. Not
chased further; the workaround was to select the columns and post-process. Low priority, noted
only so a future worker does not assume the database is corrupt.

## 6. Nothing here needed `--repeat`

The symptom is fully deterministic (same output on repeated runs, 18/18 releases, both CE
panes). Recorded only because SKILL.md asks that the decision to skip `--repeat` be a decision
rather than an omission.

## 7. Cross-issue note, deliberately kept out of the draft

The reporter and the subject area (debug metadata consumed by a shader debugger) put this near
other debug-info issues in the backlog. SKILL.md is explicit that "same area" is not "same
defect" and that cross-issue claims belong to collation, so `comment.md` says nothing about any
other issue. Collation may want to check whether the local-resource debug-metadata loss
identified here is the same underlying loss as anything else in the tracker.
