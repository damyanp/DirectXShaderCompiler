# End-of-pass review of the DXC issue-triage skill

## Review scope

I reviewed the current `SKILL.md`, `README.md`, `.github/copilot-instructions.md`, all five
shared scripts, all 14 orchestrator-note files, and all 25 numbered session checkpoints plus
`checkpoints/index.md`. I indexed the
lesson headings in all 91 `method-notes.md` files. For the issue-local sample I then read in
full all nine batch-017 notes plus eight high-risk/long-form notes chosen for proven
wrong-answer incidents and subsystem diversity: 2128, 2188, 2191, 2202, 2918, 2923, 3005 and
3237. I also read the relevant sections of 4036, 4384, 4605 and 4614 where the heading scan
showed a lesson not present in `SKILL.md`.

No surviving workflow-critical lesson was found only in a checkpoint. The checkpoint-only
material was either environment/session-specific, later superseded, or already encoded in a
repo file or script. Three substantive lessons were still stranded in one issue note: stale
labelled captures after source edits in 4605, the live-attach debugger-thread trap in 4614,
and `-verify` parsing prose comments in 4722. The fixed-output collision in 2128 had reached
its batch report but not `SKILL.md`. They are addressed below.

`.github/copilot-instructions.md` does not conflict with this skill. It applies to pull-request
release-note review, while this workflow is issue triage and report-only.

## Proposals

## 1. Use the real script path in every `SKILL.md` command
[APPLY]

**Summary:** Make all command examples runnable from the skill root, which is the working
directory established by `README.md`.

**Current text:** The exact token `python triage.py` occurs 25 times in `SKILL.md` at current
lines 265, 266, 267, 322, 395, 540, 765, 838, 839, 955, 956, 1006, 1007, 1008, 1293, 1323,
1340, 1354, 1494, 1495, 1506, 1745, 1899, 1900 and 1901. For example:

```text
python triage.py init                        # first time only
python triage.py reindex                     # after a fresh clone: rebuild db from data/
python triage.py catalog --seed-from <repo>/build/tools/clang/test/dxc_releases
```

`SKILL.md:260-262` also says:

```text
Evidence is committed because a verdict nobody can re-check is just an assertion. The cache
is not, because it is either huge, machine-specific, or derived. `scripts/triage.py` is the
only tool you need.
```

**Replacement text:** Replace every exact occurrence of:

```text
python triage.py
```

with:

```text
python scripts/triage.py
```

Replace the quoted paragraph with:

```text
Evidence is committed because a verdict nobody can re-check is just an assertion. The cache
is not, because it is either huge, machine-specific, or derived. `scripts/triage.py` is the
core triage CLI; batch verification and collation also use `test_predicates.py`,
`check_paths.py`, `render_comments.py` and `render_overview.py`.
```

**Rationale:** `triage.py` is under `scripts/`; the current commands fail from the skill root.
The cross-batch commands and all README commands already use the correct path.

**Evidence:** `README.md:140-149`; `scripts/triage.py`.

## 2. Stop registering `HEAD` as compiler provenance
[APPLY]

**Summary:** Make the setup commands agree with the later, correct public-provenance rule.

**Current text:** `SKILL.md:322` and `README.md:149` contain:

```text
--commit $(git rev-parse HEAD)
```

The surrounding `SKILL.md` text later says:

```text
> **Cite a publicly resolvable commit, not whatever the binary self-reports.**
```

**Replacement text:** In both files, replace the exact token with:

```text
--commit <public-upstream-sha>
```

The complete SKILL command becomes:

```bash
python scripts/triage.py compiler --id main-debug --exe <build>/Debug/bin/dxc \
  --commit <public-upstream-sha>
```

The complete README command becomes:

```bash
python scripts/triage.py compiler --id main-debug --exe ../../../build/Debug/bin/dxc.exe \
                                  --commit <public-upstream-sha>
```

**Rationale:** `HEAD` can be fork-local or later orphaned. This exact mismatch required the
25-issue provenance correction; the controlled diff described immediately below the command
is the authoritative equivalence test.

**Evidence:** `data/reports/provenance-correction.md`;
`data/reports/batch-010-orchestrator-notes.md`.

## 3. Correct the stale claim about compiler registration
[APPLY]

**Summary:** Describe what `cmd_compiler` now actually persists.

**Current text:** `SKILL.md:352-358`:

```text
> **Re-register the compiler after *every* rebuild, and re-read the registry to confirm.**
> `triage.py compiler` updates the database but not `.cache/compilers/<id>.json`, so a
> mid-pass rebuild silently leaves the registry describing the previous binary. The label
> `main-debug` is a *mutable pointer*, and capture headers record the compiler's path, not its
> commit — so the only in-file trace of what actually ran is the version string DXIL metadata
> happens to embed, and crash-only probes emit none at all.
```

**Replacement text:**

```text
> **Re-register the compiler after *every* rebuild, and inspect what was registered.**
> `triage.py compiler` updates both the `compilers` database row and
> `.cache/compilers/<id>.json`, then prints the executable, version, commit and registry path.
> Confirm those values before continuing. The label `main-debug` is still a *mutable pointer*,
> and capture headers record the compiler's path rather than its commit, so crash-only probes
> still have no independent in-file build identity.
```

**Rationale:** The current warning documents a defect that has already been fixed and now
teaches a fresh operator to distrust the correct behavior.

**Evidence:** `scripts/triage.py:821-853`.

## 4. Downgrade the Compiler Explorer “verified” guarantee to what the code enforces
[APPLY]

**Summary:** Make it explicit that short-link read-back failures are warnings, not hard stops.

**Current text:** `SKILL.md:1296-1299`:

```text
Compiles the repro on [Compiler Explorer](https://godbolt.org), prints the result per
compiler, and stores a short link on the issue row. Default compilers are `dxc_1_6_2112`
(CE's oldest) and `dxc_trunk`. **The link is verified before it is handed over** — never
publish one without checking it shows what you claim.
```

**Replacement text:**

```text
Compiles the repro on [Compiler Explorer](https://godbolt.org), prints the result per
compiler, and stores a short link on the issue row. Default compilers are `dxc_1_6_2112`
(CE's oldest) and `dxc_trunk`. By default the command writes every pane's full output to
`manual-case-godbolt-verify.txt` and then attempts to read the short link back. A read-back
mismatch or request failure is only a warning: the command still records and prints the URL.
Treat any warning as a hard stop, inspect the saved panes, and open the link before citing it.
```

