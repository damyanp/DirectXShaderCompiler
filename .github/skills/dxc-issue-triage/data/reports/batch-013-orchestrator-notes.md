# Batch 013 — orchestrator notes for the collation session

You are collating batch 013. You did not see the dispatch conversation; this file is the only
channel from the orchestrator to you. Everything else must come from `data/issues/<nnnn>/`.

## The batch

| Issue | Opened | Labels at dispatch | Title |
| --- | --- | --- | --- |
| 3531 | 2021-03 | — | No debug info for locally-declared dynamic resources (SM 6.6) |
| 3535 | 2021-03 | — | Retrieving reflection data for structs used in input signatures |
| 3835 | 2021-06 | — | Internal compiler error on shader validation |
| 3863 | 2021-07 | — | Support `-H` and `-P` at the same time |
| 3872 | 2021-07 | — | SV_ShadingRate allowed in certain shader signatures where it shouldn't be |
| **5293** | **2023-06** | **bug** | **Assert in `template` + `out` functions when it has local variables** |

## 5293 is a user-directed exception — read this before you plan anything

**The repository owner added 5293 to this batch by hand, mid-flight, and asked that it be
highlighted in the report.** It is not part of the oldest-100 sweep and was not selected by the
usual oldest-first rule. Three consequences, all mandatory:

1. **Highlight it prominently in `reports/batch-013.md`.** Give it its own section near the
   top, not a row in the middle of a table. The reason it was pulled in is that **a new comment
   arrived on it today** (`2026-08-10T12:29:38Z`, from `rbertin-aso` at Asobo) reporting a
   Release crash and a Debug LLVM assert on templated code, and stating *"it was not crashing
   before"*. A studio appears to be blocked on it right now.
2. **It must NOT count toward the oldest-100 progress figure.** The target set is the oldest 100
   open issues, spanning #708–#4763; 5293 is outside it. Count it separately, exactly as the
   four deliberately-mixed recent issues (8527, 8725, 8732, 8737) are already counted separately
   in `overview.md`. Do not let the percentage drift.
3. **Nothing may appear publicly on this issue.** This applies to every issue, but the owner
   restated it specifically for this one because the thread is actively watched by external
   parties *today*. No `gh issue edit|comment|close|reopen|label`. And **no `#5293` or issue URL
   in any commit message** — that creates a permanent, undeletable timeline cross-reference the
   moment a branch is pushed. Bare numbers only.

Its shape is also the hardest one to score correctly, so scrutinise that worker's output hard:
the reporter describes **two different manifestations** (Release crash, Debug assert), which is
the textbook `any_of` composition case; and *"was not crashing before"* is a regression claim
that an endpoints-only bisect will miss. Check the worker actually did both rather than picking
one signature and one bisect mode.

## Sampling bias — state this in the report

Batches 011 onward are drawn **exclusively from the oldest 100 open issues**, at the owner's
request for exhaustive coverage; SKILL.md's advice to mix ages is deliberately suspended for
age. 5293 is the single exception, added by hand.

Unlike batch 012 — which was enhancement-heavy and exercised no crash path at all — this batch
**does** exercise the crash path, twice (3835 and 5293), plus a missing-diagnostic issue (3872),
a debug-info issue (3531), a reflection issue (3535), and a preprocessor option issue (3863).
Say so; it is a materially better-balanced batch than 012 and its method conclusions carry
further.

## Ground truth and how to cite it

- Registered compiler `main-debug` self-reports `1.9.0.5433 (triage, ab5400907)`.
- **`ab5400907` is fork-local and resolves nowhere public. It must never appear as a citation.**
  The correct public citation is **`13730886e`**; see `data/reports/provenance-correction.md`.
- Verbatim `--version` or `!llvm.ident` output inside a draft may still show `ab5400907` — that
  is captured evidence, not a citation. Check every draft in this batch for the distinction.

## This is the first batch to run under batch 012's tooling fixes — verify they behaved

Batch 012 changed how probes execute. This batch is the first real exercise of that code, so
treat the following as findings to look for, not background:

- **Probe isolation and input-mutation detection.** Every probe now runs in a scratch copy, and
  a run that modifies a file declared as one of its inputs raises
  `probe modified its own input evidence`. If any worker hit that, it is a **real finding about
  the command**, not a tool fault — surface it in the report rather than burying it.
- **Behavioural spelling validation.** A spelling retry is now accepted only on positive proof
  the option was honoured, not on the absence of an `Unknown argument` diagnostic. Check whether
  any probe in this batch was consequently kept as `invalid-probe` that would previously have
  been silently scored — especially 3863, which is a `-P` option issue and therefore lands
  exactly on the changed code.
