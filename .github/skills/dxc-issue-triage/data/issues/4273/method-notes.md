# Method notes from #4273

Observations for future batches. Nothing here is a claim about #4273 itself -
that is in `notes.md`. This was the first issue in this workflow to exercise the
**rewriter**, so most of what follows is new ground rather than a refinement.

---

## 1. `triage.classify` scores `Compilation failed - error code 0x8007xxxx` as `no-repro`

v1.4.1907's rewriter rejects every `-`-prefixed rewriter option with:

    Compilation failed - error code 0x80070057.   (0x80070057 = E_INVALIDARG)

exit 1, no other output. `classify` has no marker for this shape, so it fell
through to `no-repro`. That **failed safe** - it did not manufacture a
reproduction - but a naive reading of the release table would have reported
"fixed in the oldest release, regressed at v1.5.2010", which is the exact
opposite of the truth.

What rescued it was per-release *controls*, not the primary probe: an `optcheck`
(`-unchanged repro.hlsl` - does this build accept the option surface at all?)
and a `noopts` (bare `repro.hlsl` - does the rewriter run at all?). optcheck
failing while noopts succeeds is a clean signature for "this release predates
the options". Confirmed independently from source with
`git show v1.4.1907:include/dxc/Support/HLSLOptions.td`.

**Suggestions.** (a) Add `Compilation failed - error code 0x` to the
invalid-probe marker set - an HRESULT-only failure with no diagnostic text is
never a reproduction of a *behavioural* symptom. (b) More generally, the pattern
"the primary probe alone cannot distinguish 'clean' from 'cannot express the
question'" is not specific to the rewriter; any issue whose repro depends on a
flag that was introduced partway through the release range has it. A generic
`--optcheck` control - run the repro's flags against a trivially-satisfiable
input and require it to parse - would catch it cheaply.

## 2. `-external` is a confound when the harness is not `dxc.exe`