**Rationale:** `cmd_godbolt` warns and continues on a dropped pane, changed source, or failed
read-back. The later SKILL paragraph already says it “warns on a mismatch.”

**Evidence:** `scripts/triage.py:2460-2593`; `data/reports/batch-008.md`.

## 5. Fix the two misleading strings emitted by the runner
[APPLY]

**Summary:** Make linear history and harness captures say what actually happened.

**Current text:** `scripts/triage.py:2104-2113`:

```python
        if len(runs) == 1:
            state = f"{'always' if runs[0][1] else 'never'}-repro'd"
            print(f"\nresult: {state} across {usable[0][0]}..{usable[-1][0]}{note}")
            warn_release_blind(a.issue, state)
        else:
            print("\nresult: non-monotonic history" + note + ", transitions at " +
                  ", ".join(f"{t} -> {'repro' if v else 'no-repro'}"
                            for t, v in runs[1:]))
```

`scripts/triage.py:1456` also hardcodes:

```python
        chunks.append(f"$ dxc {line}\n[exe] {display_exe(exe)}\n"
```

**Replacement text:**

```python
        if len(runs) == 1:
            state = ("always-repro'd" if runs[0][1]
                     else "never-repro'd-in-releases")
            print(f"\nresult: {state} across "
                  f"{usable[0][0]}..{usable[-1][0]}{note}")
            warn_release_blind(a.issue, state)
        elif len(runs) == 2:
            transition_tag, new_value = runs[1]
            transition_index = next(
                i for i, (tag, _) in enumerate(usable)
                if tag == transition_tag)
            prior_tag = usable[transition_index - 1][0]
            if runs[0][1] and not new_value:
                print(f"\nresult: fixed-in {transition_tag} "
                      f"(last repro: {prior_tag}){note}")
            else:
                print(f"\nresult: regressed-in {transition_tag} "
                      f"(last good: {prior_tag}){note}")
        else:
            print("\nresult: non-monotonic history" + note
                  + ", transitions at "
                  + ", ".join(f"{t} -> {'repro' if v else 'no-repro'}"
                              for t, v in runs[1:]))
```

and:

```python
        chunks.append(
            f"$ {os.path.basename(exe)} {line}\n"
            f"[exe] {display_exe(exe)}\n"
```

**Rationale:** A single clean→repro transition is monotonic, not “non-monotonic,” and linear
mode currently spells the clean-all case differently from binary mode. A harness capture must
not claim that `dxc` was executed when the registered executable was a wrapper.

**Evidence:** `data/issues/3954/method-notes.md`;
`data/issues/4615/method-notes.md`; `data/issues/4710/method-notes.md`;
`data/issues/2923/method-notes.md`.

## 6. Decide whether timeout captures should stop recording exit zero
[JUDGE]

**Summary:** A timed-out process currently persists `# exit: 0`, even though the run never
exited successfully.

**Current text:** `scripts/triage.py:1688-1713` persists `worst_rc` in three exact places:

```python
                + f"# exit: {worst_rc}\n# timed_out: {int(timed_out)}\n"
```

```python
                  (issue, compiler, " ; ".join(cmds), worst_rc, int(timed_out),
                   out_path, verdict, match_file, now()))
```

```python
    return {"compiler": compiler, "exit": worst_rc, "timed_out": timed_out,
```

**Replacement text:** Immediately before `with open(out_path, ...)`, add:

```python
    recorded_exit = None if timed_out else worst_rc
    displayed_exit = "TIMEOUT" if timed_out else worst_rc
```

Replace:

```python
                + f"# exit: {worst_rc}\n# timed_out: {int(timed_out)}\n"
```

with:

```python
                + f"# exit: {displayed_exit}\n"
                  f"# timed_out: {int(timed_out)}\n"
```

Replace:

```python
                  (issue, compiler, " ; ".join(cmds), worst_rc, int(timed_out),
                   out_path, verdict, match_file, now()))
```

with:

```python
                  (issue, compiler, " ; ".join(cmds), recorded_exit,
                   int(timed_out), out_path, verdict, match_file, now()))
```

Replace:

```python
    return {"compiler": compiler, "exit": worst_rc, "timed_out": timed_out,
```

with:

```python
    return {"compiler": compiler, "exit": recorded_exit,
            "timed_out": timed_out,
```

Also replace `cmd_run`'s display with:

```python
    shown_exit = "TIMEOUT" if r["timed_out"] else r["exit"]
    print(f"{r['compiler']}: exit={shown_exit} timed_out={r['timed_out']}"
          f" -> {r['verdict']}{extra}")
```

**Rationale:** The current predicate uses `timed_out` correctly, but a human reading the
header sees a successful exit. Multi-invocation semantics should be considered before changing
the persisted exit field, hence the judgement tag.

**Evidence:** `data/reports/batch-016.md`;
`data/issues/4614/method-notes.md`.

## 7. Document frozen expectations, `--hypothesis`, and `quote_from`
[APPLY]

**Summary:** The tool now distinguishes predictions from controls, but the procedure still
teaches only control assertions.

**Current text:** `SKILL.md:421-428` ends step 2 with:

```text
Record the repro quality honestly: `complete`, `partial`, `prose-only`, `none`, or
`agent-constructed`.
```

`SKILL.md:777-790` says:

```text
**Always declare `--expect`.** It is recorded in the output header and re-checked on every
`reindex`, which turns the control from an observation into a permanent assertion.
```

`SKILL.md:1097-1101` says only:

```text
> **What this means for you when triaging a diagnostic-quality issue:** write the diagnostic
> text into `match.json` rather than approximating it, and check the header.
```

**Replacement text:** After the repro-quality paragraph, add:

```text
Treat `expected.md` as write-once once the first probe has run. If the evidence contradicts
it, preserve the prediction and reconcile the difference explicitly in `notes.md`; do not
silently rewrite the pre-run criterion to fit the output.
```

After the `--expect` table, add:

````text
**Use `--hypothesis` when the expected result is a prediction, not a control invariant.**
A refuted control means the instrument or control is wrong; a refuted hypothesis is often the
finding. Record that distinction before running:

```bash
python scripts/triage.py run --issue <N> --shader case.hlsl \
  --label scope-question --expect no-match --hypothesis
```

The capture records `# expectation-kind: hypothesis` and
`# outcome: supported|refuted`. `triage.py expect` deliberately refuses to rewrite a tested
hypothesis after the result is known; use a new label for a new prediction.
````