- **The clean-endpoints warning.** `bisect` now warns when both endpoints are clean but the
  issue's filing date lies inside the probed range. If it fired anywhere, say so and confirm the
  worker responded with `--linear` rather than accepting `never-repro'd-in-releases`.

Run `reindex` **first**, before anything else, and check all four of its reports. If it moves
nothing, prove why rather than accepting silence.

## Your job

1. **`reindex` first.** Any output is a finding.
2. **Cross-issue consistency.** Two pairs need explicit checks:
   - **3863 against 3044** (batch 012). Both are preprocessor option-surface issues, and 3863's
     worker was told to determine whether they are duplicates. Verify that determination against
     3044's own artifacts and make sure the two recommendations do not contradict each other.
   - **3535 against 2952** (batch 011). Both are "reflection does not expose X". Same check.
   Consult `data/reports/overview.md` for the 56 issues already triaged.
3. **Run the step-10 independent draft review** on a *different* model (previous batches used
   `gpt-5.6-sol`). Apply with judgement, not wholesale; SKILL.md records what that review
   reliably gets right and what it reliably gets wrong. Record your decisions.
   **5293's draft deserves the most care in this batch** — the thread is live, a studio is
   blocked, and the draft must not over-claim. In particular, a Debug-only measurement must not
   be generalised to Release, and no fix or timeline may be promised.
4. **Blind re-derivation is MANDATORY for any issue recommended for closure** (`close-fixed`).
5. **Promote method lessons** from every `method-notes.md` into SKILL.md. Workers were forbidden
   from touching shared state, so every tooling fix they identified is unapplied and waiting for
   you. Applying one mid-batch would invalidate already-finished workers.
6. `python scripts/render_comments.py <batch>` — **query the DB for the exact batch label
   first**, it has been inconsistent historically (`002` vs `batch-002`) — then
   `python scripts/render_overview.py`. **`overview.md` is a standing deliverable.**
7. Write `reports/batch-013.md`, with 5293 highlighted as described above.

## Gates before you hand back

- `git status` shows nothing changed outside `.github/skills/dxc-issue-triage/`.
- `python scripts/test_predicates.py` passes.
- `python scripts/triage.py audit` passes.
- `python scripts/check_paths.py` passes.
- No staged binaries. `git add -An` **quotes** paths, so a regex anchored with `$` on the
  extension silently never matches — that exact mistake gave a false negative once.
- Every `verdict.json` has a non-empty `reviewed_by`, and none self-reviewed.
- No `ab5400907` in any citation position.

## Standing constraints

- **Read-only on GitHub.** Drafting is in scope; posting is not. Never `gh issue edit|comment|
  close|reopen|label`.
- **Never modify DXC source.** Only `.github/skills/dxc-issue-triage/` may change.
- **Do not commit and do not push.** The orchestrator commits; the owner has not authorised a
  push.
- **No history rewriting** — it orphans commits without retracting what they already published.
- **Never write an issue reference (`#NNNN`, `GH-NNNN`, an issue URL) where it could reach a
  commit message.** Bare numbers only.
- If you are genuinely stuck, say so and stop. Do not guess a verdict.

---

# Post-run orchestrator findings

Written after reading all six workers back and **verifying their claims against artifacts
rather than their prose**. Worker summaries have twice in earlier batches been imprecise while
`match.json` / `manual-case-*.txt` were correct. Trust the files.

All six verdicts are `repros`. **No closable issue in this batch.** Verified independently:
all six record `triaged_with_commit = 13730886e` (the public SHA, not the fork-local one).

## 1. HIGHEST PRIORITY — 5293's draft must lead with "your own paste does not reproduce"

Verified by a declared `# expect:` assertion pair, so `reindex` re-checks it:

| variant | exit | verdict | `# expect:` |
| --- | --- | --- | --- |
| `repro-asobo.hlsl` (the function **as quoted by the reporter**) | `0` | `no-repro` | `no-match` |
| `repro-asobo-scalar-out.hlsl` (one scalar `out` added) | `0xE0000001` | `repro` | `match` |

