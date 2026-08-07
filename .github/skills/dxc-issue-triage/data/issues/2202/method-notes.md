# Method observations from triaging #2202

Recorded here rather than acted on, per the single-writer rule. Collation decides whether
any of these belong in `SKILL.md` or `triage.py`.

---

## 1. `invalid-probe` detection only looks backwards in time; the same trap fires forwards

**How I hit it.** #2202's command as filed is `dxc -E ps_main -T ps_6_0 test.hlsl`, no `-HV`.
Run verbatim against `main-debug` today it gives:

```
repro.hlsl:11:33: error: condition for short-circuiting ternary operator must be scalar,
                         for non-scalar types use 'select'
[exit] 2147500037
```

The compile stops in Sema; the DXIL validator — the thing the issue is about — never runs.
`classify()` scored it **`no-repro`**. Had I left `cmd.txt` as filed, the linear scan would
have reported a clean fix somewhere around the release that changed the default `-HV`, and
the issue would have been recommended for closing. Pinning `-HV 2018` makes every release
from v1.4.1907 to `main` reproduce.

**Why the existing check misses it.** The `unsupported` regex in `classify()`
(`invalid profile`, `use of undeclared identifier`, `unknown type name`, `no member named`,
`no matching function for call to`, …) is built entirely from the *old release lacks a new
feature* direction — #3873's `ps_6_7`, #3038's `RayQuery`. This is the mirror image: a
**newer default rejects older-language source**. Every existing marker is a "you used
something that does not exist yet" message; this is a "that spelling is no longer allowed"
message, and none of them match it.

SKILL.md's prevention rule — *"target the repro at the oldest profile and flag set that still
shows the symptom"* — does cover this in spirit, but it is phrased entirely in terms of
profiles and flags. The language version is a third axis, it is **implicit** (there is no
`-HV` on the command line to notice), and its meaning silently changed under an eight-year-old
issue. Any issue filed before ~2022 whose repro uses HLSL-2016/2018-only spellings has this
problem, and the affected constructs are common: vector-condition `?:`, `matrix`/`vector`
truncation rules, `printf`, bitfield and initializer-list behaviour.

**Suggestions for collation, in increasing order of intrusiveness:**

1. Add the HLSL-2021 migration diagnostics to the `unsupported` regex, e.g.
   `condition for short-circuiting ternary operator must be scalar`, and more generally
   `for non-scalar types use 'select'`.
2. Add a sentence to step 3/step 6 naming `-HV` explicitly: *for issues filed before HLSL 2021
   became the default, pin `-HV` to what the reporter's compiler defaulted to, and keep the
   as-filed line in `cmd-as-filed.txt`.*
3. Cheap generic backstop: for an issue whose predicate is a **codegen or validation** symptom,
   a probe that produced **no DXIL at all** cannot be a clean run. `run` could warn when a
   `no-repro` probe has a non-zero exit and empty stdout.

---

## 2. A `no-repro` that is actually an internal failure is not detected — and it faked a fix window

**How I hit it.** `bisect --linear` reported:

```
result: non-monotonic history, transitions at v1.8.2403 -> no-repro, v1.8.2403.1 -> repro
```

`out-v1.8.2403.txt` is:

```
[exit] 3221225477
Internal compiler error: access violation. Attempted to read from address 0x00000000000000B0
```

`3221225477` = `0xC0000005`. That release does not fix the bug, it **crashes on it** — the
one behaviour strictly worse than the reported symptom, scored as the absence of a problem.

**Why the existing check misses it.** `classify()` reclassifies an internal failure as
`invalid-probe` in exactly one situation:

```python
if verdict == "repro" and _is_absence_predicate(...) and (unsupported or is_internal_failure(...)):
    return "invalid-probe"
```

— i.e. only for a `repro` under an *absence* predicate. A **`no-repro` that crashed** is
never reclassified, for any predicate kind. SKILL.md's `internal_failure` guidance is all
about not *missing* a crash when the crash is the reported symptom; this is the case where
the crash is **not** the reported symptom, and it silently converts a probe that proves the
compiler is broken into a probe that reads as "clean".

This one is dangerous in the same direction as the `nonzero_exit` trap SKILL.md already warns
about, but inverted: instead of inventing a bug, it **erases** one, and it does so at exactly
the point where the output is a release boundary someone will act on. Note that `--linear`
found it and a binary `bisect` would not have: both endpoints agreed, so the plain bisect
short-circuited to `always-repro'd` and never opened the file. `always-repro'd` happened to
be the right answer, but for the wrong reason.

**Suggestion:** in `classify()`, treat `verdict == "no-repro" and is_internal_failure(...)`
as `invalid-probe` unconditionally. If a text predicate did not match *because the compiler
died*, nothing was measured. I did not make the change (single-writer rule), and note it
would be applied retroactively to every past batch by `reindex`, which is presumably the
point — but it should be a deliberate decision, since some issues' predicates may currently
be resting on it.

---

## 3. `--match` on a primary run silently replaces the primary predicate's probes