After the diagnostic-quality paragraph, add:

```text
When one issue uses several predicates for the same diagnostic surface, a secondary predicate
may opt into a sibling predicate's literal diagnostic quotation with a top-level field such as
`"quote_from": ["match-diagnostic.json"]`. Use this only when the predicates genuinely describe
the same diagnostic; without the explicit link, sibling predicates remain isolated.
```

**Rationale:** Before `--hypothesis`, documented refutations were reported forever as rotted
controls. `quote_from` is implemented and used, but discoverable only from code and one issue
note.

**Evidence:** `data/reports/batch-014.md`;
`data/reports/batch-016-orchestrator-notes.md`;
`data/issues/4648/method-notes.md`; `data/issues/4723/method-notes.md`;
`scripts/triage.py:504-583,1462-1485,3213-3216`.

## 8. Adopt a real `never-implemented` history value and constrain `history`
[JUDGE]

**Summary:** Two isolated workers independently needed a value outside the documented
taxonomy; nearly half the existing field values are prose.

**Current text:** `SKILL.md:1010-1014`:

```text
Checks both endpoints first and short-circuits when they agree, so an always-broken or
never-implemented issue costs only two runs. Reports `fixed-in <tag>`, `regressed-in <tag>`,
`always-repro'd`, or `never-repro'd-in-releases`.
```

`README.md:87-91`:

```text
`history` is either `always-repro'd`, `never-repro'd-in-releases`, or names the release on
each side of a transition.
```

**Replacement text:**

```text
Checks both endpoints first and short-circuits when they agree. `bisect` reports
`fixed-in <tag>`, `regressed-in <tag>`, `always-repro'd`, or
`never-repro'd-in-releases`. The issue-level `history` field additionally permits
`never-implemented` when the measured rejection is correct because the requested capability
has never existed. Keep release intervals, attribution caveats and explanatory prose in
`notes.md`, `fixed_in` and `regressed_in`; keep `history` short.
```

and:

```text
`history` is a short classification: `always-repro'd`,
`never-repro'd-in-releases`, `fixed-in <tag>`, `regressed-in <tag>`, or
`never-implemented`. The last value means the observed rejection is correct because the
requested capability has never existed; it must not be normalized to `always-repro'd`.
Detailed intervals and caveats belong in `notes.md`.
```

After agreeing on this text, add `cmd_verdict` validation for new records. Do not mechanically
rewrite the existing prose values; several contain load-bearing caveats that must first be
moved into `notes.md`.

**Rationale:** `always-repro'd` would falsely publish “DXC has always been broken” for a
correct, never-supported feature. Schema cleanup and legacy migration require judgement.

**Evidence:** `data/reports/batch-017.md`;
`data/reports/batch-017-orchestrator-notes.md` findings 1, 14 and 17;
`data/issues/4708/method-notes.md`.

## 9. Make `releases.cached_path` the only supported release-enumeration API
[APPLY]

**Summary:** Close the proven two-root, arm64 and nonuniform-layout failure class.

**Current text:** `SKILL.md:274-280`:

```text
The catalog is also the reconciliation layer for the two physical release roots: downloaded
assets under `.cache` and test-seeded trees under
`build/tools/clang/test/dxc_releases`. The `seed_local()` importer writes the selected
executable into the single `releases.cached_path` column; there is no `seed_local` column.
Release-matrix scripts should query `cached_path` rather than walking one root and silently
missing the other.
```

**Replacement text:**

```text
The catalog is the only supported release-enumeration API. It reconciles downloaded assets
under `.cache` with test-seeded trees under
`build/tools/clang/test/dxc_releases`, and stores the selected executable in
`releases.cached_path`; there is no `seed_local` column. Release-matrix scripts **must obtain executables through `ensure_release(tag)` or catalog
`cached_path`, ordered by `build_date`, and must not recurse either cache root**. The physical
trees are nonuniform and can contain both x64 and arm64 `dxc.exe` files; an arm64 launch
failure on an x64 host can otherwise be scored as empty compiler output and manufacture a
reproduction. A NULL `cached_path` for a row with a usable asset means unresolved machine
state; consult `asset_name`, `bisectable` and the per-issue release policy rather than inferring
that the release lacks the tool.
```

**Rationale:** Single-root walks already undercounted `dxv.exe`; recursive walks found 15 arm64
binaries capable of producing plausible false results.

**Evidence:** `data/reports/batch-016.md`;
`data/reports/batch-017-orchestrator-notes.md` finding 2;
`data/issues/4708/method-notes.md`.

## 10. Extend instrument controls to anchors, no-op modes and bundled validators
[APPLY]

**Summary:** Add the final-batch cases where the measuring layer, not the compiler behavior,
created the apparent transition.

**Current text:** `SKILL.md:748-756`:

```text
**A predicate reads the instrument as well as the behaviour.** Check its self-test on every
release, not only on `main`. Two tidy-looking regressions were instrument changes instead:
#3535's v1.4.1907 disassembly still held reflection metadata in DXIL before it moved to
`STAT`, and #3872's 2019 disassembler printed `NONE` where current builds print
`SHDINGRATE` even though the acceptance clauses and `i8 29` metadata were unchanged. If the
self-test flips while the behavioural clauses do not, that release is unmeasurable under the
predicate, not `no-repro`; write an instrument-portable twin or use a fixed reader.
```

**Replacement text:**

```text
**A predicate reads the instrument as well as the behaviour.** Check its self-test on every
release, not only on `main`. Two tidy-looking regressions were instrument changes instead:
#3535's v1.4.1907 disassembly still held reflection metadata in DXIL before it moved to
`STAT`, and #3872's 2019 disassembler printed `NONE` where current builds print
`SHDINGRATE` even though the acceptance clauses and `i8 29` metadata were unchanged. If the
self-test flips while the behavioural clauses do not, that release is unmeasurable under the
predicate, not `no-repro`; write an instrument-portable twin or use a fixed reader.

Before using any printed string, field or layout spelling as a history anchor, prove that the
anchor is present in a known-good compile at both the oldest and newest releases in the range.
A boundary at either measurable endpoint is especially suspicious: it may be the anchor's
history rather than the defect's.

A control whose expected result is also the default or no-op result proves nothing about
whether a requested mode ran. Add an engagement witness whose output changes only when the
mode or pass is active.

A release tag is a bundle, not just `dxc.exe`. When the symptom is a validator verdict, record
the emitted artifact separately from the bundled validator's pass/fail result. If two releases
emit byte-identical bad artifacts and only the validator verdict moves, attribute the boundary
to the validator component, not to DXC code generation.
```

