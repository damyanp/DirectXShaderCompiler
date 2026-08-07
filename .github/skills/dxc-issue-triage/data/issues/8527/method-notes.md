# Method observations from triaging #8527

For collation to promote (or reject). Nothing here was acted on; `SKILL.md`,
`scripts/triage.py` and every other issue directory were left untouched.

---

## 1. Multi-file repros work, but nothing in the procedure says so

This is the first issue in the workspace needing more than one source file, and the
tooling handled it **without any change**: `execute()` runs with `cwd=<issue dir>`, so
`#include "x.hlsli"` resolves relative to the main file with no `-I` at all, and every
release probe and `--shader` variant inherits that working directory. Four files in
`data/issues/8527/`, one line in `cmd.txt`, and `bisect` worked first try.

Two details that had to be discovered by reading `triage.py` rather than `SKILL.md`, both
of which happen to be right:

- The completeness audit only demands captured output for `*.hlsl`, not `*.hlsli`
  (`audit_issue`, the `f.endswith(".hlsl")` filter). Headers are correctly treated as
  part of a repro rather than as unrun shaders. Had the convention been `.h`, the same
  would hold; had someone named a header `common.hlsl`, `reindex` would demand a probe of
  it.
- `retarget_cmd` replaces only the source operand, so a control that swaps one *header*
  needs its own main `.hlsl` — one per variant. That is a little verbose (this issue has
  six extra `.hlsl` files) but it keeps each variant differing from the repro in exactly
  one way, which is the point.

Suggested: a sentence in step 3 saying multi-file repros are supported, that paths resolve
relative to the issue directory so no `-I` is needed for same-directory headers, and that
extra headers should keep a `.hlsli`/`.h` extension so the audit does not demand probes of
them.

## 2. `godbolt` already warns about multi-file repros — the warning should be louder

`cmd_godbolt` prints `warning: repro references local file(s) [...]; CE is single-file, so
the link demonstrates only part of this issue` — but it prints it *and then publishes the
link anyway*. For #8527 the link would have been actively wrong, not merely partial. The
warning is checking `os.listdir` for `.h`/`.hlsli`, so it already knows enough to refuse,
or at least to require an explicit override.

Note it also fired on headers belonging to *variants* rather than to `repro.hlsl`, so it
over-reports once an issue has several controls. Listing only the headers reachable from
the published source would be more precise.

## 3. The trap this issue actually hit: a CE workaround that measures a different rule

