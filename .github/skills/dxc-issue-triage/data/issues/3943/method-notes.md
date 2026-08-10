# Method notes from triaging #3943

Observations about the *method and tooling*, not about the issue. Kept separate from
`notes.md` so a future batch can read them without reading the triage.

## 1. Putting the instrument self-test inside the scored predicate

The symptom here is a **compile error**, which makes the usual "did the probe even run?"
check useless: a failing compile is the signal. And `'inc/common.h' file not found` is an
ordinary diagnosed error, not one of `classify()`'s feature-absence markers, so an old
release that could not resolve `-I` would emit no redefinition, score a confident `no-repro`,
and manufacture a fix boundary out of nothing.

The fix used here: `cmd.txt` holds **two** invocations, and `match.json` is an `all_of` over
both — clause 1 requires DXIL from a same-spelling control, clause 2 requires the redefinition
from the repro. A `repro` verdict is then *arithmetically* impossible unless the self-test
passed, on every release, forever, including after any future `reindex`.

This generalises. Whenever the symptom is a diagnostic rather than a crash or a wrong value,
consider making the predicate a conjunction with a positive control. Prose in `notes.md`
saying "I checked the self-test" is not re-scored by `reindex`; a clause is.

## 2. The `.hlsli` trick, and why it is load-bearing

`retarget_cmd` (triage.py:925) rewrites argv tokens **ending in `.hlsl`**. With a two-line
`cmd.txt` that is exactly what you want — but only if the self-test file is *not* named
`.hlsl`. Hence `control-once.hlsli`.

If it were `control-once.hlsl`, every `run --shader <variant>` would rewrite *both* lines, so
each variant would overwrite its own self-test with the variant under test — and since a
reproducing variant emits no DXIL, clause 1 could never be satisfied and `--expect match`
would be unsatisfiable. The failure is silent and looks like a compiler result.

This is fragile enough that it is documented twice (in `cmd.txt` and in the file's own header
comment). A future reader "tidying" the extension would break the whole issue's evidence.

## 3. `VALUE_FLAG_ARITY` does not list `-I`

`VALUE_FLAG_ARITY` (triage.py:841-863) gives `option_arity("-I") == 0`, so `-I <dir>`'s
argument is treated as a positional token. Harmless here — `inc` is a directory and does not
end in `.hlsl` — but a `cmd.txt` containing `-I something.hlsl` would have its *include path*
silently retargeted by `--shader`. Worth adding `-I` (and `-D`, checked: also absent) to the
table, or at least worth knowing before writing a `cmd.txt` with include paths.

## 4. `run --args` is a single invocation and drops the self-test

`--args` replaces the whole command list, so on a multi-line `cmd.txt` it silently discards
the self-test line and scores against a one-invocation capture. The two `include-trace-*`
variants here are `--args` runs and compile cleanly, so clause 1 is satisfied by their own
output and `--expect no-match` is honest — but a `--args` capture of a *failing* command would
score `no-match` for a purely mechanical reason. Use `--shader` where a variant is a different
shader; reserve `--args` for variants that change flags, and check what the predicate then
sees.

## 5. Other `cmd.txt` / harness details worth writing down

- Comment lines must start at **column 0**: the check is `not ln.startswith("#")` against the
  *unstripped* line, so an indented `#` is parsed as arguments.
- `split_cmd` disables shlex escape processing, so `\` is a path separator and backslash paths
  in `cmd.txt` are safe. (This issue needs that: `control-separator.hlsl` exists to compare
  separators.)
- `_run_probe_command_list` copies the **whole issue directory** into a scratch tree, so
  subdirectories and headers travel with the probe automatically; no manifest is needed.
  Inputs named on the command line are hashed and mutation is a hard error.
- Each line runs as a **separate process** with `cwd` set to the scratch copy, so no
  preprocessor state leaks between the self-test and the repro. Good: the conjunction is two
  genuinely independent measurements.

## 6. The empty-directory trap, avoided by construction

The brief warned about it (an earlier issue's repro depended on a directory git cannot store,
so re-running it later failed with the real bug's exit status for an unrelated reason).

`expected.md` originally planned claim B as `#include "inc/sub/../common.h"`, which would have
needed an `inc/sub/` directory containing nothing. It was built as `inc/../inc/common.h`
instead — same `..` semantics, but every directory it traverses (`inc/`) already contains two
tracked headers. **Prefer a `..` that walks out of and back into a directory that must exist
anyway over one that requires a new, empty one.** More generally: after building a multi-file
repro, list the directories it touches and confirm each holds a tracked file.