SKILL.md step 5 shows `run --issue <N> --match match-crash.json` as the way to add a second
predicate, and step 4 says to bisect each separately. But with no `--label`, `execute()`
writes to `out-<compiler>.txt` — the *same* file the primary predicate's probe uses — with
`# match: match-crash.json` in the header, and `reindex` re-scores each `out-*.txt` using the
match file named in its own header. So `bisect --issue N --match match-crash.json` would have
overwritten all 20 of my primary probes and left the issue with no captured evidence for the
predicate its verdict rests on. Nothing warns about this.

I worked around it by putting the second predicate on **labelled variants** only
(`variant-crash-signature-<compiler>.txt`, with `--expect match` / `--expect no-match`), which
turned out better anyway: `reindex` re-checks declared expectations forever, so
"v1.8.2403 crashes, v1.8.2403.1 and `main` do not" is now a permanent assertion rather than a
sentence in `notes.md`.

**Suggestion:** either give `execute()` a per-match output name (`out-<compiler>-<match>.txt`)
or have `run`/`bisect` refuse a non-default `--match` without a `--label`. Also worth noting:
`--label` currently *requires* `--shader` or `--args`, so labelling a run of the unmodified
repro means retyping `cmd.txt`'s arguments — which is itself a drift risk, since the retyped
string is not re-checked against `cmd.txt` the way `out-*.txt` is.

---

## 4. The per-issue worker cannot make `reindex` clean, by construction

`audit_issue()` reports `verdict.json has no reviewed_by -- the independent review is
mandatory and left no trace (step 10)` for any issue that has a verdict. But SKILL.md's own
phase table puts step 10 in **collate**, not in the per-issue phase, and my brief explicitly
said to skip it. So a correctly-executed per-issue session *must* end with `reindex` reporting
a gap, and the instruction "run `reindex` and confirm it reports no missing evidence" cannot
be satisfied without either fabricating a `--reviewed-by` value or doing work assigned to
another phase.

I left `reviewed_by` unset rather than invent one, since SKILL.md is explicit that an empty
`reviewed_by` is the only way a skipped review is visible later — filling it in would destroy
the very signal the check exists for.

**Suggestion:** have `audit_issue()` distinguish *not yet reviewed* from *review skipped* —
e.g. only demand `reviewed_by` when the issue is attached to a batch whose report exists, or
downgrade it to a separate "pending collation" list so a per-issue worker has a reachable
clean state.

*(Follow-up: the instruction to run `reindex` at all was withdrawn mid-batch for an unrelated
and more serious reason — see note 6. Note 4 still stands as a description of `audit_issue()`,
and remedy 3 in note 6 — a read-only `audit --issue N` — would resolve both notes at once.)*

---

## 5. Minor: `godbolt` accepts duplicate compiler ids, and that is very useful

`--compilers "dxc_trunk,dxc_trunk:<other args>"` produces two panes of the same compiler with
different arguments, because `cmd_godbolt` builds a list of `(id, args)` tuples rather than a
dict. That is what let the link show the validation error and the `-Vd` disassembly that
explains it side by side — the difference between reproducing the bug and making it visible.
It is not mentioned in SKILL.md and reads like an accident; worth documenting as supported
before someone "fixes" it into a dict.

---

## 6. `reindex --reset` defaults to **True** — a bare `reindex` wipes the shared database

Found the hard way during the first parallel batch (`batch-004`). My brief instructed me to
finish with `python scripts/triage.py reindex` as a completeness check; the orchestrator
withdrew that instruction mid-flight, after I had already run it **four times** (~01:10-01:14
UTC). Recording it here while it is fresh rather than reconstructing it later.

**The mechanism**, read from the source rather than inferred:

```
scripts/triage.py:1487   s.add_argument("--reset", action="store_true", default=True,
scripts/triage.py:1488                  help="clear issues and runs first (default)")
scripts/triage.py:1489   s.add_argument("--no-reset", dest="reset", action="store_false")

scripts/triage.py:1344   if a.reset:
scripts/triage.py:1345       c.executescript("DELETE FROM issues; DELETE FROM runs;")
```

`action="store_true"` combined with `default=True` means the flag can only ever be *on* — so
a bare `reindex`, with no arguments at all, unconditionally executes
`DELETE FROM issues; DELETE FROM runs;` and rebuilds from whatever happens to be on disk at
that instant. `--no-reset` exists (line 1489) but appears in **neither** `SKILL.md` nor
`README.md`, and is not shown by any usage example. Nothing in the command's name, its
`help` text ("rebuild the local database from the committed evidence tree"), or the docs
suggests that running it is destructive to anyone but yourself.

**Why it collides with the documented workflow.** SKILL.md is internally inconsistent about
who may run this:

- `SKILL.md:46` assigns `reindex` to the **collate** phase, and `SKILL.md:63` says
  "Collation runs `reindex` before writing anything" — correct, and safe, because collation
  runs after all workers have stopped.
