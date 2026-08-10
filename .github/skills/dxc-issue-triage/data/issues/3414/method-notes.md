# Method notes — from triaging #3414 (batch-012)

Observations about the *method*, not about the issue. Kept separate so they can be collated
without touching `SKILL.md`.

## Exploring old releases before finalising the predicate changed the verdict

The first compile was against ground truth, and its DXIL was correct. Under the rules written
in `expected.md` that pointed at `not-compiler-verifiable`, and it would have been defensible
to stop there and write it up. Compiling two or three old releases *before* settling the
predicate is what turned it into a measured `fixed` with a 13-release window and a named
candidate commit.

The general shape: for an issue several years old whose ground-truth output looks clean, a
handful of cheap probes at releases contemporary with the filing date is worth more than any
amount of reasoning about the current output. The report was written against a compiler nobody
has run yet at that point.

Corollary for step 4: the predicate should be written after that reconnaissance, because a
predicate written from clean output can only encode what correct code looks like.

## `--linear` is not just for non-monotonic history, it is for clean endpoints

Both ends of the release range are clean here, so a binary search short-circuits to "never
reproduced" and erases the entire window. This is the trap SKILL.md records for #3768, but it
is worth stating in the more general form: **binary search is only valid if you already know
the endpoints disagree.** A regression that has since been fixed presents as agreeing
endpoints, and that is precisely the shape of a stale bug report worth triaging. If the issue
is old and ground truth is clean, `--linear` is the default, not the fallback.

## Anchors must be validated across the release range, not against ground truth

`add i32 %\d+, 1` scored v1.4.1907 no-match for a reason with nothing to do with the symptom:
that release emits *named* SSA values, `%.i09 = add i32 %.i08, 1`. Widening to `%[\w.]+` fixed
it. Numeric-register anchors are safe only on modern output; anything scanning a decade of
releases should assume the naming scheme changed.

This is the same failure mode as an invalid probe — a release scoring no-match for a reason
unrelated to the bug — but it does not trigger the `invalid-probe` classifier, because the
compile succeeded. Worth a look whenever the oldest one or two releases are the only clean
ones.

## Per-release controls need a per-issue script

`run --compiler <tag>` cannot target releases: they are rows in `releases`, not registered
compilers. A small per-issue `measure-controls.py` reading `cached_path` from `triage.db` and
writing `manual-case-*.txt` is the practical route, and it is what turns "0 invalid probes"
from an assumption into a measurement — `control-hello.hlsl` compiling on all 20 releases is
the evidence that each clean probe is a real negative rather than a missing feature.

Two details that cost time: release binaries sit at inconsistent paths (`v1.4.1907\dxc.exe` vs
`v1.5.2010\bin\x64\dxc.exe`), so paths must be read from the DB rather than constructed; and
the `releases` table has no `sort_key`, so order by `build_date`.

## `incorrect-code` does not mean "the compiler emitted incorrect code"

Its description in the live taxonomy is "Issues relating to handling of incorrect code" — i.e.
how DXC handles invalid *source*. For a wrong-code bug the apt label is `correctness` ("Bugs
that impact shader correctness"). The names are close enough to invite the wrong pick, and the
brief for this issue suggested `incorrect-code` on exactly that misreading.

There is also no raytracing or DXR label in the 58-label taxonomy, so a DXR issue can only be
tagged by stage (`dxil`) and kind.

## `triage.py` regex evaluation is MULTILINE but not DOTALL

`.` does not cross lines. A predicate spanning a `define` line and a later call needs `[\s\S]`
or explicit `\n` in the gap, e.g. `(?:[^\n]*\n)*?`. Easy to get wrong in a way that silently
scores everything no-match.

## Grep tool false-zeroes in this tree

The agent `grep` tool returned zero matches for patterns that `Select-String` found, unless a
`glob` filter was given. Anything where a zero result would be *evidence* (an absence claim, a
"no release does X" check) should use `Select-String`.

## The blind re-derivation earns its cost

Run for the `close-fixed` requirement, it independently reproduced status, both transition
points, repro quality and suggested action — and separately caught a stale header comment in a
control file that still described the abandoned first theory, plus the divergence between the
pre-registered rules in `expected.md` and the final status. Both were fixed rather than
argued. Handing over the directory *without* `notes.md`/`comment.md` is what made those
findings possible; they are exactly the things the author cannot see.
