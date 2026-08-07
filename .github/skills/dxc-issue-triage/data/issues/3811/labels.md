# #3811 — label review (recorded, never applied)

`python scripts\triage.py labels --issue 3811` output:

    #3811 now:      validation
    #3811 proposed +incorrect-code, diagnostic, check-in-clang -

Nothing was applied. This is a suggestion for a maintainer, read off the label
**descriptions** in the repo taxonomy against the evidence in `notes.md`.

The issue has **0 comments**, so there is no maintainer position these proposals
could be contradicting — and equally no history to lean on.

## Keep

- **`validation`** — "Related to validation or signing".

  This label is narrower than it sounds: it means **DXIL validation**, not "the
  compiler ought to validate this". It is easy to assume an issue titled "no
  error/warning" was mislabelled by someone reaching for the second meaning.
  Here the narrow reading is the correct one, and the source settles it:

  - the diagnostic the reporter contrasts against is
    `ValidationRule::InstrNoReadingUninitialized`, emitted from
    `lib/DxilValidation/DxilValidation.cpp` — the DXIL validator, not Sema;
  - the straight-line spelling fails with `error: validation errors` /
    `Validation failed.` and exit `0x80004005`
    (`variant-straightline-main-debug.txt`);
  - the single line that lets the loop through is one line of that same rule:
    `bool LegalUndef = isa<PHINode>(&I);`.

  So the whole issue is about the behaviour of one DXIL validation rule.
  **Keep, unchanged.**

## Proposed additions

- **`incorrect-code`** — "Issues relating to handling of incorrect code".
  Exact fit. The shader *is* incorrect (an `out` parameter accumulated into
  before it is written), and the entire issue is about how DXC handles that
  incorrect code — rejecting one spelling and accepting another. Because the
  source reads an uninitialised value, its emitted output is evidence of the
  validation gap, not evidence of a miscompile.

- **`diagnostic`** — "Issues for diagnostics". The reporter's ask is a
  diagnostic that is not emitted. Worth adding *despite* the 2023 warning,
  because the warning does not cover the defect: `-Wparameter-usage` is
  parameter-specific, and `variant-local-uninit.hlsl` — the same loop over a
  local — is still completely silent on `main`
  (`variant-local-uninit-main-debug--match-silent.txt`: exit 0, no error, no
  warning, same undef-seeded phi). The diagnostics question is live.

- **`check-in-clang`** — "See if this repros in clang as well". The label reads
  as a to-do and the check is already done, which is the only reason I hesitated.
  Proposing it anyway, because the answer is a *positive* result that should be
  findable when the Clang front end is being built out: `hlsl_clang_trunk` emits
  the same undef-seeded phi feeding `fadd` and **no** uninitialised-value
  diagnostic — not for the loop case and not for the straight-line case either,
  so it has no equivalent of `-Wparameter-usage` at all
  (`manual-case-clang-control.txt`, three cases with controls;
  https://godbolt.org/z/57zn3j6YK). Caveat recorded in `notes.md`: the CE Clang
  pane stops before DXIL validation, so this is evidence about front-end silence
  only.

## Explicitly not proposed

- **`needs repro steps`** — "Cannot reproduce or don't have repro informations".
  The opposite is true: the body carries a complete repro, the exact command, and
  the reporter's own DXIL, and today's `define void @main()` is line-for-line
  identical to their 2021 paste (`manual-case-dxil-identity.txt`, 27/27). If
  anyone is tempted to apply this label after spot-checking and seeing the new
  warning, that is precisely the `text_stale` failure mode recorded in the
  verdict — the repro is fine, the *title* is out of date.

- **`crash`** — "DXC crashing or hitting an assert". Nothing crashes. The
  straight-line spelling returns `E_FAIL` (`0x80004005`) cleanly with a
  diagnostic; that is an ordinary diagnosed error, not an internal failure.

- **`bug`** — "Bug, regression, crash". Defensible, but the description bundles
  "regression" in, and this is provably not one: the PHI exemption dates to
  `6ee4074a4` (2016-12, the repository's first commit) and `match.json`
  reproduces on all 20 bisectable releases v1.4.1907..v1.9.2607. Not proposed,
  since `incorrect-code` and `diagnostic` say the same thing more precisely.

- **`hlsl-next`** — "Bugs for consideration on next language version". Whether
  reading an uninitialised value should be *ill-formed* in the language, versus
  caught by the validator or by a front-end warning, is exactly the design call
  I flagged for the team in `comment.md`. Not proposed, because choosing it would
  be pre-deciding that question on the maintainers' behalf.

- **`wont-fix`**, **`external`** — not my call, and no evidence supports either.

## Removals

None.

## Caveat

Label *history* is not in the fetched issue payload, so any of these may have
been considered and deliberately removed before. Treat all of the above as
suggestions from evidence, not as a claim that something is missing by mistake.