**Rationale:** These rules prevent regressions manufactured by a new PSV field, an old IR
spelling, a no-op-equivalent control, or a bundled SPIRV-Tools update.

**Evidence:** `data/reports/batch-016.md`;
`data/reports/batch-017.md`; `data/issues/4666/method-notes.md`;
`data/issues/4701/method-notes.md`; `data/issues/4763/method-notes.md`.

## 11. Strengthen “evidence or it didn't happen” for public claims
[APPLY]

**Summary:** Require durable captures for shell observations, quotations and corrections of
named people.

**Current text:** `SKILL.md:48-50`:

```text
- **Evidence or it didn't happen.** Every verdict must be reproducible by a human from the
  files left behind: the repro, the exact command, and the captured output.
```

**Replacement text:**

```text
- **Evidence or it didn't happen.** Every verdict and every measurement asserted in
  `notes.md` or `comment.md` must be reproducible from the files left behind: the repro, the
  exact command, and the captured output. If prose names a command, version, count, pane,
  permalink or quoted output, copy it from a durable artifact rather than terminal scrollback
  or memory. If a draft contradicts a claim made by a named person, that contradiction needs
  its own recorded measurement with a discriminating control — preferably a pre-declared
  `--hypothesis` — or it does not go in the draft.
```

**Rationale:** Three true commands in 4701 existed only in terminal history; 4721 found
plausible but unverbatim quotes; 4763 nearly published a source-derived correction that
measurement proved wrong.

**Evidence:** `data/reports/batch-017.md`;
`data/issues/4701/method-notes.md`; `data/issues/4721/method-notes.md`;
`data/issues/4763/method-notes.md`.

## 12. Promote quote checking and preserve the draft-review delta
[JUDGE]

**Summary:** Turn the successful issue-local quote checker and otherwise-lost review history
into batch-level artifacts.

**Current text:** `SKILL.md:1643-1646`:

```text
Where you reject a suggestion, know why. Record anything that changes the method in the batch
report, and record the reviewer itself with `verdict --reviewed-by <model>` — a required step
that leaves no trace is one you cannot later tell was skipped.
```

**Replacement text:**

````text
Where you reject a suggestion, know why. Persist a batch review artifact at
`reports/batch-NNN-draft-review.md` containing the reviewer model, each quoted current passage,
the exact accepted replacement or rejection reason, and the final decision. Before stamping
`reviewed_by`, run:

```bash
python scripts/check_quotes.py --batch NNN
```

The checker must require every output-shaped fenced line and inline quotation in each
`comment.md` to occur in an issue capture after ANSI normalization, while excluding its own
output from the search corpus. Record anything that changes the method in the batch report,
then stamp the reviewer with `verdict --reviewed-by <model>`.
````

Move and generalize:

```text
data/issues/4721/check-quotes.py
```

to:

```text
scripts/check_quotes.py
```

**Rationale:** The checker caught two fabricated “verbatim” quotes. In-place draft editing
currently destroys the exact pre-review text, so later reconstruction can recover only a
semantic summary.

**Evidence:** `data/issues/4721/check-quotes.py`;
`data/reports/batch-016.md` reconstruction gaps;
`data/reports/batch-017-orchestrator-notes.md` finding 15.

## 13. Add a command-line and file-output harness discipline
[APPLY]

**Summary:** Capture the observable that command-line issues actually expose, without trusting
shell status propagation or file excerpts.

**Current text:** Insert after `SKILL.md:922-926`, the paragraph beginning:

```text
> **Not every repro is a shader.**
```

**Replacement text to add:**

```text
> **File-output and command-line issues need harness controls of their own.** Treat the harness
> as part of the instrument. Capture every produced file's byte size and both its head and
> tail; a head-only excerpt can hide an appended defect. Delete expected outputs before each
> arm and report PRESENT/MISSING explicitly so stale files cannot satisfy the predicate.
> Capture the real subprocess status in Python. `%ERRORLEVEL%` in a single `cmd /c` line is
> expanded before the command runs, and a `.cmd` wrapper can mangle an HRESULT into a
> crash-looking unsigned value. If a wrapper must be registered as a compiler, return a small
> documented wrapper status and print the real hexadecimal status and classification in the
> captured text.
```

**Rationale:** All four failures occurred while triaging 4723 and each produced plausible,
wrong evidence rather than a loud harness failure.

**Evidence:** `data/reports/batch-017.md`;
`data/issues/4723/method-notes.md`.

## 14. Make the `reindex` and overview rules conditional on pipelining
[JUDGE]

**Summary:** The current absolute sequencing is unsafe when batch N+1 workers overlap
collation of batch N.

**Current text:** `SKILL.md:98-107`:

```text
- **Collation runs `reindex` before writing anything.** Because probes are re-scored rather
  than restored, any lesson promoted during collation is applied retroactively to every issue
  in the batch — including the ones triaged before it was learned. That is what buys back the
  lesson-propagation a parallel batch would otherwise lose.
  **`audit` does not do this**; only `reindex` re-scores. `audit` checks completeness and
  staleness and reads the existing verdicts. Batch 008's brief said `audit` re-scored every
  probe and used that as the reason to run it first — it does not, so a batch that runs only
  `audit` gets no retroactive re-scoring at all. Both commands are worth running; do not
  substitute one for the other, and if `reindex` is deliberately withheld from a batch, say in
  the report that no retroactive re-scoring occurred.
```

`SKILL.md:1873-1881` also says:

````text
`reports/overview.md` is the standing answer to "what should we do next?" across every issue
triaged so far. **Regenerate it at the end of every batch — it is the last step:**

```bash
python scripts/triage.py reindex        # rebuild the db from the evidence
python scripts/render_overview.py       # then regenerate the overview
```
````

**Replacement text:**

```text
- **Run `reindex` only at a quiescent single-writer boundary.** Without pipelining, collation
  runs it before writing anything, so promoted predicate lessons are applied retroactively to
  the whole batch. With overlapping batches, the orchestrator owns `reindex` and runs it only
  when no per-issue worker in any batch is live; collation must not run it. A pipelined
  collation uses `audit --issue <n> --collated` after stamping `reviewed_by`, never a bare
  `audit`, because bare audit also checks the in-flight global overview. `audit` checks
  completeness and staleness but does not re-score probes. If a batch is handed off before
  the next authoritative `reindex`, state explicitly that no retroactive re-scoring has yet
  occurred.

- **Do not reinterpret live invocations.** While another batch is running, shared-tool changes
  must be opt-in/additive or monotonically stricter and regression-tested. Any change that
  loosens a gate or changes scoring for an existing invocation waits for the quiescent
  boundary.
```

