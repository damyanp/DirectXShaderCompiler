# Method notes — #4723

Observations for collation. Four are generalisable; the last one is a near-miss that cost the
best finding in the issue and would have cost it silently.

## 1. A head-only view of a produced file hides the defect at its tail

The harness originally printed the first 8 lines of every artifact it found. That is the wrong
end of a preprocessed file: the head is always `#line 1 "…"` and reveals nothing. The bug —
the dependency list being appended to the `.i` — lives in the last three lines, and for the
first half of this triage the conclusion on the table was the weaker "the flags do nothing
under `-P`".

What actually exposed it was a **size** comparison that was not part of any predicate: the
harness prints `bytes=` for each artifact, and `repro.i` came out at 354 bytes with `-MF` and
291 without — a 63-byte difference that happened to equal the exact size of the depfile the
compile-mode line had just written. Two numbers that should not have been related.

Generalisable rule: **when the observable is a produced file, report its size and both ends.**
Size is what makes an unexpected difference visible without knowing what to look for; the tail
is where anything appended lands. `dep4723.py` now prints `dep4723-content` (head) and
`dep4723-tail` (last 3 non-blank lines) for every artifact.

## 2. `%ERRORLEVEL%` inside a single `cmd` line is expanded at parse time

`cmd /c "dxc … & echo EXIT=%ERRORLEVEL%"` prints the status of whatever ran *before*, because
the whole line is expanded when it is parsed. Several minutes of exploration here recorded
confident, wrong exit codes from exactly this. It is not fixed by `&&` or by quoting; it needs
`setlocal enabledelayedexpansion` and `!ERRORLEVEL!`, or — better — capturing the status in
Python, which is what every script in this directory now does.

SKILL.md already says to capture exit status in Python. Worth adding *why*, because the failure
is silent and plausible-looking rather than an error.

## 3. A `.cmd` wrapper cannot carry an HRESULT out intact

Related but distinct. When the harness returned dxc's real status, the capture header read
`# exit: 4294967295` for a run whose true status was `0x80004005` — cmd mangled it on the way
out. `4294967295` reads like a crash; `0x80004005` is an ordinary diagnosed error, and the
distinction is exactly the one SKILL.md warns not to get wrong.

Fix: a harness-as-compiler should exit with a **small, documented** code (0 clean / 1 diagnosed
/ 3 internal-failure, derived in Python from `triage.INTERNAL_STATUS`) and print the real
status in the text as `dep4723-exit=0x%08X` plus a `dep4723-status=` classification. The
predicate reads the text, and nothing between Python and the capture can corrupt it. Reusing
`triage.INTERNAL_STATUS` rather than a local copy keeps the harness's idea of "crash" identical
to the runner's.

## 4. Absence as a positive line, and the anchor that goes with it

The symptom here is a missing file, and SKILL.md's rule is to make the instrument prove a
presence. Two halves, both needed:

- The harness prints `dep4723-artifact depfile-MF dep-preprocess.d MISSING` — a line that only
  exists because the harness ran, parsed the command line and looked. `not_contains "…\.d"`
  would have been satisfied by a run that never started.
- Every finding clause is a **two-line regex** whose second line is the adjacent
  `dep4723-artifact preprocessed-P … PRESENT bytes=\d+`. Without that, a `dxc` that failed
  outright would report MISSING and score as a reproduction.

The `-MD` clause has a property worth stealing: `repro.d` must appear **PRESENT in one
invocation and MISSING in another within the same capture**. A single capture that contains
both readings of the same filename cannot be satisfied by a build that simply cannot write
files, and cannot be faked by a stale artifact (the harness deletes each expected artifact
first and says so).

## 5. Probing a flag whose spelling changed leaves droppings — and one of them looked like data

`-P` was a Separate option taking the output filename until `8bf2b087c` (v1.7.2212), and a flag
paired with `-Fi` after it. A release sweep must try both spellings, which means deliberately
mis-parsing one of them on every release. On the old releases `-P -Fi new.i` consumes `-Fi` as
`-P`'s value and writes the preprocessed text **to a file literally named `-Fi`** in the issue
directory. It sat there looking like a legitimate 291-byte artifact.

`measure-history.py` now snapshots the directory before the sweep and deletes anything new it
left at the top level, and `.gitignore` covers it as well. Generally: **a compatibility sweep
should run each release in its own directory it created itself, and clean up what a mis-parse
produces** — an unexplained file in an issue directory is worse than no file, because the next
reader has to work out whether it is evidence.

## 6. `--label` requires `--shader` or `--args`, so a second predicate over the *same* command
list is a plain `run --match`

Scoring a second predicate against the full `cmd.txt` is not a variant and `--label` rejects it.
`run --issue N --compiler C --match other.json --expect match` writes
`out-<compiler>--<stem>.txt` alongside the primary capture without clobbering it, and accepts
`--expect`. Useful when one issue records two distinct defects from one run; `audit` counts it
as a capture rather than as a variant.

## 7. Two predicates for two defects, linked with `quote_from`

The reported defect (no depfile) and the one found while measuring it (the `.i` is corrupted)
are scored by separate predicates, so the verdict for the issue as filed does not depend on the
extra finding. Because the second predicate's evidence is a clang diagnostic containing
`unknown type name` — one of `classify`'s feature-absence markers — it quotes that text
verbatim in a positive clause, and the primary predicate carries `"quote_from":
["match-contamination.json"]`. Without the link, a capture containing the deliberate downstream
failure could be demoted to `invalid-probe` for containing evidence the predicate went looking
for. This is the documented use of `quote_from` and it applied cleanly.

## 8. Compiler Explorer skip

Recorded with a reason rather than forced. The observable is a set of files the driver writes
and the contents of a `-Fi` output; CE shows the compiled result of one translation unit and
cannot display either, and the repro needs two `#include`d headers that CE has nowhere to put.
A link here would show a compile that is not the thing under test — worse than no link, because
it looks like corroboration.
