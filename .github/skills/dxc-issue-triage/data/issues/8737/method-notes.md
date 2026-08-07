# Method observations from triaging #8737

Recorded here rather than acted on, per the single-writer rule. Collation decides whether any
of this belongs in `SKILL.md` or `triage.py`.

---

## 1. An internal failure that exits **E_FAIL**, in both Debug and Release

SKILL.md's exit-code table is the load-bearing artefact for crash predicates, and it reads as
though internal failures always have a distinctive status:

| Outcome | Exit | Internal failure? |
| --- | --- | --- |
| syntax error, invalid profile, **DXIL validation failure** | 0x80004005 (E_FAIL) | **no** |
| assert fires (Debug) | 0x80000003 | yes |

#8737's ICE fits neither row. It exits **0x80004005 (E_FAIL)** in the Debug ground-truth build
*and* in every release binary, and prints `error: llvm::cast<X>() argument of incompatible type!`
as an ordinary-looking diagnostic. The reason is in the tree: a failed `llvm::cast<>` in DXC is
not an `assert` at all —

```cpp
// lib/Support/ErrorHandling.cpp:143
void llvm::llvm_cast_assert_internal(const char *func) {
  throw hlsl::Exception(DXC_E_LLVM_CAST_ERROR, std::string(func) + "<X>() argument of incompatible type!\n");
}
```

— it throws, dxc catches it, reports it through the diagnostics engine and returns E_FAIL. So
this class of internal failure is **indistinguishable from a legitimate error by exit code
alone, on every build configuration**. It is caught only by the `(?:llvm::)?cast<[^>]*>\(\) argument`
entry in `INTERNAL_MARKERS`.

Nothing was wrong: `is_internal_failure()` scored it correctly, exactly because it falls back to
the text markers. But SKILL.md's framing — "Prefer the exit code; treat text markers as a
backstop" — is inverted for this class, where the marker is the *only* signal. Two consequences
worth promoting:

- The advice "prefer the exit code" should be qualified: for `llvm_unreachable`,
  `report_fatal_error` and `llvm::cast` failures, DXC converts a would-be crash into a thrown
  `hlsl::Exception` on Windows (`ErrorHandling.cpp`, `#ifndef LLVM_ON_WIN32 … abort() #else throw`),
  so the exit code is E_FAIL and only the message distinguishes it.
- The Debug-vs-Release argument for the ground-truth build does not apply to this class. SKILL.md
  says Debug matters "because a large share of old DXC issues are asserts, and Release builds
  have asserts compiled out". Here Debug and Release are identical, and the release binaries were
  useful precisely because they behaved the same.

## 2. `bisect` cannot probe a symptom that is not in `cmd.txt`

SKILL.md step 4 explicitly contemplates an issue needing more than one predicate
("add e.g. `match-crash.json` and **bisect each separately**"). That works when the two
signatures come from the *same* input. #8737's two symptoms come from two different source
lines that cannot coexist in one translation unit — the ICE aborts the compile before the
silent case's DXIL exists — so they are two shaders, and `bisect` has `--match` but no
`--shader`. Only the `cmd.txt` repro can be bisected.

Workaround used, which worked well and is worth documenting as the pattern:

```powershell
foreach ($t in $tags) {
  python scripts\triage.py run --issue 8737 --compiler $t `
      --match match-silent-ub.json --shader repro-implicit-sample.hlsl `
      --label silent-ub --expect match
}
```

`run --compiler <release-tag>` resolves through `ensure_release`, and because the output name is
`variant-<label>-<compiler>.txt`, one fixed label across many compilers produces a complete
per-release history that `reindex` re-checks against `--expect` forever. This is strictly better
evidence than a bisect (every release probed, not a binary search), just more expensive.
A `bisect --shader/--label` option would make it a one-liner.

## 3. `--expect` is checked against the `--match` file, which is easy to get wrong for a probe
   whose purpose is the exit code

Capturing "does the full-container/validation path succeed" with
`--args "… -Fo NUL …" --match match-silent-ub.json --expect match` scored `no-match` and warned.
Correctly: with `-Fo` the disassembly is not printed, so a predicate whose conjuncts read the
DXIL cannot fire. The fix was to score that probe with `match.json` (`internal_failure`) and
`--expect no-match` instead. Nothing is broken, but the trap is real: **when a variant changes
what the compiler *outputs* rather than what it compiles, the primary predicate may become
inapplicable rather than false.** A one-line warning in step 7's control discipline would save
the round trip.

Related, and useful: re-running with the same `--label` overwrites the variant file cleanly, so a
mis-declared control can be corrected. But re-running with a *different* label leaves the old
file behind, still carrying its `# expect:` line, and `reindex` will re-check it forever. I hit
this when renaming a control and had to delete the stale `variant-…txt` by hand. Worth a note
that relabelling requires deleting the old capture.

## 4. `audit_issue` requires `reviewed_by`, but per-issue workers are told to skip step 10