and:

````text
`reports/overview.md` is the standing answer to "what should we do next?" across every issue
triaged so far. Regenerate it only from a quiescent snapshot, after the authoritative
`reindex`, when no later batch has uncommitted issue directories on disk:

```bash
python scripts/triage.py reindex
python scripts/render_overview.py
```

Running the renderer while another batch is in flight can publish dangling links to issue
directories that are not part of the batch being committed.
````

Also replace `README.md:32-36`:

```text
Both run at the end of a batch. `triage.py audit` fails if `overview.md` is older than the
newest `verdict.json`, so a forgotten regeneration is caught rather than shipped — a stale
overview is a well-formed document that quietly omits a whole batch, which is exactly the
kind of error nobody notices.
```

with:

```text
Run this pair only at a quiescent batch snapshot, when no later batch has uncommitted issue
directories on disk. `triage.py audit` fails if `overview.md` is older than the newest
`verdict.json`, so a forgotten regeneration is caught rather than shipped; it cannot detect
that an in-flight future batch was accidentally included.
```

**Rationale:** The destructive reindex hazard materialized in batch 004; overview generation
mid-pipeline was later shown to mix uncommitted future-batch data into the current snapshot.
Whether pipelining should be a supported default is a method decision.

**Evidence:** `data/reports/batch-014-orchestrator-notes.md`;
`data/reports/batch-015.md`; `data/reports/batch-016-orchestrator-notes.md`.

## 15. Make reading every `method-notes.md` an explicit collation gate
[APPLY]

**Summary:** Remove the current possibility that one worker's method lesson is never opened.

**Current text:** `SKILL.md:1774-1779`:

```text
Write `reports/batch-NNN.md` covering: ground truth used (commit + version), a summary table
with a Compiler Explorer link per issue, per-issue findings, the **draft comments**, and —
importantly — **what the batch taught you about the method**. Predicate bugs and methodology
gaps found while triaging are as valuable as the verdicts, and should change how the next
batch is run.
```

**Replacement text:**

```text
Before writing `reports/batch-NNN.md`, enumerate the batch's issue directories and read every
`method-notes.md` in full; a worker summary is not a substitute. Record which observations
were promoted, rejected as issue-specific, superseded, or left as an open tooling question.
Also re-read every `match*.json` `note` against the implementation and captures — predicate
explanations are unreviewed prose and have been wrong while the predicate itself was right.

Write the report covering: ground truth used (commit + version), a summary table with a
Compiler Explorer link per issue, per-issue findings, the **draft comments**, and —
importantly — **what the batch taught you about the method**. Predicate bugs and methodology
gaps found while triaging are as valuable as the verdicts, and should change how the next
batch is run.
```

**Rationale:** SKILL currently says where notes go and how to rank them, but never says every
file must be read. `match.json` notes failed in the same way as compressed verdict fields.

**Evidence:** Every batch-008 method note was explicitly read in full;
`data/issues/3954/method-notes.md`; `data/reports/batch-016.md`.

## 16. Add a first-class “Adjacent findings” report section
[JUDGE]

**Summary:** Preserve controlled defects discovered beside, but not represented by, the source
issue.

**Current text:** `SKILL.md:1774-1779`, quoted in proposal 15, lists the required batch-report
contents and has no place for unfiled adjacent defects.

**Replacement text to add after that paragraph:**

```text
If triage finds a controlled defect that is not the issue under test, add an
`## Adjacent findings` section:

| Source issue | Adjacent finding | Repro and control evidence | Owner |
| --- | --- | --- | --- |

Do not file or post anything from this report-only workflow. Distinguish adjacent defects from
duplicates and from changed forms of the source issue; include only findings with a durable
repro and control.
```

**Rationale:** The pass found ready repros for distinct DXC and Clang defects that otherwise
survived only inside source-issue notes. Making this a required deliverable changes report
scope and needs a human decision.

**Evidence:** `data/reports/batch-017.md`;
`data/reports/batch-017-orchestrator-notes.md` findings 6 and 11.

## 17. Strengthen worker boundaries and completion checks
[APPLY]

**Summary:** State the negative write boundary, protect shared build outputs, and stop treating
an idle worker as complete.

**Current text:** `SKILL.md:136-137`:

```text
- the boundary: it writes only `data/issues/<nnnn>/`, and records method observations in
  `method-notes.md` rather than editing `SKILL.md` or `triage.py`;
```

`SKILL.md:145-147`:

```text
- the stop condition: verdict recorded and draft written, or a clear statement of what blocked
  it. `inconclusive` is a real outcome; a forced verdict is not.
```

**Replacement text:** Replace the boundary bullet with:

```text
- the boundary, as an absolute path: it writes inside
  `data/issues/<nnnn>/` **and nowhere else**, and records method observations in
  `method-notes.md` rather than editing `SKILL.md` or shared scripts. It must not rebuild or
  relink a shared repository target while peers are measuring the ground-truth build; record
  that question as unmeasured unless the orchestrator grants a quiescent exception;
```

Replace the stop-condition bullet with:

```text
- the stop condition: `verdict.json`, `notes.md` and `comment.md` exist, the per-issue audit
  has run after the verdict was recorded, and a substantive final response states the verdict
  or the exact blocker. An idle/empty final turn is not completion. `inconclusive` is a real
  outcome; a forced verdict is not.
```

After the list, add:

```text
The orchestrator verifies completion from disk rather than worker self-report, re-prompts any
worker whose substantive response is missing, and checks for new untracked files outside the
skill tree before commit.
```

**Rationale:** Three workers ended before reporting, one completed 55 artifacts without a
verdict, one wrote a stray repro at repo root, and one correctly refused to relink `clang.exe`
while peers were using shared build products.

**Evidence:** `data/reports/batch-015.md`;
`data/reports/batch-017-orchestrator-notes.md` finding 16.

## 18. Move model and batch provenance out of worker self-report
[JUDGE]

**Summary:** The current responsibility assignment produces factually wrong provenance.

**Current text:** `SKILL.md:1745-1750` includes this worker command:

```bash
python triage.py verdict --issue <N> --status repros --repro-quality complete \
  --history "always-repro'd" --confidence high --suggested-action still-valid-keep-open \
  --summary "..." --notes-path issues/<nnnn>/notes.md --triaged-with-commit <sha> \
  --triaged-by "<model>" --reviewed-by "<reviewer model>"
