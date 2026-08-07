# Method observations from triaging #2188

Recorded here rather than acted on, per the boundary rule: a per-issue session does not
edit `SKILL.md` or `triage.py`. Collation decides what, if anything, to promote.

---

## 1. A secondary `match-*.json` bisection would silently destroy the primary evidence

**Severity: high — this one can quietly delete committed evidence.**

SKILL.md, step 4:

> **An issue may need more than one predicate.** When the reported symptom differs from
> current behaviour, add e.g. `match-crash.json` and bisect each separately.

But `execute()` derives the output path from the *compiler* alone:

```python
out_path = os.path.join(
    d, f"variant-{label}-{compiler}.txt" if label else f"out-{compiler}.txt")
```

`match_file` appears only in the header (`# match:`), never in the filename. So
`bisect --issue N --match match-crash.json` **overwrites every `out-<tag>.txt` already
captured under `match.json`**, and `reindex` then re-scores the surviving files with
whichever predicate the *last* run happened to use. The primary predicate's history is
gone, and nothing reports it: file counts, `cmd.txt` staleness and `--expect` checks all
still pass, because each file is individually well-formed.

I hit this while planning, not while running — #2188's repro contains two independent
failure sites (a `groupshared` array bound and a `[numthreads]` argument), so the obvious
move was one predicate per site. I did not do it, for this reason.

**Workaround used instead**, which may be worth promoting on its own merits: run
`bisect --linear` once with the primary predicate, then grep the captured probes for each
sub-symptom. All 21 outputs are on disk, so a per-release table for *any* number of
sub-symptoms can be derived from a single scan, without re-running anything and without
overwriting anything. The derivation command is recorded in `notes.md` so it is
re-runnable.

