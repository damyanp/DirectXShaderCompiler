# Method observations from triaging #2191

Recorded here rather than acted on, per the single-writer rule. Collation decides whether
any of these belongs in `SKILL.md` or `triage.py`.

---

## 1. `bisect` is structurally blind to Debug-only asserts, and says "never reproduced"

**How I hit it.** #2191's symptom is an assert. `match.json` is `internal_failure`, as
SKILL.md step 4 requires. On the Debug ground truth it fires: exit `0xE0000001`. Then:

```
python scripts/triage.py bisect --issue 2191
  v1.4.1907      no-repro
  v1.9.2607      no-repro
result: never-repro'd-in-releases across v1.4.1907..v1.9.2607
```

Taken at face value that reads "no shipped compiler has ever had this bug", which for an
`internal_failure` predicate is a hair's breadth from "it was never real". The truth is that
**every release binary is a Release build**, and `include/llvm/llvm_assert/assert.h` compiles
`assert` to `((void)0)` under `NDEBUG`. All 20 releases *cannot* exhibit the symptom.

**Why the existing guards do not catch it.** SKILL.md warns about this in exactly one place -
"a large share of old DXC issues are asserts, and Release builds have asserts compiled out" -
and it is in the *ground-truth build* section, framed as a reason to build Debug. The warning
is never carried forward to step 6, where the whole bisection axis is Release binaries. Nor
does `invalid-probe` help: an invalid probe is one that never ran the repro, and these ran it
perfectly - exit 0, correct DXIL. They are valid probes of a symptom that cannot appear in
them. That is a third category the vocabulary has no word for, alongside `no-repro` and
`invalid-probe`.

This is the same shape as the trap SKILL.md already documents for #3873 ("a bare `timeout`
predicate scores the Debug ground truth as no-repro and reports this open bug as fixed") -
but the axis is inverted, and #3873's fix (`any_of` over both signatures) does not apply,
because in Release there *is* no second signature: the code is simply correct.

**Suggested change.** Either or both:

- `bisect` should warn when the ground-truth probe's exit status is `0xE0000001`
  (`STATUS_LLVM_ASSERT`) - or more generally when the only signature seen is one that
  `NDEBUG` removes - saying that release binaries cannot show this and the result is not
  evidence of a fix;
- give `history` a value such as `not-observable-in-release-binaries`, so the database row
  cannot be misread. I worked around it by putting the qualification inline in the free-text
  `--history` string, which works but relies on every reader reading it.

The general rule worth stating in `SKILL.md`: **"never-repro'd-in-releases" is only a finding
when the release binaries were capable of showing the symptom in the first place.**

---

## 2. dxc never prints the assert message, so every assert issue captures the least useful half

`triage.py run` captured, in full:

```
--- stderr ---
Internal compiler error: LLVM Assert
```

That identifies *that* it asserted, not *which* assert - which is the fact a maintainer needs,
and the only thing that distinguishes "still the same bug" from "a different bug at the same
input". The message goes to `OutputDebugString`:

```c
// lib/Support/assert.cpp
OutputDebugFormatA("Error: assert(%s)\nFile:\n%s(%d)\nFunc:\t%s\n", ...);
RaiseException(STATUS_LLVM_ASSERT, 0, 0, 0);
```

A debugger is the only way to read it. This one-liner works and needs nothing installed
beyond the Windows SDK debuggers:

```
cdb.exe -c "sxe -c \"kn 30;q\" e0000001;g;q" <dxc.exe> <args...>
```

It prints the `OutputDebugString` text *and* the stack. On #2191 it turned "an assert" into
`assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")` at
`SemaDecl.cpp(11156)` in `Sema::ActOnFinishFunctionBody`, which is what made it possible to
show the defect is not `[numthreads]`-specific.

**Suggested change.** Document this in step 4 or 5 next to the `internal_failure` guidance -
"on Windows, capture the assert text with cdb; `run` cannot see it" - and consider a
`run --debugger` mode that does it automatically for `internal_failure` issues. I wrote it
as `assert-stack.cmd` in the issue directory, which is re-runnable but is per-issue
boilerplate that every future assert issue will re-invent.

---

## 3. A second predicate silently destroys the first predicate's release probes

