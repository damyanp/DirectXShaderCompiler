# Issue 4721 — "Support applying clang fix-its automatically"

Written **before** running anything. Batch batch-017.

Filed 2022-10-12 by llvm-beanz (Chris B), label `hlsl-next`, one comment (2023-06-30, same
author): *"This should be included in HLSL 202x support to aid developers in adopting new
syntaxes to replace removed ones."* No cross-reference events on the timeline.

## Shape of the issue

This is a **feature request**, not a bug report. Nothing is claimed to be broken, no output is
quoted, and there is no reporter-supplied repro. So:

- the right verdict shape is `enhancement-not-bug`, not `close-fixed` / `still-valid-keep-open`
  applied to a defect;
- `always-repro'd` would be **the wrong history value and actively misleading**. It says "a
  defect was present in every release we can check". A capability that was never implemented
  is not a defect that always reproduced. The honest short value is **`never-implemented`**,
  and if measurement shows a piece of it *is* implemented, the value must say so instead.
- repro quality is `none` as filed; anything I run is `agent-constructed`.

## What is actually being asked (decompose — three asks)

1. **`-fixit`** — a driver flag that applies fix-its to the input file, overwriting it.
2. **`-fixit=<suffix>`** — the same, writing a new file with the given extension instead.
3. **HLSL rewriters apply fix-its automatically** — i.e. `dxr.exe` / `IDxcRewriter`, "as that
   will extend their utility".

Score each separately. A single yes/no across the three would hide the interesting case where
part of the machinery is already there.

## The question worth measuring

Not "does it still reproduce" — there is nothing to reproduce. The measurable question is
**what the current state of the capability is**, which decomposes into four sub-questions.
DXC is a Clang fork, so all four are real possibilities and the answers are not guessable:

- **Q1 — hints.** Does DXC's Sema attach `FixItHint`s at all, and does its diagnostic printer
  *render* them? (In clang the rendering is the suggested-replacement line under the caret.)
  If yes, the request is "apply the hints we already compute", which is much smaller than
  "add fix-it support".
- **Q2 — machinery.** Are `FixItRewriter` / `FixItAction` (the code that consumes hints and
  writes a corrected file) present in the DXC tree and actually built, or were they stripped
  when the clang driver was removed?
- **Q3 — reachability.** Can *any* spelling reach it from `dxc.exe`: `-fixit`, `-fixit=hlsl`,
  `/fixit`, `-Xclang -fixit`? A `-Xclang`-reachable implementation would shrink the request
  from "add a feature" to "expose an existing one at the driver level".
- **Q4 — rewriters.** Does `dxr.exe` / the rewriter API apply fix-its today (ask 3)?

## Predicates and what each result means

**Primary `match.json` — "the driver does not accept `-fixit`".** Positive presence predicate:
the output must contain an unknown-argument diagnostic naming `fixit`. Presence, not absence,
so a failed parse cannot satisfy it for free.

- match ⇒ ask 1 is unimplemented at the driver (the symptom of the request).
- no-match ⇒ either the flag is accepted (feature present) **or** it was silently swallowed.
  Those are different and must be told apart — see the trap below.

**`match-hint.json` — "DXC renders a fix-it hint".** POLARITY INVERTED relative to the
primary: a *match* here means the capability is **present**. Anchored on a real diagnostic plus
the rendered replacement text, so a compile that never started cannot produce it.

## Controls (every predicate gets one, and it must not match)

- `variant-no-fixit-flag` — the identical command with `-fixit` removed: must **not** produce
  an unknown-argument diagnostic (`--expect no-match`). Proves the primary predicate is not
  matching everything, and that the rest of the command line is well-formed.
- `variant-clean` — a valid shader with no typo: must **not** match `match-hint.json`
  (`--expect no-match`). Proves the hint predicate is not satisfied by any successful compile.
- **`/`-style trap control.** Unrecognised `/`-prefixed flags are *silently ignored* by dxc —
  `/ZZZNONSENSE` can exit 0. So a clean exit from `/fixit` proves nothing whatsoever. I must
  run `/fixit`, `/ZZZNONSENSE` and no flag on the same valid shader and compare the produced
  artifact **byte-for-byte** (SHA-256). Identical hashes ⇒ the flag was ignored, not honoured.
  Correspondingly, for the `-`-spellings, a flag only counts as "parsed" if I can make it fail
  or see it in `-help`; exit status alone is not evidence in either direction.

## Predicted outcome (to be confirmed or refuted by measurement)

Stated so it can be scored against, not to be rationalised into: I expect `-fixit`,
`-fixit=<suffix>` and `/fixit` all to be unavailable from `dxc.exe`. I do **not** know whether
DXC renders fix-it hints, whether `FixItRewriter` survives in the tree, whether `-Xclang`
exists in this driver at all, or what the rewriter does. Those four are the measurement.

## What would make this `does-not-repro`-shaped instead

If `-fixit` turned out to be accepted and to rewrite the file, the request is satisfied and the
action is `close-fixed`. If only part is reachable (e.g. via `-Xclang`), the action stays open
but the ask shrinks, and that shrinking is the finding to report.

## Out of scope / not measurable here

Whether fix-its *should* be added is a product decision, not a measurement. The Clang-based
HLSL front end is a separate compiler; if it has the capability that is evidence about the
successor, not about DXC.