```

`SKILL.md:1761-1766` then says:

```text
`--triaged-with-commit` records which compiler was measured; `--triaged-by` and
`--reviewed-by` record who did the measuring and who checked the write-up. Record all three.
A verdict is weighed differently depending on which model produced it, and step 10's review is
mandatory but unfalsifiable if nothing on disk says it happened — an empty `reviewed_by` is
the only way a skipped review is visible later.
```

**Replacement text:**

```bash
python scripts/triage.py verdict --issue <N> --status repros \
  --repro-quality complete --history "always-repro'd" --confidence high \
  --suggested-action still-valid-keep-open --summary "..." \
  --notes-path issues/<nnnn>/notes.md --triaged-with-commit <public-upstream-sha>
```

and:

```text
`--triaged-with-commit` records which compiler source was measured and is part of the
per-issue verdict. The worker must not self-report its model or batch identity. The
orchestrator stamps canonical `batch` and `triaged_by` values from the dispatch record; the
collation session stamps canonical `reviewed_by` from the independent-review dispatch after
the review is applied. Put details such as “blind attribution check” or “review applied
selectively” in `notes.md` or the batch review artifact, not in the identity field. Treat
legacy free-form identity values as hints, not reliable provenance.
```

**Rationale:** Workers and two collation agents misidentified their own models; `triaged_by`
has 22 spellings and `reviewed_by` 11. Changing field ownership and validation is a method and
schema decision.

**Evidence:** `data/reports/batch-015.md`;
`data/reports/batch-016-orchestrator-notes.md`;
`data/reports/batch-017-orchestrator-notes.md` finding 17.

## 19. State explicitly what `reindex` cannot re-run
[APPLY]

**Summary:** Do not let a bespoke release matrix appear mechanically protected when it is not.

**Current text:** `SKILL.md:199-203`:

```text
It cannot check reasoning. It will not tell you a repro is unfaithful to the issue, that the
predicate tests the wrong thing, or that a verdict misreads its own output. That is what the
human gate and the blind test are for.
```

**Replacement text:**

```text
It cannot check reasoning. It will not tell you a repro is unfaithful to the issue, that the
predicate tests the wrong thing, or that a verdict misreads its own output. It also does not
execute bespoke `manual-case-*.txt` generators or issue-local history matrices unless they
have been registered as a compiler and captured through `run`. If a headline status or release
boundary comes only from a manual harness, either bring it under `run`/`runs`, or state in the
notes and batch report that it is outside automatic re-checking and re-run it deliberately at
collation. The human gate and blind test cover the remaining reasoning gap.
```

**Rationale:** The headline 5293 regression boundary was correct but invisible to both
`reindex` and `audit`; the same limitation affected artifact-only histories.

**Evidence:** `data/reports/batch-014-orchestrator-notes.md`;
`data/reports/batch-015-orchestrator-notes.md`;
checkpoint `021-batch-013-committed-sleep-and.md`.

## 20. Correct and complete the `cdb` invocation guidance
[APPLY]

**Summary:** Distinguish interactive PowerShell from Python and prevent capturing the
debugger's injected break-in thread as the hung compiler.

**Current text:** `SKILL.md:518-527`:

```text
> **Run `cdb` through `cmd.exe`, not through PowerShell.** From PowerShell, `cdb -c "..."`
> produces no output at all — no error, no diagnostic, exit 0 — which reads as "the debugger
> found nothing". Measured on #3377. Put the whole invocation, redirection included, inside
> `cmd.exe /c`, and drop the `--` separator, which `cmd` does not need and `cdb` sometimes
> takes as a target. While you are there: **do not try to report `ERRORLEVEL` from a `.cmd`
> harness.** `set /a` resets it and a nested `for /f` clobbers it, so a batch file will
> cheerfully print `0` for a run that crashed. Capture exit statuses from the Python that
> launched the process. Invoke a local harness as `.\name.cmd` inside `cmd /c`; bare
> `name.cmd` need not resolve because the current directory is not guaranteed to be on
> `PATH`.
```

**Replacement text:**

```text
> **Choose the `cdb` launcher by the caller.** From an interactive PowerShell command,
> put the complete invocation and redirection inside `cmd.exe /c`; direct PowerShell
> invocation can silently produce no output. From Python, do **not** add another shell:
> pass the `cdb.exe` argv list directly to `subprocess.run` and record
> `subprocess.list2cmdline(argv)` in the capture. Wrapping a quoted debugger path and quoted
> `-c` script in `cmd.exe /c` from Python can make `cmd` report that the debugger path is not
> a command.
>
> When attaching to a live hung process, a bare `kn` initially shows the injected
> `DbgUiRemoteBreakin` thread, not necessarily the compiler's hung thread. Capture all threads
> with `~*kn` or select the target thread explicitly before interpreting the stack.
>
> Do not report `%ERRORLEVEL%` from the same compound `cmd` line: expansion happens at parse
> time, and batch helpers such as `set /a` or `for /f` can overwrite it. Capture the native
> status in Python. Invoke a local `.cmd` harness as `.\name.cmd`; a bare name need not resolve
> because the current directory is not guaranteed to be on `PATH`.
```

**Rationale:** These are measured, caller-specific rules. The live-attach trap produced a
plausible complete stack that contained only the debugger's own break-in thread.

**Evidence:** `data/issues/4036/method-notes.md`;
`data/issues/4384/method-notes.md`;
`data/issues/4614/method-notes.md`;
`data/issues/4723/method-notes.md`.

## 21. Treat source edits and fixed output names as capture invalidation
[APPLY]

**Summary:** Promote the two issue-local cases where a capture remained well-formed after its
input or produced artifact changed.

**Current text:** `SKILL.md:851-854`:

```text
> **Editing a captured repro's comments invalidates the capture.** Assert and diagnostic output
> quotes `Line:` numbers, so tidying a comment after the fact silently desynchronises every
> line number in every file you have already written. Preserve the line count, or re-capture.
> Noticed on #2530.
```

**Replacement text:**

```text
> **Editing any captured input invalidates every capture that used it.** Comment edits can
> desynchronise quoted `Line:` numbers, and a labelled variant can change behavior while
> keeping the same filename and command. The tool checks `cmd.txt` staleness but does not
> persist input-content hashes, so re-run every affected primary and labelled capture after a
> source edit; preserving line count is not enough when semantics changed.
>
> `run --shader` also preserves fixed output arguments such as `-Fo out.cso`. Several
> variants can therefore overwrite the same produced artifact even though their text captures
> have different labels. Give each arm a distinct output path via labelled `--args`, or use a
> matrix harness that owns and records its output names.
```

**Rationale:** A 4605 variant capture silently outlived a three-arm source edit; 2128 found
that all `--shader` corpus arms would overwrite one `-Fo` target.

**Evidence:** `data/issues/4605/method-notes.md`;
`data/issues/2128/method-notes.md`.

## 22. Document that Compiler Explorer annotations alter line-sensitive input
[APPLY]

**Summary:** Keep banner prose from becoming a `-verify` directive or silently shifting quoted
diagnostic lines.

**Current text:** Insert after the `godbolt-note.txt` paragraph at `SKILL.md:1301-1308`.

**Replacement text to add:**

```text
The annotation is compiled input, so it also shifts every source line number reported by a
pane. Do not copy a local line number into a draft after adding the banner; quote the archived
pane output instead. `dxc -verify` scans comments for directive tokens such as
`expected-error`, including explanatory prose, so keep those literal tokens out of
`godbolt-note.txt` and ordinary header comments unless they are intentional verify directives.
```

**Rationale:** The banner moved diagnostic lines in several issues, and one prose mention of
`expected-error` was parsed as a malformed directive and changed the result.

**Evidence:** `data/issues/4520/method-notes.md`;
`data/issues/4615/method-notes.md`;
`data/issues/4722/method-notes.md`.

## 23. Make `reindex` return a failing exit code when it finds unresolved problems
[JUDGE]

**Summary:** The command is described and used as a regression gate, but currently exits zero
after reporting changed verdicts, stale probes, preserved-only fields or evidence gaps.

**Current text:** `scripts/triage.py:3063-3093` ends with:

```python
    if not (stale or changed or gaps or preserved):
        print("every probe re-scores as captured, none are stale, and no "
              "issue is missing required evidence")