SKILL.md step 4 says: *"An issue may need more than one predicate... add e.g.
`match-crash.json` and bisect each separately."* I did exactly that. `bisect --issue 2191`
(default `match.json`) wrote `out-v1.4.1907.txt` and `out-v1.9.2607.txt`. Then
`bisect --issue 2191 --linear --match match-rejected.json` **overwrote both**, and went on to
overwrite all 20 releases. The header now reads `# match: match-rejected.json`, and the primary
predicate's recorded release scoring is gone.

**Mechanism.** `triage.py:776` builds the output filename from the compiler and the `--label`
only; the predicate is not part of it:

```python
out_path = os.path.join(
    d, f"variant-{label}-{compiler}.txt" if label else f"out-{compiler}.txt")
```

So any second predicate run over the same compilers lands on the same paths.

**It is completely silent.** No warning, no prompt, no note in the run output. `reindex` stays
happy, because it re-scores each file under the predicate its own header names, and that
predicate does agree with the file. And the surviving file looks *exactly* as authoritative as
the one it replaced - same format, same headers, a real measurement, just of a different
question. There is nothing in the artifact that says "something else used to be here".

Worth stating plainly: this was found by the orchestrator inspecting the `# match:` headers
across my directory from outside the session. Nothing in the tool surfaced it, and I had not
noticed the full extent - I recorded the first two files being overwritten and did not check
that the `--linear` pass had done it to all 20.

**Recovering the claim - and the wrong argument I nearly left in place.** I first justified
"no release asserts" by arguing that `internal_failure` is a strict subset of `nonzero_exit`,
so exit 0 settles it. **That is false.** `is_internal_failure` (`triage.py:268`) ends with

```python
return re.search(INTERNAL_MARKERS, text) is not None
```

reached *regardless of exit code*. A compiler exiting 0 while printing `Stack dump` or
`Assertion failed` is an internal failure and not a nonzero exit, so the two predicates are not
nested and the exit codes alone prove nothing.

The right recovery is to re-score the archived text, which is cheap because the raw
stdout/stderr and the `# exit:`/`# timed_out:` headers all survive an overwrite - only the
*scoring* is lost, not the measurement. `recheck-primary-predicate.py` does this by importing
`triage.is_internal_failure` rather than reimplementing it (a reimplementation could drift and
would prove nothing about what the tool would say); output in
`manual-case-primary-predicate-recheck.txt`: 0 of 20.

The general lesson is worse than my case, though. I got lucky that the overwritten predicate was
re-derivable from text the surviving probe happens to contain. Two predicates that need
*different compiler invocations* - different profiles, different flags, `-Zi` vs not - are not
recoverable at all, and that is precisely the multi-predicate case SKILL.md's advice is aimed at.

**Suggested change.** In preference order:

1. Put the predicate stem in the filename for anything other than the default:
   `out-<compiler>.txt` for `match.json`, `out-<compiler>-<stem>.txt` otherwise. Cheap, and it
   makes the evidence self-describing.
2. Failing that, refuse to overwrite an output whose recorded `# match:` differs from the
   current one unless `--force` is given. Refusing is better than warning: a warning scrolls past
   in a 20-release bisect.
3. Independently of either, have `reindex` report when an issue has two `match-*.json` files but
   only one predicate represented across its probe headers. That is the exact signature of this
   collision and it is detectable after the fact, from the tree alone.

---

## 4. A variant can silently test nothing, and `--expect` is what catches it

I built `variant-maxvertexcount.hlsl` to ask "is this specific to `[numthreads]`, as the title
claims?". The first version had a normal GS body. It compiled cleanly, which reads as "yes,
`[numthreads]`-specific" - a wrong and quotable conclusion. The confound: the repro's function
body is **empty**, and any full expression in the body drains the state the assert checks. The
variant had changed two things at once.

`--expect match` caught it immediately:

```
WARNING: control expected match but scored no-repro. Either the predicate does not
discriminate, or the control is not what you think it is.
```

SKILL.md frames `--expect` as an assertion re-checked by `reindex` - a guard against *future*
drift. Here it worked as an immediate guard against a *present* mistake, which is a stronger
selling point than the one currently written down, and an argument for stating the expected
result before running rather than after.

