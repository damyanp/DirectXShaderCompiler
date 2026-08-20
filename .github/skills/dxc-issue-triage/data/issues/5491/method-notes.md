# Method notes — #5491

Recorded for collation review. Not applied to `SKILL.md` or `triage.py` by this per-issue
session (single-writer rule).

## Recognised, not new: ancestor-check trap on a rewritten-history SHA

Tried to name the specific commit that fixed PR #4174 ("Wave intrinsics inside of dead loops are
not properly deleted") to date the surrounding loop-deletion mechanism. `git log --all --grep`
found `5ec85fbc5`, but `git merge-base --is-ancestor 5ec85fbc5 HEAD` and the same check against
the registered `main-debug` ground-truth commit both failed (exit 1), even though the file the
commit is associated with (`wave_intrinsic_dead_loop.hlsl`) is present and unchanged in the
ground-truth tree. This is the exact trap SKILL.md already documents under "A rewritten history
invalidates recorded build provenance" (the batch-007 finding) — a message-only or otherwise
history-rewriting change gives every commit a new SHA without touching any tree, so an
old/mirrored SHA found via `git log --all` can fail an ancestry check against the current branch
for reasons that have nothing to do with whether the change is present. Rather than assert an
unverifiable commit identity or count, the notes cite only what is independently checkable (the
test file's presence and content) and drop the specific SHA/commit-count claim entirely. Filed
here as a second occurrence of the known trap, per SKILL.md's guidance to record repeated hits so
collation can weigh how often it recurs — not proposed as a new lesson.

## Technique: a register-name-independent "unused call result" predicate

The issue's symptom is "a call's result is unused," which is awkward to express as a plain
substring/regex match because the specific SSA register name assigned to the call varies across
compiler builds (SKILL.md already warns IR text is not portable across release ages for this
reason). For this repro specifically — a minimal function whose entire body is
`{producer-call, wave-op-call, ret void}` — "the wave-op call line is immediately followed by
`ret void`, with the gap spanned only by `[^\n]*\n` (the rest of that same line, not `[\s\S]*`)"
is a structural proxy for "nothing consumes the call's result," verified by a control
(`control-used.hlsl`) where the same call instead feeds a `sitofp` + `storeOutput` before
`ret void`, and the predicate correctly scores `no-repro`. This only works because the repro is
trivial enough that "immediately before the function's only `ret`" and "has no users" coincide;
it would not generalise as-is to a repro with multiple basic blocks or multiple wave calls, where
proving "this specific SSA value has no users" would need a real IR reader rather than a text
regex. Recording the technique and its scope limit in case a future wave/quad-intrinsic-DCE issue
(e.g. a duplicate report) reaches for the same shortcut without the same trivial-function
precondition holding.