**This is the finding worth promoting.** CE is single-file, so the tempting move for a
multi-file repro is to fold it into one file that includes *itself* under a different
spelling. It produces exactly the reported diagnostic — locally, on `dxc_1_6_2112`, on
`dxc_trunk` and on `hlsl_clang_trunk`. A link was built, verified per step 7, and looked
like a clean win, including what appeared to be a valuable new fact ("reproduces on Linux
too, so it is not about case").

It is wrong. `#pragma once` in the **main file** is ignored by design in clang — that is
what `-Wpragma-once-outside-header` warns about — so the second pass happens whatever the
spelling. Running the identical construction with a *matching* spelling produced the same
error and killed the demonstration.

The general shape: **when a repro is folded into a smaller form to fit a publishing
constraint, the fold itself needs a control.** Step 7 already says "never publish one
without checking it shows what you claim", and step 4's control discipline covers
predicates — but neither covers "the restatement reproduces, therefore the restatement
demonstrates the bug". The control that catches it is the same one step 4 prescribes:
change *only* the thing under test (here, the spelling) and require the symptom to
disappear. It did not.

Worth noting how close this came to publishing: the CE probe was verified, the output was
captured, and the wrong conclusion was already written into `godbolt-note.txt` and a
`manual-case-*.txt` before the control was run.

## 4. `--expect` cannot be declared before an exploratory probe

`SKILL.md` says "Always declare `--expect`", and `audit_issue` fails a variant without
one. But a variant whose *purpose* is to answer an open question ("does the `./` spelling
reproduce too?") has no expectation until it has been run. The workflow that satisfies
both is: run once without `--expect`, read it, re-run with `--expect` set to the measured
truth — which is what was done here for `dotslash` and `selfinclude-samespelling`. That is
fine, and arguably the assertion is more valuable that way (it now pins a measured fact
forever), but it is not what the wording implies and it costs a second run.

Suggested: say explicitly that exploratory variants are run twice, and that `--expect`
records what was measured rather than what was guessed.

## 5. `-P` writes a file into the issue directory

`run --args "... -P repro.hlsl"` silently dropped `repro.i` next to the evidence: not in
`cmd.txt`, not named in any header, invisible to `reindex`. Re-running with an explicit
`-P -Fi preprocessed-repro.i` made it reproducible and traceable, since the variant's
`# cmd:` header now names the file it emits.

Generalises beyond `-P`: any probe with a file-producing flag (`-Fo`, `-Fh`, `-Fre`,
`-Fd`) leaves an artifact the audit cannot see. #2427's `dbgdir/` note in step 3 is the
same hazard from the other direction (a directory git cannot store). A line in step 5 —
"name any file a probe emits, so it is evidence rather than litter" — would cover both.

## 6. Filesystem-dependent issues need the filesystem recorded

Whether this issue reproduces at all depends on the case sensitivity of the directory the
repro lives in, and Windows 10+ makes that a **per-directory** attribute
(`fsutil file queryCaseSensitiveInfo`), not a platform constant. That is environment
state no `out-*.txt` header captures, and it is exactly the kind of thing that makes a
verdict unreproducible six months later. Captured by hand here as
`manual-case-filesystem.txt`.

There is no label for it either: the taxonomy has `linux` and `macos` but no `windows`,
so a platform-conditional bug cannot be routed by label.

## 7. Nothing in the taxonomy expresses "the title is wrong"

The most useful thing found here is that #8527's title and framing ("case sensitive")
describe a special case of a broader defect (`#pragma once` keyed on the spelled path).
`SKILL.md`'s batch-report section says to flag prominently any issue whose text no longer
matches its behaviour — which is the right home for it — but there is no field on
`verdict.json` for it, so it survives only in prose. A `--title-misleading` flag, or a
convention that such findings open `summary`, would make them queryable.

## 8. `reindex` silently drops db-only fields, and `godbolt --skip` is one of them

`cmd_reindex` rebuilds the `issues` table from `verdict.json` alone (`triage.py`, the
`fields = {k: v for k, v in rec.items() if k in ISSUE_FIELDS}` loop). Anything written to
the db by another subcommand and *not* mirrored into `verdict.json` is lost the next time
anyone reindexes. Several workers share one db and each runs `reindex` at the end, so a
peer's reindex can wipe your fields mid-triage.

Concretely, this bit twice in this triage:

* `godbolt --skip "<reason>"` reported success, but `verdict.json` had no `godbolt_skip`
  and `SELECT godbolt_skip FROM issues WHERE number=8527` returned NULL afterwards.
  `write_verdict_json` serialises the db row it reads at `verdict` time, so a skip
  recorded through `godbolt` only survives if `verdict` runs *after* it and no reindex
  intervenes. `audit_issue` then reports the false gap "neither a Compiler Explorer link
  nor a recorded reason for skipping one (step 7)".
* `fetch` populates `title`, `url`, `created_at` and `labels`; after a reindex,
  `labels --issue 8527` printed `now: (none)` because the row had been rebuilt from a
  `verdict.json` that carried none of them.

Both are recoverable — `verdict --godbolt-skip ... --title ... --labels ...` writes them
to the db *and* into `verdict.json`, so they then survive — but nothing warns you, and the
`labels` regression is easy to miss because the command still exits 0.

Suggested fixes, in order of cheapness: have `cmd_godbolt` (and `cmd_fetch`) rewrite
`verdict.json` when one already exists; or have `reindex` preserve existing non-NULL
columns not present in `verdict.json` instead of leaving them at their rebuilt default;
or have `SKILL.md` say plainly that `verdict` must be the last write, and that
`--godbolt-skip` on `verdict` is preferred over the standalone `godbolt --skip`.

How I hit it: ran `godbolt --skip` at step 7, then `verdict` at step 11, then noticed
`verdict.json` had no `godbolt_skip` while sanity-checking the file.

## 9. `reindex` is destructive by default and unsafe in a parallel batch

Found live during batch-004, the first batch run with several workers on one machine.

`reindex` takes `--reset`, and **`--reset` defaults to True**:

    s.add_argument("--reset", action="store_true", default=True,
                   help="clear issues and runs first (default)")
    s.add_argument("--no-reset", dest="reset", action="store_false")

so a bare `python scripts\triage.py reindex` runs
`DELETE FROM issues; DELETE FROM runs;` and rebuilds from whatever happens to be on disk
at that instant (`cmd_reindex`, `triage.py:1344-1346`). One shared database, several
workers mid-write: a reindex by any one worker deletes rows the others are still
producing, and re-adds only the subset already flushed to disk.

I hit this from the other side. My brief instructed me to finish with `reindex` as a
completeness check; I ran it three times. The orchestrator then withdrew the instruction
mid-flight, having realised the default. No evidence was harmed -- `reindex` only *reads*
the evidence tree, and the tree is the source of truth -- but the audit output it printed
was misleading in both directions: it listed gaps for other workers' issues that were
simply work-in-progress, and it could equally have shown *my* issue as complete on the
strength of a half-written peer's rows.

Two distinct problems, worth separating:

* **The default is backwards.** A subcommand whose first act is `DELETE FROM` should
  require the destructive flag, not the safe one. `--reset` defaulting to False, with
  `--reset` opt-in for the authoritative end-of-batch rebuild, would make the accident
  impossible. Note this compounds observation #8: reset+rebuild is exactly what discards
  db-only fields such as `godbolt_skip`.
* **The completeness audit is entangled with the rebuild.** `audit_issue` is the genuinely
  valuable half and it is pure -- it reads a directory and a `verdict.json` and yields
  strings. There is no way to invoke it alone. A `triage.py audit --issue N` that runs
  `audit_issue` over one directory and touches no tables would give a worker the check
  they actually want, per-issue, with no shared-state risk at all. `SKILL.md` could then
  point workers at `audit` and reserve `reindex` for the collation step.

Until then the per-issue check has to be done by hand, and `SKILL.md` should say so
explicitly for parallel batches: **`reindex` is a collation-time command, not a
worker-time one.**

## 10. `--expect no-match` is silently satisfied by `invalid-probe`

`expectation_violated` (`triage.py:812-814`) is
`(verdict == "repro") != (expect == "match")`, so a control declared `--expect no-match`
passes when the run scores `no-repro` *and* when it scores `invalid-probe`. Those are not
the same claim: `no-repro` means the compiler ran the test and the symptom was absent,
`invalid-probe` means the test never ran.

Hit here deliberately. `variant-as-filed-cs66-v1.4.1907.txt` runs the reporter's exact
`-T cs_6_6` command on the oldest release to demonstrate *why* `cmd.txt` retargets to
`cs_6_0`; it produces `error: invalid profile cs_6_6` and scores `invalid-probe`. I had
declared `no-match` and the tool accepted it without comment.

In this instance the recorded header still says `verdict: invalid-probe`, so a reader is
not misled, and the run is the evidence for a claim rather than a control on the defect.
But the general shape is the one `cmd_reindex`'s own docstring calls out as a
wrong-verdict class -- "an absence predicate satisfied by a failed parse". A third
expectation token (`--expect invalid`), or simply treating `invalid-probe` as violating
*any* declared expectation, would close it: an expectation is a claim about what the
compiler did, and `invalid-probe` is the assertion that it did not get far enough to say.