**Suggested change.** Extend the control discipline in step 4 explicitly to *variants*: a
variant built to isolate one property must hold everything else constant, **including
incidental properties of the repro** - an empty body, a missing return, an unused declaration.
Cite this as the example; it is cheaper than #1702's.

---

## 5. `reindex`'s completeness audit cannot pass in a per-issue session

`audit_issue` flags `verdict.json has no reviewed_by -- the independent review is mandatory
and left no trace (step 10)`. But SKILL.md's own phase table puts step 10 in **collate**, not
in the per-issue phase, and this session was told to skip it. So a per-issue worker who runs
`reindex` at the end - as instructed - sees a gap it is forbidden to close, and the only way
to make the audit clean is to record a review that did not happen.

I left `reviewed_by` empty, which is correct: SKILL.md says an empty `reviewed_by` is the only
way a skipped review is visible later. But "run `reindex` and confirm no missing evidence" and
"do not do step 10" cannot both be satisfied.

**Suggested change.** Have the audit distinguish "not yet reviewed" (expected mid-batch) from
the other gaps - e.g. list it under a separate heading, or suppress it unless `reindex` is run
with a `--final`/collation flag - so that a genuinely incomplete issue still stands out.

**Update (added later, see finding 7).** The instruction to run `reindex` per-issue was withdrawn
mid-batch because the command is destructive by default. That removes the contradiction described
above by removing the command from the per-issue phase - but the audit itself is still worth
having, so the suggestion stands for whoever runs it during collation.

---

## 6. PowerShell harness trap: `Select-Object -First N` leaves `$LASTEXITCODE` stale

SKILL.md's commands are bash; on Windows they get translated, and this environment is
PowerShell. While verifying that a snippet quoted in `comment.md` compiles, I ran:

```powershell
& dxc.exe -T cs_6_0 -E main $scratch 2>&1 | Select-Object -First 1
"exit=0x{0:X8}" -f $LASTEXITCODE
```

and read `exit=0xE0000001` - an assert. It was not. `Select-Object -First 1` terminates the
pipeline early, so `$LASTEXITCODE` was never updated and still held the value from the
*previous* dxc invocation, which had genuinely asserted. Re-run without truncation:

```powershell
$o = & dxc.exe -T cs_6_0 -E main $scratch 2>&1 ; $rc = $LASTEXITCODE   # -> 0x00000000
```

The first line of output (`;`, the start of DXIL) contradicted the exit code, which is the
only reason I caught it. Had the shader been one that legitimately produces no stdout, the
two would have agreed and I would have published a false assert.

This is SKILL.md's "a negative result from a command that errored is not a negative result"
in a Windows costume, and it hits exactly the hand-driven verification that step 9 demands
("Quote compiler output verbatim and verified, not from memory. Re-run it."). `triage.py run`
is immune - it uses `subprocess` - so the exposure is only in manual checks, which is where
the #3038 and #3150 defects also lived.

**Suggested change.** If `SKILL.md` ever grows a Windows/PowerShell section, say: capture into
a variable and read `$LASTEXITCODE` on the next statement; never truncate a native command's
pipeline before reading its exit code.

---

## 7. `reindex` defaults to destroying the database, which is unsafe in a parallel batch

**How I hit it.** My brief instructed me to finish with `python scripts\triage.py reindex` as a
completeness check, and I ran it - twice, once at the end of the main work and once after some
prose-only edits. The orchestrator then withdrew the instruction mid-flight, having realised the
command is not read-only. Recording it here so the finding is dated to the first parallel batch
rather than reconstructed later.

**What the code actually does.** `cmd_reindex` (`scripts/triage.py:1332`) starts with:

    if a.reset:
        c.executescript("DELETE FROM issues; DELETE FROM runs;")

and the flag is declared (`scripts/triage.py:1487`) as

    s.add_argument("--reset", action="store_true", default=True,
                   help="clear issues and runs first (default)")

so the destructive path is the **default**, and `--reset` is a no-op switch - only the separate
`--no-reset` turns it off. Nothing in the subcommand's help text
("rebuild the local database from the committed evidence tree") signals that it begins by
emptying two tables, and the docstring frames the command as a *verification* pass, which is
what made it read as a safe final check.