The obvious way to point an old release's code at a new driver is
`-external <dxcompiler.dll> -external-fn DxcCreateInstance`. For `dxr.exe` this
is unsafe: `dxr` forwards its **entire argv** to
`IDxcRewriter2::RewriteWithOptions`, so `-external` is re-parsed by the *release
DLL's* option table - and `-external`/`-external-fn` only gained `RewriteOption`
in the 2020-03-04 change (#2730). On exactly the oldest releases, where the
answer is most delicate, the mechanism perturbs the measurement.

Safer pattern, used here: copy the fixed driver next to each release's
`dxcompiler.dll` in a scratch directory (`.cache/rw4273/<tag>/`) and run it from
there - Windows searches the executable's own directory first. Nothing is added
to the command line, so the release's option parser sees exactly the reporter's
options and nothing else.

Both mechanisms were then cross-checked (`measure.py --equiv`): SHA-256 over
combined stdout+stderr, identical on all 20 releases. Worth doing rather than
asserting - it costs one extra run per release and converts "I believe these are
equivalent" into a measurement.

**Generalisation:** whenever the thing being varied is `dxcompiler.dll` rather
than the executable, prefer directory staging to `-external`, and prove the two
agree at least once.

## 3. `/`-prefixed nonsense is silently ignored - confirmed in the rewriter driver

The skill's known hazard reproduces here, and the sharper form is worth writing
down. On ground truth, against the same shader:

- `/ZZZNONSENSE` -> exit 0, output **byte-identical** to omitting it entirely.
- `-ZZZNONSENSE` -> exit 1, `dxc failed : Unknown argument: '-ZZZNONSENSE'`.

So the silent-ignore hazard is specific to the `/` prefix; `-`-prefixed unknown
options *are* diagnosed. Both spellings of the *real* option
(`-remove-unused-globals`, `/remove-unused-globals`) produce identical output,
so `/` is not "broken", it is "unvalidated".

The cheap proof that a flag was honoured is a **three-way** comparison, not a
clean exit: flag present vs flag absent vs flag misspelled. Present-vs-absent
must differ (the flag did something); misspelled must fail loudly (the name you
typed is the name the parser knows). `flagcheck.py` in this directory is a
reusable shape for that.

Related presentation bug found while writing it: the first draft printed
"removed"/"absent" for the *failed* runs, computed from output that was an error
message. It read as a finding. Fixed to print `n/a` when the run did not exit 0.
**A derived column must not render a value for a row where the underlying
measurement did not happen.**

## 4. `dxr` parses options twice, and the two parsers give different errors

`dxr.exe` calls `ReadDxcOpts(optionTable, DxrFlags, ...)` itself and *also*
forwards argv to the DLL, which parses again. Consequences when reading captures:

- `dxc failed : Unknown argument: 'X'` is the **driver** (ground-truth table)
  talking - it can reject an option the DLL would have accepted.
- `Compilation failed - error code 0x80070057.` is the **DLL** talking.
- `-remove-unused-globals` without `-E` fails driver-side at
  `lib/DxcSupport/HLSLOptions.cpp:1396`, before the DLL is involved at all.

When the driver is newer than the DLL under test, the driver's table is the
*newer* one - so a driver-side rejection says nothing about the release.

## 5. `dxc --help` advertises options `dxc` rejects

`dxc --help` prints a `Rewriter Options:` section listing `-remove-unused-globals`,
`-extract-entry-uniforms`, `-rewrite`-adjacent options and so on. `dxc.exe`
rejects all of them (`Unknown argument`). The options carry `RewriteOption` in
`HLSLOptions.td` and are only in the accepted mask for the rewriter entry points,
while `--help` dumps the whole table.

Triage impact: **do not infer the instrument from `--help`.** Confirm by running
the option and checking it is accepted. Captured here as
`manual-case-dxc-help-surface.txt` + two `variant-dxc-rejects-*` runs.

## 6. `bisect` correctly refuses a non-`dxc` harness, and there is a gap behind it

`is_dxc_binary()` returns False for `dxr.exe`, so `refuse_harness_bisect` hard-errors
rather than silently substituting each release's `dxc.exe` - which would have run a
different program and produced a confident, meaningless table. Good guardrail; it
worked exactly as intended.

The gap: everything after the refusal had to be rebuilt by hand
(`measure.py`, ~400 lines) - release iteration, staging, per-release controls,
scoring, redaction, verbatim excerpting. Most of that is generic.

**Suggestion:** let `compiler --id X --exe <path>` record a `history_mode`. For
`dll-swap`, `bisect` would keep the registered executable fixed, stage it beside
each release's `dxcompiler.dll`, and otherwise behave normally. That covers `dxr`,
`dxopt`, `dxa`, `dxv` and any future harness in one change, and would make
rewriter/PIX/validator issues first-class instead of bespoke. Scoring already
works - `measure.py` gets correct verdicts purely by importing
`triage.classify`, which is a good sign the seam is in the right place.

## 7. Small tooling frictions

- `run --expect` accepts only `{match, no-match, invalid-probe}`, while `run`
  *reports* `{repro, no-repro, invalid-probe}`. Mapping `match`->`repro` is
  obvious in hindsight but cost a wrong declaration and an `expect` correction.
  Accepting `repro`/`no-repro` as aliases would remove the trip hazard.
- `audit` wants a tool-made `variant-*.txt` for every `.hlsl` in the issue
  directory. That is a good rule, but it also applies to `.hlsl` files that are
  *generated artefacts* rather than inputs - `rewritten.hlsl` here is the
  rewriter's own output, kept byte-identical on purpose. It was given a real
  capture (compiling it with `dxc`), which is genuinely useful, but a directory
  that generated many such artefacts would fight the rule.
- Binary artefacts (`.dxo`) must be written to `.cache/`, which is gitignored,
  not to the issue directory. Easy to do by accident when a step needs a
  container to feed `dxa -dumpreflection`.

## 8. Reading the thread mattered more than the repro

The title is a question ("How to remove unused cbuffer?") and the issue is
labelled `enhancement`. The decisive content is a maintainer comment three weeks
later that answers the question *and converts the issue in place* -
"Let's consider this issue a feature request..." - followed by the reporter
agreeing. A triage that reproduced the symptom and stopped would have reported a
`bug`-shaped finding for an issue that was settled as an accepted enhancement in
2022.

The general rule: on question-titled issues, **the last maintainer comment is
part of the evidence**, and the suggested action often follows from it rather
than from the compiler. `enhancement-not-bug` was the right outcome here, and the
compiler work's job was to confirm the position is still accurate four years
on - which is a real contribution, just not the headline one.

## 9. Checking the reporter's stated *harm*, not just the stated symptom

The reporter gave a motivation ("wasted register slot ... overflow the limit of
cbuffer slot(15 in dx11)"). That is a separate, checkable claim from the symptom,
and checking it took four commands: compile the rewriter's own output and read
the binding table and reflection. Result: on the DXC/SM6 path the retained block
consumes nothing.

Two disciplines this needed:

- **State the scope of what was not tested.** DX11/SM5.x is FXC, a different
  compiler; the measurement is silent about it, and the write-up says so
  explicitly rather than letting the reader over-read it.
- **Do not turn it into a rebuttal.** The finding is context for prioritisation;
  the maintainer accepted the request on source-cleanliness grounds that this
  does not touch. Presented neutrally in both `notes.md` and `comment.md`.

Worth generalising: when a reporter states a *consequence*, it is often cheaper
to measure than the symptom itself, and it is frequently the thing a maintainer
actually wants to know when prioritising.