SKILL.md's phase table assigns step 10 (the independent draft review) to **collation**, and this
worker was briefed to skip it. `audit_issue` nonetheless reports
`verdict.json has no reviewed_by -- the independent review is mandatory and left no trace` for
any issue with a recorded verdict. So a correctly-executed per-issue session cannot produce a
clean `reindex`, and the worker is pushed toward either (a) reporting a gap that is not a gap,
or (b) inventing a reviewer, which is the failure the check exists to prevent.

Suggest either making the `reviewed_by` gap conditional (e.g. only for issues whose batch has
been collated), or having SKILL.md state plainly that this one gap is expected until collation
and must not be filled in by the worker. **This worker left `reviewed_by` empty deliberately.**

## 5. `labels --issue N` said "not in the index; run 'fetch' first" *after* a successful fetch

`python scripts\triage.py labels --issue 8737` at step 8 answered
`#8737 not in the index; run 'fetch' first`, even though `fetch --issue 8737 --batch batch-004`
had succeeded and written `issue.json`. I first assumed the row was only created at `verdict`
time. That was wrong — `cmd_fetch` (triage.py:592-597) does `INSERT OR IGNORE` + `UPDATE`. The
actual cause is note 6 below; the error message is accurate about the symptom and misleading
about the remedy, because re-running `fetch` *would* have fixed it. Worth knowing that this
message does not mean "you forgot to fetch" when several workers share a workspace.

## 6. A concurrent worker's `reindex` silently deleted my issue's database row

**This is the biggest trap I hit, and SKILL.md does not mention it.**

`reindex` defaults to `--reset` (triage.py:1487, `action="store_true", default=True`) and its
first act is `DELETE FROM issues; DELETE FROM runs;` (triage.py:1344-1345). It then rebuilds the
`issues` table *only from `verdict.json` files on disk*. An issue that has been fetched and probed
but does not yet have a `verdict.json` — i.e. any in-flight triage — is **not** rebuilt. Its row
simply disappears.

SKILL.md tells every worker to finish with `reindex`, and the brief says several workers run in
parallel. So the normal, instructed behaviour of worker A destroys worker B's fetch metadata.
Concretely, by the time I recorded my verdict, #8737 had lost `title`, `url`, `created_at`,
`labels` and `godbolt_url` — all written earlier by `fetch` and `godbolt`. Because `verdict`
starts with `INSERT OR IGNORE`, it happily re-created a bare row and reported success; nothing
warned me. I only noticed because `labels --issue 8737` printed `now: (none)` when the issue
plainly carries `bug` and `needs-triage`.

The `godbolt_url` loss is the dangerous one: `audit_issue` requires `godbolt_url` or
`godbolt_skip` in `verdict.json`, so the result would have been a *published, verified* CE link
being reported as missing evidence — or, worse, a worker concluding they had somehow failed to
run `godbolt` and re-publishing. `runs` rows are also deleted, but those are rebuilt from the
`out-*.txt` / `variant-*.txt` captures, so that half is self-healing. The `issues` half is not.

I recovered by re-supplying the lost values through `verdict` (`--title --url --created-at
--labels --batch --godbolt-url`), read back out of my own `issue.json`, which is the safe path —
but a worker who never checked would have shipped a verdict with five null fields.

Suggestions, in rough order of value:
- make `reindex`'s reset preserve rows that have no `verdict.json` yet, or at least warn about
  them by name rather than dropping them silently;
- default `reindex` to `--no-reset` and make `--reset` opt-in, given that SKILL.md asks every
  worker to run it;
- failing either, have SKILL.md warn that in a shared workspace you should re-run `fetch` (it is
  idempotent and `batch=COALESCE(?, batch)`) immediately before recording the verdict, and check
  `labels --issue N` echoes the issue's real current labels.

### 6a. Confirmed independently by the orchestrator, and the instruction was withdrawn mid-flight

Worth recording precisely, because it happened during the first parallel batch rather than being
reconstructed later. My brief for this issue ended with an explicit instruction:

> "Before you finish, run `python scripts\triage.py reindex` and confirm it reports no missing
> evidence for #8737."

I followed it and ran `reindex` twice (once filtered, once for the full tail). Shortly afterwards
the orchestrator **withdrew that instruction** for parallel batches, for the same reason I had
already written up above: `--reset` defaults to True, so every worker's instructed final step
wipes `issues` and `runs` and rebuilds from whatever happens to be on disk at that instant,
deleting rows other workers are mid-way through writing and potentially producing duplicate or
missing run rows. The orchestrator's stated remedy is that the database is derived data and will
be rebuilt authoritatively once all workers have finished.

So this was found from two directions at once — I hit it as a *victim* (my row was deleted by
another worker, note 6 above) and then discovered I was also a *perpetrator* (my own instructed
`reindex` will have deleted the in-flight rows of every other worker in batch-004). Both halves
matter, and the second is the one a single worker is least likely to notice, because the damage
is entirely to other people's issues and shows up in their sessions, not yours. Concretely: my
`reindex` output listed `reviewed_by` gaps for #2188, #2191, #2202 and #8527. I read those as
other workers' work-in-progress, which the orchestrator has since confirmed is the right reading
— but I had no way to tell from the output whether I was reporting on their progress or on
damage I had just done to it.

