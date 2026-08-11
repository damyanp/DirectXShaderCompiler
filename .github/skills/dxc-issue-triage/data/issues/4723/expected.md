# #4723 — expected symptom (written before running anything)

**Issue:** "Support -M depfile generation flags during -P preprocess to file"
(<https://github.com/microsoft/DirectXShaderCompiler/issues/4723>), filed 2022-10-12 by
`ScatteredRay`, 0 comments, labels `bug` + `high-impact`.

## What the report actually says

Whole body, paraphrased with nothing added:

> We use `-M` (as covered in #2063), but our build process also runs DXC with `-P` to
> preprocess the file. It'd be great if `-MD` and `-MF` were supported when running DXC in
> `-P` preprocess-only mode.

Two things follow from that wording and matter for how this is scored:

- It is written as a **request** ("It'd be great if..."), not as a defect report. There is no
  command line, no shader, no quoted output, and no claim that anything crashes or
  miscompiles. Repro quality from the issue alone: **prose-only**; anything runnable here is
  **agent-constructed**.
- It presupposes that `-M`-family depfile generation *does* work in DXC on its own (#2063,
  closed 2021-12-21, asked for exactly that). The claimed gap is the **combination** with
  `-P`, not the flags themselves.

## Asks, decomposed (scored separately)

| # | ask | "reproduces" (i.e. the gap is still there) means |
| --- | --- | --- |
| A1 | `-MF <path>` honoured during `-P` | dxc run with **both** `-P` and `-MF dep.d` does **not** write `dep.d` |
| A2 | `-MD` honoured during `-P` | dxc run with **both** `-P` and `-MD` does **not** write a default-named depfile |
| A3 | the preprocessed output is still produced | if a depfile *is* written, the `-P` output must still be written too — one mode silently displacing the other is still the reported gap, in a different shape |

## What "still reproduces" is, concretely

The subject is **flag handling and file output**, so the observable is the *set of files the
run produced* plus the exit status — **not** DXIL, not stdout text from a compile. A verdict
here rests on:

1. `-P` alone writes the preprocessed file (baseline: the mode the reporter is in works).
2. `-MF dep.d` **without** `-P` writes `dep.d` containing a dependency list (baseline: the
   flag itself works, so the combination is what is being tested).
3. `-P` **plus** `-MF dep.d`: is `dep.d` written? Is the `-P` output written? Both? Neither?

**Reproduces** = case 3 fails to produce the depfile while case 2 produces it.
**Changed behavior** = case 3 produces the depfile but drops the preprocessed output (or vice
versa), i.e. the modes are mutually exclusive rather than the flags being unsupported.
**Does not reproduce** = case 3 produces both artifacts, the depfile listing the includes.

## Traps I must not fall into (pre-committed)

- **Exit 0 proves nothing.** DXC silently ignores unrecognised `/`-style flags, and an
  unsupported `-M` combination could equally exit 0 having done nothing. The verdict must rest
  on the depfile existing and containing a dependency list, never on the exit status alone.
  Symmetrically, a nonzero exit is *not* a crash: E_FAIL (0x80004005) is the ordinary
  diagnosed-error status.
- **Argument quoting is part of the subject.** The repro must be driven through `cmd.exe`, not
  PowerShell, so nothing re-quotes or re-splits the command line under me.
- **`-P` itself may have changed.** DXC historically spelled this `-P <outfile>`; the value
  vs. `-Fi` spelling has moved at least once while this issue has been open. I must establish
  what `-P` does on the ground-truth build *first* and not assume the 2022 spelling still
  holds — and, for history, must probe the spelling each release actually accepts.
- **A depfile is only interesting with `#include`s**, so the repro is multi-file. Compiler
  Explorer is single-file; if it cannot express this, record a `--skip` reason rather than
  publishing a link that cannot show the symptom.
- **Prove the flag is parsed at all** before concluding it is "supported": an option that is
  silently discarded and an option that is honoured both exit 0. Point `-MF` at an unwritable
  path, and/or check `-help`, so there is positive evidence the driver parsed it.

## Expected outcome (prediction, to be falsified by measurement)

If `-M`/`-MD`/`-MF` are simply not wired into the `-P` path, this is an **enhancement**, not a
bug, and `always-repro'd` would be a misleading way to describe "never implemented". If instead
the flags exist independently and only the *combination* misbehaves — e.g. one mode silently
wins and the other artifact is dropped, with no diagnostic — that is a materially different,
more actionable finding and should be reported as such. I do not yet know which.
