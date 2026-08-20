# Method notes — #4914

Observations about the *method/tooling*, for collation to consider promoting. Nothing here
changed the verdict for #4914; it is recorded here per the skill's rule that a per-issue
session writes method observations to its own `method-notes.md` rather than editing `SKILL.md`
or `triage.py` directly.

## `godbolt --compilers "id:<args>"` — do not repeat the source filename in the override

First attempt used `fxc_10_0_19041:-T cs_5_0 -E main repro.hlsl` (copying the filename out of
`cmd.txt`, the way `cmd.txt` itself is written). Compiler Explorer supplies the source
automatically as the compiled document; giving the filename again in the override args made
FXC see two file operands and fail with `Too many files specified ('<source>' was the last
one)` — a plausible-looking compiler complaint that is actually an artifact of the harness
call, not a finding about FXC. Corrected by omitting the filename from the override
(`fxc_10_0_19041:-T cs_5_0 -E main`), matching how the *unoverridden* `dxc` panes are printed
in `godbolt`'s own summary line (`CE args: -T cs_6_0 -E main`, no filename). Worth a one-line
callout in `SKILL.md`'s `id:<args>` documentation (section 7) so the next per-issue session
does not re-discover this by trial and error, since #4914 is a new instance of the same shape
of trap as the existing `-P`/`-Fi` "an override may not repeat the filename" caution already
documented for a different command.

## Pre-existing `check_paths.py` failures are outside this issue's directory

`python scripts/check_paths.py` fails on this run, but every reported line is under
`data/issues/4766/`, `data/issues/4786/`, `data/issues/4858/` and `data/issues/4958/` — none
under `data/issues/4914/`. Confirmed with `check_paths.py 2>&1 | Select-String "4914"`
(zero matches). Per the task's strict per-issue boundary, these are left untouched; flagging
them here rather than silently fixing another issue's directory, and rather than silently
ignoring that the gate is presently red for the tree as a whole. Collation/a maintainer should
decide whether to clean those up in their own issues' scope.

## Hit the documented PowerShell backtick trap first-hand, on `verdict --summary`/`--expected-symptom`

The very trap `SKILL.md` already documents (`` `else `` becoming `U+001B` + `lse`) fired here in
its "swallows a character" form: the first `triage.py verdict` invocation wrapped
`--summary "... returning \`this\` by value ..."` in an ordinary PowerShell **double-quoted**
string. PowerShell reads `` `t `` as the TAB escape, so `` `this` `` (backtick, "this",
backtick — intended as markdown code-formatting inside the stored JSON string) became a literal
TAB character followed by `his`, with the closing backtick silently absorbed. The result
committed to `verdict.json` read `"...the whole \this value..."` (a real `\t` control
character, confirmed with `'\t' in json.load(...)['summary']`), not the intended
`` `this` ``. Caught by re-reading the written JSON with `json.load` and `repr()`
immediately after recording — not by eye, since a raw TAB does not render as visibly wrong in
most viewers. Fixed by re-running `verdict` with the offending fields rewritten to avoid
backticks entirely (plain quotes instead of code-formatting) rather than hand-editing the JSON.
`SKILL.md`'s existing guidance ("single-quote any string containing `$` or a backtick") already
covers this if followed, but this is now the second recorded case of the *same* mechanism (the
first was `` `else `` in #3251's captured output, which could not be corrected because it was a
capture). A verdict field is not a capture, so it *was* correctable here — but only because it
was checked, and this argues for a stronger tooling fix than a documentation callout: consider
having `triage.py verdict`/`run` reject or warn on an unescaped backtick or `$` received in a
string argument on Windows, or reading these long-form text fields from a file argument instead
of a shell-quoted string.

## `-fcgl` is a fast, low-cost way to localize "Sema accepts it, CodeGen doesn't"

For #4914, `dxc -fcgl` (front-end codegen, the earliest CodeGen stage) reproduced the same
diagnostic as full compilation, while the repository's own `-fsyntax-only -verify` test
(`tools/clang/test/HLSL/cpp-errors.hlsl`) shows Sema raises nothing for the identical
construct. That two-probe combination (an existing `-verify` test plus a local `-fcgl` run)
cheaply confirmed the "CodeGen-only, not Sema" attribution without needing a debugger or a
source walk of `Sema*.cpp` beyond locating `genereateHLSLThis`. Not a new tooling gap, just a
technique worth remembering for other "compiler rejects code that reads like it should be
legal" issues where the diagnostic-layer question (SKILL.md's "a source location does not
identify the diagnostic layer") is in play.
