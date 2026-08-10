# Method notes — #4351

Observations about the *method*, not about the issue. #4351 is a rewriter issue,
so it hit the ground already broken open by #4273; most of what is below is
either a re-verification of an inherited claim or a new trap.

## `dxr -no-warnings` is inverted, and that inversion is an evidence channel

The most useful thing found this pass. `dxr.cpp:147` passes
`!dxcOpts.OutputWarnings` as the "quiet" argument to
`WriteOperationResultToConsole`, so `-no-warnings` **enables** the extra output
stream rather than suppressing it. What appears is `DoRewriteUnused`'s internal
accounting:

```
//found 1 globals as candidates for removal
//found 1 functions as candidates for removal
//entry point found
//found 0 globals to remove
//found 0 functions to remove
//found 1 types to remove
```

That last line is a *self-report of the decision*, and it makes an absence
predicate far less lonely. `struct Child` missing from the output is consistent
with "the rewriter removed it" and also with "the rewriter fell over and printed
less"; `//found 1 types to remove` against the control's `//found 0 types to
remove` distinguishes them from inside the compiler.

Worth generalising in the skill: **when a predicate turns on an absence, look
for a verbosity, statistics or accounting flag that turns the absence into a
presence.** The skill already insists on anti-vacuity anchors; an internal
counter is strictly better than an anchor, because it reports the decision
rather than the side effect. Cheap to look for — one grep for the message text
in the pass that is under suspicion.

The generalisable half of the trap: a flag whose name says "less output" may be
wired to mean "more". Do not infer a flag's polarity from its name; read the one
line that consumes it.

## Inherited claims, independently re-verified

The prompt supplied three measured facts from #4273 and told me to verify rather
than assume. All three held, and re-verifying was cheap (about three commands):

- **`dxc.exe` cannot reach the rewriter.** Re-measured directly:
  `dxc -E InitArgs -remove-unused-globals repro.hlsl` → `Unknown argument`,
  exit 1. Captured as `variant-dxc-rejects-rewriter-flag-main-debug.txt` rather
  than cited from the neighbour, because the neighbour's capture is evidence for
  the neighbour's shader.
- **`bisect` refuses a non-`dxc` harness**, so a purpose-built matrix is needed.
  Held; `measure.py` is the local descendant of #4273's.
- **v1.4.1907 is a genuine invalid probe.** Held, and I confirmed it from a
  second, independent direction: `git show v1.4.1907:include/dxc/Support/HLSLOptions.td`
  has no `RewriteOption` and no `remove-unused-globals`. The measurement says
  "this release rejects the smallest rewriter option"; the source says "this
  release has no rewriter options". Two dissimilar methods agreeing is what
  makes the exclusion safe to state in a public comment.

**The re-verification cost is much lower than the skill's warning implies, at
least for measurements.** Re-running a neighbour's *measurement* on your own
shader is a few commands and yields a capture you own. What actually needs care
is inherited *explanations*: I re-derived the root cause from source for my own
two asks rather than reusing #4273's, and they turned out to be different gaps
in the same pass — one would not have substituted for the other.

## `--expect` for a control whose correct outcome is `invalid-probe`

`run --expect` takes `{match, no-match, invalid-probe}` while `run` reports
`{repro, no-repro, invalid-probe}` — the two vocabularies are deliberately
different, and `invalid-probe` is the one value that appears in both.

I declared the misspelled-flag control as `--expect no-match`, reasoning "the
misspelling should not reproduce". Wrong: a rejected flag does not produce a
non-matching *run*, it produces no run at all, and the tool correctly scored it
`invalid-probe` and flagged the mismatch. Corrected with
`triage.py expect --issue 4351 --label misspelled-flag --expect invalid-probe`.

The lesson is worth stating positively, because the mistake is natural: **expect
`invalid-probe` for any control that works by making the compiler reject its
input.** A negative control that proves a flag is parsed *must* be an
invalid-probe — that is the whole mechanism by which it proves anything. The
`expect` subcommand existing as a separate verb was what made this cheap to fix
without touching a capture.

## Write the predicate so the control differs in exactly one clause

`match.json` clause 1 is
`\bChild\s+\w+\s*(\[\s*\d+\s*\])?\s*;`, with the array subscript **optional**.
That is deliberate. The non-array control's output contains
`Child SingleChild;`, which still satisfies clause 1, so the control and the
repro differ in exactly one clause — clause 3, the absence of `struct Child`.

Had I anchored clause 1 to the array form, the control would have failed two
clauses, and "no-repro" would no longer have isolated the variable. The general
form: **write the shared anchors to be true of both arms, so the arms differ
only where the hypothesis says they differ.** A control that fails for two
reasons is a control that tests neither.

## Small tool friction

- **The capture echo hardcodes `dxc`.** Every `run` capture opens with
  `$ dxc <args>` even when the harness is `dxr.exe`; the truthful line is the
  `[exe]` line below it. For a rewriter issue, where "which binary was this?" is
  the whole question, that is a genuine reading hazard — a human checking my
  evidence sees a command that, if pasted, fails with `Unknown argument`. The
  header does carry `# compiler:` and `# exe:`, so the information is present,
  but the one line that *looks* like a runnable command is wrong. Echoing the
  harness's own basename would fix it. My scripted evidence works around it by
  echoing `subprocess.list2cmdline(argv)`.
- `triage.py sql "SELECT ... exe ..."` fails; the column is `exe_path`. In
  `runs` the analogous trap is `issue`, which is really `issue_number`, and
  there is no `label` column — variant labels live in the capture filename. A
  one-line note in the `sql` help text, or an alias view, would save the
  round-trips. Minor.
- Ripgrep (and `grep` via the `grep` tool) silently returns nothing for files
  under `.github/` — no error, just zero results, which looks exactly like "no
  matches". `Select-String` works. This is a *silent* failure of a search tool
  inside the skill's own directory, which is the worst possible place for it;
  worth a line in the skill so the next worker does not conclude a file lacks
  text it contains.
- `run --args` replaces the entire command including the filename, and
  overwrites the primary capture unless `--label` is given. Both behaviours are
  documented; the second is still easy to walk into when adding a variant late.

## Cross-issue observation (deliberately kept out of the draft)

#4351 and the 2022-08-15 comment on it are two symptoms of one design property
of `DoRewriteUnused`: type liveness is computed from value references only, so
any type that is *named but never referenced* is at risk. Array element types
and unread parameter types are two instances; there are plausibly others (I
observed the same loss for an array-typed local in a scratch run, not captured
as a case). A fix aimed at either symptom alone would leave the other standing.

Per the prompt this is not a cross-issue claim about another issue *number*, but
it is the kind of connection the skill wants confined to method notes, so it is
here and not in `comment.md`.

## What I did not resolve

`godbolt --skip` is recorded with reasons, but I am not certain it is the best
call. A CE pane *could* show `rewritten.hlsl` failing to compile, which is the
harm. It would also imply DXC rejects a user's shader, when in fact DXC
*generated* that shader — a misleading frame, and CE cannot run `dxr` to show
the generating step. I chose no pane over a misleading one. A skill rule for
"the artifact is compiler output, not user input" would decide this class of
case rather than leaving it to judgement.