```

**Replacement text:**

```python
    problems = stale or changed or gaps or preserved
    if not problems:
        print("every probe re-scores as captured, none are stale, and no "
              "issue is missing required evidence")
    return 1 if problems else 0
```

Then replace the clean-run sentences in `SKILL.md` and `README.md` with:

```text
A clean run prints `every probe re-scores as captured, none are stale, and no issue is
missing required evidence` and exits 0. Unresolved re-scoring differences, stale captures,
database-only preserved fields or evidence gaps exit 1. `--accept` clears only the
re-scoring differences it explicitly restamps.
```

**Rationale:** A shell pipeline can currently continue after a serious reindex finding. Whether
database-only preserved fields should also fail is the trade-off requiring judgement.

**Evidence:** `scripts/triage.py:2889-3093`; parser exit propagation at
`scripts/triage.py:3282-3287`.

## 24. Make `render_comments.py` reject malformed report skeletons
[JUDGE]

**Summary:** Avoid a successful-looking no-op when a fresh report omits the exact splice
headings.

**Current text:** `scripts/render_comments.py:70-76`:

```python
    if START in text:
        head, _, rest = text.partition(START)
        _, _, tail = rest.partition(END)
        text = head + section + END + tail
    else:
        text = text.replace(END, section + END, 1)
```

**Replacement text:**

```python
    if START not in text or END not in text:
        sys.exit(
            f"{os.path.basename(report)} must contain both {START!r} and "
            f"{END!r} before comments can be rendered")
    if text.index(START) > text.index(END):
        sys.exit(f"{START!r} must appear before {END!r} in "
                 f"{os.path.basename(report)}")
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    text = head + section + END + tail
```

After the render command in `SKILL.md`, add:

```text
The report skeleton must contain the exact headings `## Proposed issue comments` and
`## Caveats`, in that order; the renderer refuses any other shape.
```

**Rationale:** With neither marker present, the current `replace` changes nothing and the
script still prints a success message. Requiring the headings is a small but real report-format
contract.

**Evidence:** `scripts/render_comments.py`.

## 25. Correct the README inventory and issue-file semantics
[APPLY]

**Summary:** Make the pickup guide list the files and meanings a fresh collation actually
depends on.

**Current text:** `README.md:10-15`:

```text
scripts/            triage.py, test_predicates.py, render_comments.py,
                    render_overview.py
```

The issue table currently says:

```text
| `variant-*.txt` | a *control* or translated variant — deliberately not scored by `match.json` |
| `manual-case-*.txt` | output captured by hand, where the repro is not a `dxc` invocation |
```

It omits `method-notes.md`, the Godbolt configuration files and `release-policy.json`.
`README.md:71` also defines `not-compiler-verifiable` only as:

```text
| `not-compiler-verifiable` | judging it needs a GPU, driver or runtime, not a compiler |
```

**Replacement text:** Replace the layout entry with:

```text
scripts/            triage.py, test_predicates.py, check_paths.py,
                    render_comments.py, render_overview.py