**Why that is a problem with several workers on one machine.** The rebuild is driven entirely by
what is on disk *at that instant*. Any row whose backing file is not yet written is simply gone.
The write ordering makes this mostly survivable but not entirely:

- `execute` writes `out-<compiler>.txt` (`:778`) **before** inserting the run row (`:789`), so a
  reindex racing a single probe usually re-derives the lost row from the file. Good.
- The `--repeat` aggregation path (`:717-726`) inserts a row with
  `cmd = "(see single runs)"` and a note like `match.json (2/3 runs)`. That row summarises N
  executions and has **no file of its own**. A file-driven rebuild cannot reconstruct it, so the
  hit-rate is destroyed permanently.
- Labelled/variant runs are dropped from the `runs` table. Row creation is driven by
  `f.startswith("out-")` (`:1391`), so my four `variant-*.txt` probes - recorded at capture time
  by `triage.py run --label` - are gone from the database after the reindex. Measured:
  `SELECT COUNT(*) FROM runs WHERE issue_number = 2191` returns **21** (1 ground truth + 20
  releases) though 25 output files exist.

  To be fair to the tool, and I checked this before writing it down rather than assuming: the
  *control assertions* in those files survive, because a separate loop at `:1377-1389` reads
  `variant-*.txt`, re-scores each one, and reports `control declared X but now scores Y`. So
  reindex still catches a variant whose expectation has broken. What is lost is only the run
  rows - which matters for anything that queries `runs` (batch reports, probe counts), since the
  GS variant is the evidence for the "not `[numthreads]`-specific" finding and no longer appears
  there.

That last one is the sharp edge, and it is not merely a concurrency issue: `reindex` is lossy for
any run metadata not derivable from an `out-*.txt` file, for the whole workspace, at any time.
For an intermittent crash - exactly the case where SKILL.md tells you to use `--repeat` - the
`2/3 runs` hit rate *is* the evidence, and it lives only in the database.

I checked after the fact: `SELECT COUNT(*) FROM runs WHERE cmd = '(see single runs)'` returns
**0**. I first read that as "my two reindexes destroyed no repeat metadata". **That reading is
wrong, and I am correcting it rather than leaving it.** A count of 0 is exactly what you would
see *after* the deletion, because those rows are the ones a file-driven rebuild cannot
reconstruct. Absence of the rows is not evidence they were never there - it is the predicted
symptom either way, which makes the check I ran incapable of distinguishing the two.

Worse, there is positive reason to think something *was* lost. `git status` in the repo root
lists an untracked `data/issues/3768/manual-case-repeat-measurements.txt` belonging to another
worker - a filename that strongly suggests that issue was probed with `--repeat`. I have not
opened it (not my directory), and I am not going to. But if #3768 recorded repeat aggregates
before my reindex, my reindex deleted them and could not rebuild them.

**Action for collation:** when the database is rebuilt authoritatively, treat run-row counts for
any issue that used `--repeat` - #3768 at least - as suspect, and get the hit-rates from that
issue's own files rather than from the database. This is the concrete damage from running a
destructive command mid-batch, and it landed on someone else's work, not mine.

**What was not harmed.** My own evidence is untouched - the files under `data/issues/2191/` are
the source of truth and `reindex` only reads them; all 21 of my run rows were re-derived. The
gaps it printed for #2188, #2202, #8527 and #8737 are other workers' work-in-progress, not
defects, and I have disregarded them.

**Suggested change.** Three things, in decreasing order of importance:

1. Flip the default to non-destructive (`--reset` off unless asked), or make the destructive
   form explicit (`reindex --rebuild`). A command whose help says "rebuild ... from the committed
   evidence tree" should not silently `DELETE FROM` anything.
2. Give the aggregate `--repeat` row and labelled/variant runs a durable on-disk form that the
   rebuild ingests - e.g. write the per-attempt verdicts into the `out-` file header, and create
   run rows from `variant-*.txt` too - so a rebuild is genuinely lossless.
3. Have SKILL.md say plainly that `reindex` is a **collation-phase** command, not a per-issue
   self-check, and give per-issue workers a read-only alternative (an `audit`/`--check` mode that
   reports gaps without touching the tables). Note this compounds finding #5: the command a
   per-issue worker is drawn to run is both unable to come back clean *and* unsafe to run.