**Possible fixes** (collation's call): include a non-default `match_file` stem in the
output name (`out-<compiler>--<match>.txt`), or refuse to overwrite a probe whose header
records a different `# match:`.

## 2. `reindex` defaults to `--reset`, so it destroys other workers' in-flight DB state

**Severity: high — it silently deleted a published Compiler Explorer link mid-triage, and
the destructive behaviour is the default, not an opt-in.**

The flag is declared `--reset`, `action="store_true"`, **`default=True`**
(`scripts/triage.py:1487`), with an explicit `--no-reset` to opt *out*. So a bare
`python scripts\triage.py reindex` — the form SKILL.md and the batch brief both ask for —
executes `DELETE FROM issues; DELETE FROM runs;` (`scripts/triage.py:1344-1346`) and
rebuilds from whatever `verdict.json` files exist at that instant.

This happened to #2188 during this session. Sequence:

1. `fetch --issue 2188 --batch batch-004` → sets `title`, `url`, `created_at`, `labels`,
   `batch` on the `issues` row.
2. `godbolt --issue 2188 ...` → verified and stored `godbolt_url`.
3. *A bare `reindex` ran* — mine or another worker's; see the correction below.
4. `verdict --issue 2188 ...` → `write_verdict_json` snapshots the DB row, which by then
   held **only the twelve fields I had just passed**. No title, no url, no batch, no
   `godbolt_url`.
5. `reindex` then reported `#2188: neither a Compiler Explorer link nor a recorded reason
   for skipping one (step 7)` — for an issue whose link had been published and verified
   twenty minutes earlier.

Any issue that does not yet *have* a `verdict.json` — i.e. every issue still being triaged
— loses all its row state, because `fetch` and `godbolt` write only to the database.
Confirmed by inspection at the time: every other issue in `data/issues/` came back with
title, batch and `godbolt_url` intact, and #2188 alone was blank.

**Correction to my own first write-up of this note.** I originally recorded step 3 as
"*some other process ran `reindex --reset`*", inferring that someone had passed the flag
deliberately. That inference was wrong in a way that matters: **nobody has to pass
anything.** I had myself run bare `reindex` at least four times during this session,
each of which wiped both tables — so I am as likely to have caused this as anyone, and I
may well have destroyed *other* workers' in-flight rows in the same way. A hazard that
requires an explicit destructive flag is a footgun; one that is the default behaviour of
the command the procedure tells you to run as a final check is a trap.

The orchestrator withdrew the instruction mid-batch on exactly these grounds, and
confirmed the database is derived data that will be rebuilt authoritatively once all
workers finish. Recording it here, as asked, so the record shows it was found during the
first parallel batch rather than reconstructed afterwards.

SKILL.md says the shared *cache* is safe to contend on and that a per-issue session never
writes shared state. Both are true and neither covers this: the **database** is shared
mutable state that every worker writes through `fetch`/`godbolt`/`verdict`, and reset is
a destructive operation on all of it.

The audit did catch the consequence, which is the system working. But the diagnosis is not
obvious from the message — it reads as "you forgot step 7", and the natural response is to
re-run `godbolt` (which is in fact the fix) or, worse, to record a `--skip` reason for a
link that exists.

**Recovery, if it happens again:** re-run `fetch`, then `godbolt` (the compiler spec is
reloaded from the issue's `godbolt.txt`, so the same link comes back — the CE shortener
returned the identical `z/nvqTPYffM` for identical content), then `verdict`. Order matters:
`verdict` writes `verdict.json` last and snapshots everything, after which a reset can
restore the issue.

**Possible fixes** (collation's call), roughly in order of how cheap they are:

- Flip the default: `--reset` should be opt-in, not opt-out. This alone removes the trap.
- Scope reset to a single issue, or refuse to run it when any issue directory lacks a
  `verdict.json` (i.e. when a triage is plausibly in flight).
- Have `fetch`/`godbolt` persist to `verdict.json` immediately rather than only at
  `verdict` time, so no state is DB-only.
- Take the same per-tag style lock around reset that `ensure_release` takes around
  downloads.
- Split the completeness audit out of `reindex` into a read-only `audit` subcommand.
  The audit is the genuinely useful part and it needs no write access at all; today you
  cannot get it without also rebuilding the database. See note 6.

## 3. A positive predicate cannot self-detect an invalid probe

`classify()` only downgrades to `invalid-probe` when the verdict is `no-repro`:

```python
if verdict == "no-repro" and unsupported:
    return "invalid-probe"
```

That is correct for the documented trap (a release rejecting an unknown profile scores a
false clean). But it means a **positive** predicate — here `nonzero_exit`, which is the
faithful reading of "doesn't compile with dxc" — scores an unsupported-feature rejection
as a *reproduction*. `invalid profile`, `use of undeclared identifier` and friends all
exit nonzero, so a release that never ran the repro would be counted as reproducing it,
and a `--linear` scan of a genuinely-fixed issue would report "always-repro'd".

SKILL.md warns thoroughly about the `no-repro` direction of this and not about this one.
The absence-predicate note is the closest analogue, and it also fires only in the other
direction.

I covered it by reading all 21 captured probes and confirming each contains the issue's
own diagnostics rather than a rejection — but that is discipline, not mechanism, and
SKILL.md is elsewhere explicit that a step depending on remembering to do it by hand is a
step that will be skipped. A `nonzero_exit`/`contains`-style predicate on a release that
also emitted an `unsupported` marker is at least worth a warning.

## 4. `reindex` cannot come out clean for an issue triaged in a parallel per-issue session

`audit_issue` requires `reviewed_by`:

```python
if not rec.get("reviewed_by"):
    gaps.append("verdict.json has no reviewed_by -- the independent "
                "review is mandatory and left no trace (step 10)")
```

Step 10 is a **batch-level** step, run after the per-issue sessions by a different model,
so a worker following the phase table cannot satisfy it. Its `reindex` therefore always
reports at least this gap, which trains the worker to treat audit output as noise —
exactly the opposite of what the audit is for. (The alternative, passing `--reviewed-by`
to make it quiet, would be recording a review that did not happen; I did not do that.)

Options: exempt the `reviewed_by` gap when `verdict.json` has no `reviewed_by` *and* the
issue is in an open batch; or report it in a separate "pending collation" section; or say
plainly in SKILL.md that this one gap is expected at worker time.

This survives the withdrawal of `reindex` (note 2): the audit still runs at collation, and
whoever runs it there will see the same gap for every issue in the batch. It is only the
worker-time framing that goes away. It is also why my hand-rolled replacement (note 6)
does not check `reviewed_by` — a per-issue worker structurally cannot satisfy it.

## 5. Small: an issue whose repro is best shown against a *second* compiler has nowhere to
put that compiler's output

`triage.py run` runs a registered dxc. FXC is the whole point of an `fxc-disagrees` issue,
and CE is single-source, so I used a committed script (`run-fxc.ps1`) writing
`manual-case-fxc.txt`, which is what SKILL.md's naming rule implies. That worked well and
follows the #2427 lesson (compiler path from a variable, no hardcoded path), but the
`manual-case-*` convention is currently described only as "where the repro is not a `dxc`
invocation at all". A sentence covering "or is a different compiler, run for contrast"
would make the choice obvious rather than inferred.

Likewise `godbolt` prints only the first output line per compiler, which is not enough to
satisfy SKILL.md's own demand for a Clang control (`exit=0` alone does not show whether
`-T`/`-E` were honoured). I captured the full panes with `run-ce.py`, importing
`triage.py`'s `ce_compile`/`annotate` so the capture matches the published link exactly. A
`--capture`/`--full` flag on `godbolt` would make this the easy path.

## 6. Replacing the withdrawn `reindex` check with a per-issue self-check

Because `reindex` was withdrawn (note 2), I did its completeness audit by hand, as
`selfcheck.ps1` → `selfcheck.txt` in this directory: 45 assertions, read-only, touching
nothing outside `data/issues/2188/`. It checks the artefacts SKILL.md requires, that every
compiler probed left a capture with an exit code, that every variant declared an
expectation, and — the part that matters most — that **every measurement quoted in
`notes.md` and `comment.md` resolves to a file on disk**, by grepping the artefact for the
exact string the write-up claims.

That last class of check caught a real gap that `reindex`'s audit does not look for and
that I had missed: my source corroboration (`const-expr.hlsl:379-382`, `attributes.hlsl:659`,
`SemaType.cpp:2144`, `SemaHLSL.cpp:13889/14816`) was quoted from the working tree with **no
captured artefact**. Worse, the working tree had moved on — `HEAD` was `f8220ace4` by the
time I checked, while the ground-truth compiler was built from `eff900d54`, so a stranger
following those line numbers later could silently read different code. Fixed by capturing
`manual-case-source.txt` with every excerpt pinned via `git show eff900d5:<path>`.

Two things worth promoting from this:

- **Line-number citations are measurements too.** SKILL.md's "evidence or it didn't happen"
  is framed around compiler output, and I read it that way. Source citations decay faster
  than compiler output does, because the tree moves under you; they should be captured and
  pinned to the triage commit, not just referenced.
- A per-issue self-check is a better fit for a parallel batch than a global one anyway:
  it needs no database, cannot interfere with another worker, and can assert things a
  global audit cannot, because it knows what this issue's write-up actually claims.


## 7. Worked as documented

- The `expected.md`-before-running rule paid off concretely. I predicted before running
  that `static const uint eight = 8; [numthreads(eight, 8, 1)]` would fail, because
  cross-referenced #2191 says it asserts. It compiles cleanly. Had I run first, that would
  have been an unremarkable observation instead of a flagged surprise.
- Declaring `--expect` on exploratory variants surfaced that wrong prediction as a loud
  `WARNING` at the moment it happened. I re-ran with the corrected expectation so
  `reindex` stays clean, and recorded the wrong prediction in `notes.md` — otherwise
  re-running to fit the result would erase the finding. SKILL.md might say that explicitly:
  **correct the `--expect`, but write down what you predicted.**