Two things this suggests beyond the fixes listed above:

- Whatever the eventual default, `reindex` is a **batch-level / single-writer** operation and
  SKILL.md should say so in the step itself, not only in a note. As written, step 11's completeness
  check is the one instruction in the whole procedure that is unsafe to follow concurrently.
- The completeness check itself is genuinely valuable and should not simply be dropped for
  workers — it is the check that catches a number quoted in `notes.md` that was never written to
  disk. It wants a read-only form: an `audit`/`--check` mode scoped to a single issue that reads
  the tree and reports gaps **without touching the database at all**. That would be safe to run
  concurrently and would give the worker exactly the signal step 11 is after. Absent that, the
  fallback is what I did on the orchestrator's instruction — audit the issue directory by hand
  against the deliverable list and verify every quoted measurement resolves to a captured file.

## 7. The by-hand completeness audit caught four unbacked claims that `reindex` would have passed

Context: the orchestrator withdrew the `reindex` instruction (6a) and asked for a by-hand
self-check instead, specifically "any measurement you quote must have a captured file backing it".
I expected this to be a formality. It was not — it found four things, and I want the record to
show that the manual check is *stronger* than the automated one, not a degraded substitute.

What `audit_issue` checks is that certain **files exist** (`expected.md`, a repro, `cmd.txt`,
`notes.md`, `comment.md`, a `godbolt_url` or skip reason, and so on) and that captured probes are
still consistent with `cmd.txt` and their declared `--expect`. What it cannot check is whether a
sentence in `notes.md` corresponds to anything that was ever measured. Every one of the following
would have sailed through a clean `reindex`:

1. **The ground-truth version check had no captured file.** SKILL.md makes verifying
   `dxc --version` a precondition for trusting any result, and the brief made it a stop condition.
   I ran it, read it, and never wrote it down — the single most load-bearing measurement in the
   whole triage existed only in my terminal scrollback. Now `manual-ground-truth-version.txt`.
2. **Five source citations were quoted by file:line with no captured text.** A stranger could
   open the files, so this is weaker than case 1 — but the tree moves. Which brings up:
3. **The tree had in fact moved, and I had not checked.** `HEAD` is `f8220ace`, not `eff900d5`;
   the citations were read from the working tree while the binary was built at `eff900d5`. It
   turns out to be benign — all 316 files differing between them are triage-workspace data and no
   compiler source changed — but I only know that because the audit made me look. Had another
   worker's session committed a compiler change, every line number in my write-up would have been
   silently wrong. **Recommendation: SKILL.md should ask workers to record
   `git diff --stat <built-commit>..HEAD` whenever they cite source lines**, or simply to cite
   from the built commit via `git show eff900d5:path`.
4. **A date was wrong.** `notes.md` said v1.7.2207 was published 2022-07-18. The release
   catalogue says `2022-07-14T19:33:48Z`. Nothing depended on it, which is exactly why it survived
   — it was a plausible number recalled rather than looked up, sitting next to numbers that were
   all properly measured. Corrected, and now sourced from the catalogue.
5. **The Compiler Explorer verification had no capture**, even though `godbolt_url` was present
   and `audit_issue` was therefore satisfied. "All three panes verified" was a claim about three
   HTTP round trips that left no trace. Re-run and captured to `manual-godbolt-verification.txt`,
   with `verify-godbolt.py` checked in so it can be repeated. Same for the *negative* CE decisions
   — the reasons for having no Clang pane and no RGA pane are load-bearing (they are why the link
   cannot show the reporter's actual RGA symptom) and were equally unbacked; now
   `manual-godbolt-rejected-panes.txt`.
6. **An absence claim had no search shown.** "No test combines `RWTexture2DMS` with
   `Interlocked`" is precisely the kind of statement that needs its method visible, since it is
   unfalsifiable without knowing what was searched. Now `manual-testsuite-search.txt`, which shows
   the 8 files found and the 0 that matched both.

Two of these are worth generalising:

- **`godbolt_url` being present is not evidence that the link shows what the write-up says it
  shows.** If `cmd_godbolt` wrote a small capture of each pane's exit code and matched lines at
  publish time, this class of gap would close automatically and CE links would stop being an
  assertion of trust.
- **A convention for hand measurements would help.** I used a `manual-*.txt` prefix with a header
  saying what claim the file backs, chosen so `reindex` ignores it (`out-*` prints a "pre-reindex
  header" warning and `variant-*` gets re-scored, neither of which is wanted). Making that prefix
  official in SKILL.md — plus stating the rule as "a claim whose evidence is not a file is not a
  claim" — would turn the audit from a memory exercise into a mechanical one. Better still,
  `audit_issue` could flag an issue whose `notes.md` cites no `manual-*` file while containing
  quoted command output, though that heuristic may be too crude to be worth it.