`isTrackedVar()` requires `isScalarType()`, and the quoted `out T2` is a 2-vector, so the
pasted function is *not* the one crashing them. Anyone spot-checking their paste concludes
"cannot reproduce" and the report gets wrongly dismissed. **This must be the first thing the
draft says**, phrased as help ("your trigger is a different function — here is the shape that
does it"), never as a correction.

Also give them the second, independent trigger: crossing ~29 locals flips latent to crash with
no compiler change at all (`PackedVector` inline capacity `SmallNumDataBits=57`). That is a
second valid explanation for "it was not crashing before" and does not require the regression
story to be right.

## 2. Cross-batch correction — 3863 falsifies 3044's method note 8 (batch 012, already committed)

3044 recorded, **from reading source**, that "`-H` cannot run alongside `-P`". 3863 **measured
the opposite** through `IDxcCompiler3::Compile`: `DXC_OUT_REMARKS` already carries the include
trace under `-P` (86 bytes; empty without `-H`). The trace is captured and then simply never
printed, because `DxcContext::Preprocess()` never asks for REMARKS.

Actions: correct `data/issues/3044/method-notes.md` in place (note it was corrected and by
what measurement), check whether that claim was promoted into `SKILL.md`, and make sure 3044's
`comment.md` does not repeat it. This is the batch's clearest instance of the general rule:
**a neighbouring issue's source reading is a hypothesis; only its measurements are inherited.**

## 3. `run --shader` unusable for multi-invocation `cmd.txt` — second independent hit

`retarget_cmd` (`triage.py:925-944`) exits `no source file to replace in: <line>` for any line
without a `.hlsl` token. 3044 (batch 012) and 3863 (batch 013) hit this independently, in
different batches, with no shared context. Two hits promotes it from annoyance to defect.
Suggested fix: skip lines with no source rather than failing the whole command.

## 4. Two fake regressions, both caught by self-test clauses — promote this to SKILL.md

- **3535**: `bisect --linear` showed v1.4.1907 `no-repro` then `repro` from v1.5.2010. That is
  the *reflection-metadata relocation* out of DXIL into `STAT`, not a behaviour change.
- **3872**: `match.json` scored v1.4.1907 `no-repro`. The clause matrix showed only the
  **disassembler-spelling** clauses flipped (2019 prints `NONE`, trunk prints `SHDINGRATE`)
  while every acceptance clause held and the `i8 29` metadata was identical.

Both were caught because the predicate carried a per-release self-test clause, and both would
otherwise have been published as regressions. The generalisation to promote: **a predicate
reads the instrument as well as the behaviour, and the instrument changes across releases.**
Read self-tests per-release, not just on trunk.

## 5. New invalid-probe class — `Unknown HLSL version: 2021`

5293's four oldest releases exit `1` with `dxc failed : Unknown HLSL version: 2021`. That is an
ordinary driver rejection, not a negative result, and `bisect` does **not** currently flag it as
`invalid-probe`. Same family as the profile/feature cases already handled. Worth adding.

## 6. invalid-probe can be triggered by an *unrelated* option, silently shortening a range

3835: `-Wno-parentheses-equality` in `cmd.txt` was demoting v1.4.1907 to `invalid-probe` and
hiding the bisection floor. Proven inert and dropped; history then extended **two years earlier
than the report**. Check that a probe is invalid because of the thing under test.

## 7. Tooling defects found but deliberately NOT fixed by workers (shared state)

- `triage.py sql` raises `sqlite3.OperationalError` on `IS NOT NULL AS cached` (3531).
- `releases` has no `seed_local` column (hit independently by 3535 and 3835).
- `godbolt` overwrites the verify file each run; `ce_args` silently links only line 1 (3872).
- `-Fc -` creates a literal file named `-` on Windows (3835).

## 8. Duplicate determinations already made — verify the reasoning, do not redo the work

- **3863 vs 3044: not duplicates.** 3044 = an option that does not exist + a hardcoded library
  field, changing the `-P` **output file**. 3863 = an option that exists, is parsed under `-P`,
  already captured, changing only **console output** (`.i` byte-identical). Neither fixes the
  other.
- **3535 vs 2952: consistent, not duplicates.** 2952 = data is in the container, missing an API
  field. 3535 = data is discarded at lowering, so preservation *and* exposure are needed.

## 9. SKILL.md internal inconsistency, flagged by 3535

Step 9 asks for an HTML-comment draft marker; the committed-banner rule requires a rendered
`> [!WARNING]` callout, because GitHub renders `.md` and HTML comments are invisible to exactly
the audience that needs the warning. 3535's `comment.md` currently carries **both**. Resolve the
instruction and make the batch consistent.

## 10. Environment note that may affect timing evidence

This machine is a Dev Box whose host suspends it nightly (Hyper-V `vmicshutdown` calling
`SetSuspendState`; not preventable from inside the guest). Agent elapsed times are wall-clock
and include suspension, so **do not read a long elapsed time as a slow probe**. If any probe's
wall-clock duration is ever used as evidence, check it does not span a suspend.