```

Replace the entire issue-file table with:

```text
| file | what it is |
| --- | --- |
| `expected.md` | what "this reproduces" means, **written before anything was run** |
| `repro.hlsl`, `cmd.txt` | the repro, and the exact arguments every compiler receives |
| `cmd-as-filed.txt` | present when `cmd.txt` deliberately departs from the report |
| `match*.json` | symptom predicates, each with a `note` justifying it |
| `out-<compiler>[--<predicate>].txt` | a primary probe; header records exe, command, exit, predicate and verdict |
| `variant-*.txt` | a labelled control or translated variant, scored by its `# match:` predicate and checked against `# expect:`, but never treated as the primary repro probe |
| `manual-case-*.txt` | output captured outside a direct `triage.py run`; generate it from a committed issue-local harness where possible and keep the generator beside it |
| `godbolt-note.txt`, `godbolt.txt`, `godbolt-source.txt` | the CE annotation, pane specification and optional presentation source |
| `release-policy.json` | an explicit, validated per-issue prerelease opt-in |
| `method-notes.md` | worker observations for collation to promote, reject or supersede |
| `notes.md` | what was tested, what happened, and the assessment |
| `comment.md` | a **draft** comment for a maintainer to review — never posted by this skill |
| `verdict.json` | the recorded verdict; the database is rebuilt from these |
| `issue.json` | the issue as it read at triage time |
```

Replace the status row with:

```text
| `not-compiler-verifiable` | compiler output is not the right instrument; use GPU/driver/runtime, build/package, metadata or process evidence instead |
```

**Rationale:** The current variant row is false — variants are re-scored — and the missing
`method-notes.md` row hides the file most likely to strand a lesson. The status wording is
narrower than SKILL.md and the measured build/release-metadata cases.

**Evidence:** `scripts/triage.py:2640-2723,2958-3000`;
`data/reports/batch-010.md`; `data/reports/batch-012.md`.

## 26. Replace `triage.py`'s pre-migration module docstring
[APPLY]

**Summary:** The script still claims the workspace defaults outside the repo and advertises
only the early command set.

**Current text:** `scripts/triage.py:7-9`:

```text
The workspace lives outside the DXC repo (set DXC_TRIAGE_ROOT, default
~/dxc-triage) and holds a SQLite index plus per-issue evidence, so a long pass
can be stopped and resumed.
```

**Replacement text:** Replace the complete module docstring with:

```python
"""Tooling for evidence-backed, report-only DXC issue triage.

Committed evidence defaults to `<skill>/data`; machine-local release binaries and the derived
SQLite index default to `<skill>/.cache`. Override them with `DXC_TRIAGE_ROOT` and
`DXC_TRIAGE_CACHE`.

Common commands, run from the skill root:

  python scripts/triage.py init
  python scripts/triage.py reindex
  python scripts/triage.py audit [--issue N] [--collated]
  python scripts/triage.py catalog [--seed-from PATH]
  python scripts/triage.py compiler --id main-debug --exe PATH --commit SHA
  python scripts/triage.py fetch --issue N --batch batch-NNN
  python scripts/triage.py run --issue N [--compiler ID] [--match FILE]
  python scripts/triage.py bisect --issue N [--linear] [--repeat N]
  python scripts/triage.py godbolt --issue N
  python scripts/triage.py labels [--refresh] [--issue N]
  python scripts/triage.py verdict --issue N ...
  python scripts/triage.py expect --issue N --capture FILE --expect VALUE
  python scripts/triage.py status
  python scripts/triage.py sql "SELECT ..."

GitHub access is read-only: the tool fetches issue, release and label data and never edits,
labels, comments on or closes an issue.
"""
```

**Rationale:** This is strictly stale embedded documentation; the path constants and parser
already implement the replacement text.

**Evidence:** `scripts/triage.py:35-60,3117-3288`.

## 27. Add a role-oriented reader map near the top
[JUDGE]

**Summary:** Preserve the hard-won detail while making a 1,917-line procedure skimmable without
skipping the wrong phase.

**Current text:** After the opening paragraph, `SKILL.md` moves directly into `## Hard rules`,
then spends roughly 330 lines on rules, session design and setup before step 1. Step 10 is a
batch-level action placed between per-issue steps 9 and 11.

**Replacement text to add before `## Hard rules`:**

```text
## Reader map

| role | read first | execute |
| --- | --- | --- |
| orchestrator/open | Hard rules; How much should live in one session?; Setup; Selecting a batch | select issues, refresh labels, verify ground truth, dispatch workers |
| per-issue worker | Hard rules; Briefing a per-issue worker; Per-issue workflow steps 1–9 and 11 | write only its issue directory; run `audit --issue N` after recording the verdict |
| collation | What `reindex` guarantees; Test reproducibility; step 10; Batch report; Cross-batch overview | read every issue artifact and method note, review drafts, stamp review provenance, write the report |

### Phase checklist

1. **Open:** verify the public ground-truth commit and compiler version; refresh labels; select
   the batch.
2. **Per issue, in parallel:** pre-register the symptom; build repro and controls; run current
   and release probes; publish or deliberately skip CE; draft; write notes and verdict; audit.
3. **Collate, single writer:** read artifacts without relying on worker summaries; apply the
   independent review; resolve cross-issue claims; promote method lessons; run the appropriate
   quiescent reindex/overview sequence; write the report.

The detailed sections below are normative when this checklist and a later rule differ.
```

**Rationale:** Length is not the defect; role interleaving is. The phase table is correct but
not a navigation aid, and the step-10/step-11 numbering invites a first-time worker to perform
batch review before recording its own verdict.

**Evidence:** `SKILL.md` structure; batch timing/length analysis in checkpoint
`021-batch-013-committed-sleep-and.md`.

## What this skill gets right

- The report-only boundary is unusually explicit and backed by measured failure cases,
  including commit-message cross-references as an external side effect.
- Writing `expected.md` before running, preserving contradictory predictions, and separating
  status from history are load-bearing controls against hindsight.
- `internal_failure`, `invalid-probe`, positive anchors, declared controls and per-release
  capability checks encode the most consequential wrong-answer lessons from the pass.
- The committed-evidence/derived-cache split, `reindex` re-scoring and read-only per-issue
  audit make results independently inspectable rather than conversation-dependent.
- One isolated worker per issue plus a fresh collation reader is the right ownership model;
  the single-writer rule and per-tag cache lock make it practical.
- The Compiler Explorer guidance correctly treats comparison panes, annotations, stage
  translations and controls as measurement problems rather than presentation polish.
- The draft warning, AI disclosure, different-model review, blind re-derivation for
  `close-fixed`, and separate review of compressed fields are all worth preserving.
- The high bar for `text_stale`, stable-release prerelease policy, and action-oriented generated
  overview prevent several socially or operationally costly overclaims.

## Open questions

- Should pipelining be a supported mode in the skill, or remain an orchestrator-specific
  exception? The safe sequencing differs materially.
- Which legacy free-form `history`, `triaged_by` and `reviewed_by` values should be migrated
  after their explanatory prose is preserved elsewhere?
- Should `--expect` on non-variant `out-*.txt` captures be rechecked by `reindex`, or should the
  CLI reject `--expect` without a labelled variant? It currently accepts the header but only
  variant expectations are revalidated.
- Should `audit --issue N` report a missing `verdict.json` as a gap? Before a verdict exists it
  can still print “no missing evidence,” which has misled workers.
- Should issue-local artifact/history harnesses be imported into a first-class `run`/`runs`
  abstraction, or is an explicit “not automatically rechecked” caveat sufficient?
- How much normalization may a shared quote checker perform beyond ANSI stripping before it
  stops proving byte-faithful quotation?
- Should the blind re-derivation agent see `expected.md`? One note showed that it can accrete
  mechanism and candidate-fix information, weakening attribution independence.