**Verify it, don't reason about it.** The check that actually settles this: reconstruct the
directory from `git ls-files --others --exclude-standard` alone — i.e. exactly the bytes a
fresh clone would contain — into a scratch tree, and run `cmd.txt` there. Done for this issue;
the self-test exited 0 with DXIL and the repro produced the identical two-path diagnostic, so
the committed repro is runnable from the repo alone. It costs one command and it is the only
thing that distinguishes "I believe every needed file is tracked" from knowing it. Delete the
scratch tree afterwards or it becomes part of the next probe's copied input.

## 7. Independent re-measurement of the Compiler Explorer `#pragma once` fold trap

SKILL.md already warns (from #8527) that folding a multi-file `#pragma once` repro into a
self-including single file measures a different rule. This run re-measured it from scratch
before believing it, and the evidence is sharper than expected:

- CE masks the pane's real path as `<source>`, and `#include "<source>"` **cannot be
  resolved** — so no self-include fold runs there at all, in any spelling.
- DXC itself emits `warning: #pragma once in main file` — the compiler confirming that the
  main file is governed by a different rule.
- The fold's *known-good* control (the matched-spelling arm, which must reproduce nothing)
  fails identically, which is what proves the transformation invalid rather than merely
  unlucky.

The `godbolt --skip` recorded for this issue is therefore measured, not assumed, and
`ce-probe.py` regenerates `manual-case-ce-infeasible.txt` so a reader can re-derive it.

First-run defect in my own prober, worth repeating as a warning: the filename-extraction regex
matched too loosely and turned both fold arms into "inconclusive", which would have justified
the skip for the *wrong* reason. Fixed to `^(\S+):\d+:\d+:` and re-run. A tool you wrote for
one issue gets exactly as much scepticism as the compiler does.

## 8. `dxc -H` prints no include trace when the compile fails

`-H` on the reproducing shader emits the diagnostics and **no** `Opening file [...]` lines at
all, so it is not a usable witness on a failing compile. The trace evidence in this issue
therefore comes from `control-guard.hlsl` — the same two include spellings, but a header
guarded with `#ifndef` so the compile succeeds — which shows the two opens plainly:

```
; Opening file [./inc/guarded.h], stack top [0]
; Opening file [./inc\guarded.h], stack top [1]
```

Generalisable: when a `-H`/`-P`-style diagnostic mode goes quiet, check whether it is
suppressed by failure before concluding the thing it reports did not happen. Rearranging the
repro so the interesting event happens on a *successful* compile can recover the witness.

## 9. `check_paths.py` is batch-global, and *documenting* a leak re-creates it

Two lessons, the second one learned the hard way in this very file.

**The gate reports the whole tree, not your directory.** Under the parallel model a red
`check_paths.py` says nothing about your own work until you filter the output by path. Both
mistakes are live: reading another worker's hits as your own, and — worse — seeing a familiar
red gate, assuming it is the other worker's again, and missing a hit of your own. Filter first,
every time: `... | Select-String 'issues/<your number>'`.

**Writing a method note about a leaked path leaks the path.** The first draft of this section
named the offending file and quoted the offending prefix verbatim, so the very act of recording
the finding put a fresh absolute build path — drive letter and local checkout directory — into
a committable file, in my own directory, where the earlier run had found none. The gate caught
it on the re-run. When describing this class of problem, describe the *shape* of the path
rather than reproducing it, and never paste the detection pattern into prose.

Corollary that follows from both: **re-run the gate after the last edit, not before it.** My
first run was clean and was made several edits before I finished. A gate result is only valid
for the tree that existed when it ran.

For the record, at the end of this run the remaining hits are in two other issue directories,
both outside this worker's boundary and presumably still in flight; collation is handling them.
Nothing in `data/issues/3943/` is flagged, and no file here needs an `ALLOWLIST` entry — the
one hit was prose I wrote, not evidence.