- But `SKILL.md:159` and `README.md:92` present a bare `python triage.py reindex` as ordinary
  setup ("after a fresh clone: rebuild db from data/"), and `SKILL.md:168` / `README.md:101`
  ("`reindex` is a regression test over every past batch") actively encourage running it.
  `README.md:98` describes the reset benignly as "`reindex` restores issues and runs".

Nothing warns that the operation is global, or that it is unsafe while other sessions are
writing. A per-issue worker following the docs will run it, and under parallel execution that
deletes rows other workers are mid-way through writing, producing duplicate or missing run
rows in *their* view.

**What is and is not at risk.** Worth being precise, because the blast radius is narrower
than it first looks:

- **Evidence is safe.** `reindex` only *reads* `data/`; the `out-*.txt` / `variant-*.txt`
  captures and `verdict.json` are written by `execute()` and `cmd_verdict()`, never by
  `reindex`. The files on disk are the source of truth and they were untouched.
- **The database is derived** and can be rebuilt authoritatively once every worker stops, so
  nothing is permanently lost.
- **Other workers' in-flight rows are not safe**, and neither is the reindex *report* itself:
  the gaps it printed for #2188, #8527 and #8737 during my runs were simply other workers'
  work-in-progress, not defects. A worker who trusted that output would be reading a
  misleading picture of a batch that is still moving under them — including, potentially, of
  their own issue.

**Suggestions for collation.** Any one of these would have prevented it; the first is the
smallest:

1. Make the reset **opt-in** — `--reset` as a genuine `store_true` defaulting to `False`, or
   rename it `--rebuild`. The current signature is arguably just a bug: an argparse flag that
   cannot be turned off by its own name is not doing what it reads as doing.
2. Give `reindex` the same lock `ensure_release` already uses for the release cache, so
   concurrent sessions serialise instead of interleaving.
3. Add a **read-only per-issue audit** — e.g. `triage.py audit --issue N` — running exactly
   the `audit_issue()` completeness checks against the evidence tree without touching the
   database. That is all a per-issue worker actually needs, and it removes the reason to
   reach for `reindex` at all. It would also fix note 4 above, since a per-issue audit need
   not demand `reviewed_by`.
4. Align `SKILL.md` and `README.md` so the per-issue phase is never told to run it, and mark
   the setup-time example as collation/bootstrap only.

I substituted a manual completeness self-check for the withdrawn `reindex` step (artifact
presence, header integrity on all 36 captured probes, `--expect` on every variant, and a
quoted-claim audit). It caught two real defects that `reindex` would **not** have caught —
see note 7 — so the substitution was not merely a safe fallback.

---

## 7. The check that matters most is "does every quoted number exist in a file?", and no tool does it

`reindex` verifies that captured probes still score the way they did, and that required
artifacts exist. It cannot verify the direction that actually goes wrong in practice: a
number that appears in `notes.md` or `comment.md` and *nowhere else*, because it was measured
by hand in a shell and never written down.

Doing that audit by hand for #2202 caught two, both of which had survived every automated
check:

1. `notes.md` claimed `-HV 2016` and `-HV 2017` reproduce. True, but measured in an
   exploratory `foreach` loop in PowerShell and never captured. Fixed by re-running them as
   labelled variants (`variant-hv2016-main-debug.txt`, `variant-hv2017-main-debug.txt`) with
   declared `--expect`.
2. The ground-truth `dxc --version` string — quoted at the top of `notes.md` and in
   `comment.md` as the basis for the entire verdict — existed only in my terminal scrollback.
   Fixed by `manual-case-version.txt`.

The second is the sharper lesson: the *most load-bearing measurement in the whole triage*,
the one that establishes which compiler was being measured, was the one with no file behind
it, precisely because verifying it is step 0 and feels too obvious to record.

Capturing it also surfaced something I would otherwise have missed. The working tree's `HEAD`
is `f8220ace`, **three commits after** the `eff900d5` the compiler was built from — so
`git rev-parse HEAD` is *not* a valid way to identify the compiler under test, and a triage
that recorded HEAD instead of `dxc --version` would have mislabelled its own ground truth.
Here it was benign (all three commits are confined to
`.github/skills/dxc-issue-triage/`, `eff900d5` is an ancestor of `HEAD`, and the two DXC
source files I cite are byte-identical across the range — all checked and written to
`manual-case-version.txt`), but it will not always be, and the triage workspace living inside
the repository it measures makes the drift routine rather than exceptional.

**Suggestions:**

- Have `verdict` record the ground-truth `dxc --version` output automatically into
  `verdict.json` (it already takes `--triaged-with-commit`, which is the operator's *claim*
  about the compiler; the version string is the compiler's own account of itself, and the two
  can disagree).
- Add to SKILL.md's "Evidence or it didn't happen" section the specific failure mode: an
  exploratory shell loop is a measurement, and if you quote its result it must be re-run
  through `run --label` so a file exists. "I already know the answer" is exactly when it does
  not get captured.
- Consider a `reindex`/`audit` check that greps `notes.md` and `comment.md` for fenced code
  blocks and flags any line not found in some captured file. Crude, but it would have caught
  both of mine.
