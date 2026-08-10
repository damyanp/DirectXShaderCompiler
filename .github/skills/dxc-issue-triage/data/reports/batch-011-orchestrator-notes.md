# Batch 011 — orchestrator notes for the collation session

You are collating batch 011. You did not see the dispatch conversation; this file is the only
channel from the orchestrator to you. Everything else you need must come from
`data/issues/<nnnn>/`.

## The batch

| Issue | Opened | Labels at dispatch | Title |
| --- | --- | --- | --- |
| 6727 | 2020-04 | enhancement, high-impact | Support IMul/UMul/UDiv with two outputs from HLSL |
| 2952 | 2020-06 | reflection | Expose ray payload size / function type through Reflection |
| 3362 | 2021-01 | bug | pack-optimized issue with domain shader |
| 3883 | 2021-07 | bug, crash, incorrect-code | DXC Compiler Crash |
| 3927 | 2021-09 | spirv | [SPIR-V] Not all unnecessary bindings are eliminated |

Chosen as a deliberate mix — enhancement, reflection API, signature packing, crash, SPIR-V —
so that bisection, the `internal_failure` predicate and the invalid-probe detector are all
exercised rather than a single code path being sampled five times.

## Sampling bias — state this in the report

Batches 011 onward are drawn **exclusively from the oldest 100 open issues**, at the user's
explicit request for exhaustive coverage of that set. SKILL.md's guidance to mix ages is
therefore **deliberately suspended** for age, though not for category. Consequence: verdicts
from this batch describe the 2020–2022 backlog and **do not generalise** to recent issues.
Say so in `reports/batch-011.md`.

## Ground truth and how to cite it

- Registered compiler `main-debug` self-reports `1.9.0.5433 (triage, ab5400907)`.
- **`ab5400907` is fork-local and resolves nowhere public. It must never appear as a citation.**
- The correct public citation is **`13730886e`**. See `data/reports/provenance-correction.md`
  for the full argument and for what was deliberately *not* rewritten.
- Verbatim `--version` output quoted inside a draft may still show `ab5400907` — that is
  captured evidence, not a citation. Where such output sits next to a citation, the draft
  should carry a one-line clause reconciling the two. Check the batch-011 drafts for this.

## Your job

1. **`reindex` FIRST, before anything else.** It re-derives every verdict by running today's
   predicate code over archived output, so it retroactively applies any lesson learned during
   this batch to issues triaged in earlier ones. Check all four of its reports: changed
   verdicts, stale captures, evidence gaps, and control-assertion failures. Any output at all
   is a finding, not noise.
2. **Cross-issue patterns.** Nothing in this batch was picked as a suspected duplicate pair,
   but 6727 (integer intrinsic exposure) and 2952 (reflection exposure) are both
   "the capability is absent from the surface API" requests — check whether their verdicts and
   recommendations are mutually consistent, and whether either is really a duplicate of an
   already-triaged issue. Consult `data/reports/overview.md` for the 50 already triaged.
3. **Run the step-10 independent draft review** on a *different* model (previous batches used
   `gpt-5.6-sol`). Apply it with judgement, not wholesale — SKILL.md documents what it
   reliably gets right and what it reliably gets wrong. Record the decisions in the report.
4. **Blind re-derivation is MANDATORY for any issue recommended for closure** (`close-fixed`).
   That is the verdict most likely to be acted on unexamined.
5. **Promote method lessons** from each issue's `method-notes.md` into SKILL.md. The per-issue
   workers were forbidden from touching shared state, so any tooling fix they identified is
   *unapplied* and waiting for you. Applying a tooling fix mid-batch would have invalidated
   verdicts from workers that had already finished, which is why it was deferred to you.

   **Promote this one too — it is currently written down nowhere durable, and it is the rule
   whose breach produced the only externally-visible noise this exercise has ever caused.**
   Add a section to SKILL.md's *Hard rules* covering commit hygiene:

   > Writing `#NNNN`, `GH-NNNN`, or an issue/PR URL in a **commit message** creates a real
   > cross-reference that appears on the issue timeline as soon as the branch is pushed. That
   > is indistinguishable from commenting on the issue, and it is permanent: the timeline
   > event **cannot be deleted**, and it survives even if the commit is later orphaned by a
   > history rewrite. Commit `8b61ec72e` ("triage: batch 006 (#2128, #2331, ...)") put
   > references on five issues this way; rewriting history removed the commit from the branch
   > but left every reference in place, still displaying the subject line.
   >
   > Use **bare numbers** in commit subjects: `triage: batch 011 (6727, 2952, ...)`.
   > Issue numbers in *file contents* are safe — only commit messages and issue/PR bodies
   > create references. Verify with a regex before committing, and **validate the regex in
   > both directions**: positive controls (`fixes #3377`, `GH-3429`) must match, and negative
   > controls (`batch 011 (6727, 2952)`, a bare commit SHA) must not.

   Note also, for the *Hard rules* section, that history rewriting is now forbidden on this
   branch: it orphans commits without retracting anything they already published.
6. `python scripts/render_comments.py batch-011`, then `python scripts/render_overview.py`.
   **`overview.md` is a standing deliverable and must be regenerated after every batch.**
7. Write `reports/batch-011.md`.

## Gates before you hand back

- `git status` shows nothing changed outside `.github/skills/dxc-issue-triage/`.
- `python scripts/test_predicates.py` passes.
- `python scripts/triage.py audit` passes.
- No absolute machine paths in committed artifacts. Check BOTH the literal backslash form and
  the **JSON-escaped** form, in which every separator is doubled. The escaped form does not
  contain the literal single-backslash string, so a naive scan for the plain form misses it
  entirely — that is how 44 occurrences hid from the first sweep. Search for the drive-letter
  prefix with the separator matched as either one or two backslashes.
- No staged binaries. Note that `git add -An` **quotes** the paths it prints, so a detection
  regex anchored with `$` on the extension silently never matches — this exact mistake gave a
  false negative once already.
- Every issue has a non-empty `reviewed_by` in `verdict.json`.
- No `ab5400907` in any *citation* position.

## Corrections and findings the orchestrator owes you

These arose after dispatch. The per-issue workers cannot know them; you must act on them.

**1. A brief I gave a worker was wrong, and the worker caught it by measuring.**
I told the #3927 worker that `v1.4.1907` and `v1.5.2003` return `0x80070057` for `-spirv`.
They do not: both exit **1** with `SPIR-V CodeGen not available`, confirmed with a control
(a trivial `SV_Target0` shader fails identically). SKILL.md's own text is correct; my brief
embellished it. If any earlier batch report repeats the `0x80070057` claim, correct it.

**2. `bisect` under-reports invalid probes — likely affects earlier batches.**
On #3927 there were **two** invalid probes, but `bisect` reported **one**. It trimmed and
counted `v1.4.1907`, while `v1.5.2003` was never probed at all and so was never mentioned;
the worker found it only by running it by hand. A release that is silently *not visited* is
indistinguishable in the output from one that was visited and passed.

This matters beyond one issue: **every "invalid probes: N" figure in every prior batch report
may be an undercount**, and the floor claims derived from them ("no release before X could
ever have shown this") may be weaker than stated. Please:
- read `data/issues/3927/method-notes.md` for the precise mechanism;
- decide whether this is a `triage.py` defect worth fixing (you may change shared state; the
  workers could not);
- if you fix it, **re-run `reindex` afterwards** and check whether any prior history verdict
  moves — that is exactly what `reindex` exists for;
- state the residual uncertainty in `batch-011.md` rather than quietly correcting the number.

**3. A SPIR-V-specific form of the `godbolt-note` trap.**
CE embeds the shader source into the SPIR-V module as `OpSource`, so a banner telling the
reader to "search for `%Tex1`" makes that token appear in the pane whether or not codegen
emitted it — four false hits on #3927. Banners for SPIR-V issues must name a *structural*
line (e.g. an `OpDecorate`), never a token that also occurs in the source text.

**4. Two concrete `triage.py` defects, both found by the #2952 worker. Please fix both.**

*(a) `bisect` should refuse to run against a harness.* This trap has now produced a wrong
answer, or nearly done so, on **six** issues. The failure is silent and maximally deceptive:
`bisect` substitutes each release's real `dxc.exe` for the harness, every probe scores
`no-repro`, and it confidently reports **"never repro'd in any release"** — which for a
feature request is exactly the plausible-sounding inverse of the truth. The #2952 worker
avoided it only because the brief warned them.

The suggested guard is cheap and should end the whole class: **have `bisect` hard-error when
the registered compiler's executable is not a `dxc` binary**, directing the user to an
explicit release matrix instead. Prefer erroring to warning — a warning in a long log is how
this survived six issues. Note that `measure.py --history` (written for #2952) and the #3237
release-matrix pattern are the sanctioned replacements; consider whether one of them should
be promoted into `scripts/` as a first-class command rather than re-derived per issue.

*(b) `fetch` does not record the issue author.* `issue.json` captures commenters but omits
the **issue author** — the single handle a draft comment is most likely to need. Every worker
must therefore make a second, undocumented `gh` call, and a worker that forgets is one step
from inventing a handle. That directly undermines the *"never invent an `@mention`"* hard
rule, whose whole purpose is that these drafts notify real people. Capture the author in
`fetch`, and **re-check the already-fetched issues**: if `issue.json` lacks the author for the
50+ issues triaged so far, any draft that credits a reporter was written from a handle
obtained out of band and should be spot-checked.

**5. When the finding is an *absence*, make the instrument prove it can detect a *presence*
in the same run.** Worth promoting to SKILL.md: #2952 and #3927 reached this independently
from opposite directions.

- #2952's finding was "no field exposes payload size". A search that finds nothing is
  indistinguishable from a search that is broken, so the worker required a
  `field-search-selftest=pass` clause — the same enumeration must locate a field known to
  exist — as part of the predicate. A broken instrument then fails loudly instead of
  manufacturing a clean absence.
- #3927's finding was the mirror image, "these bindings are still present", and the worker
  noted that a **presence** predicate fails in the *fix-inventing* direction: it can be
  satisfied by output a failed compile never produced, or by a shader that never mentioned
  the resource.

SKILL.md documents the control discipline for absence (*"a predicate that matches everything
is indistinguishable from a bug that reproduces everywhere"*). Extend it to state both
directions, and to require the self-test clause live **inside** the predicate rather than in
prose — so `reindex` re-checks it on every future pass instead of it decaying into a claim
nobody re-runs.

**6. `#3362` needs blind re-derivation and unusual care with tone — treat it as if it were a
`close-fixed`.**

The worker concluded `does-not-repro` on the basis that **the reporter compared two different
things**: the PS disassembly in their attachment was produced *without* `-pack-optimized`
(the command line is embedded in the dump), while the DS used it. The worker reproduced the
reporter's exact PS table using *default* packing, and showed `PackOptimized`'s
4-component-first allocation makes their claimed layout impossible under the flag.

SKILL.md mandates blind re-derivation only for `close-fixed`. **Extend it here.** The
technical claim is strong, but "your bug report was a measurement error" is the most
socially costly thing this exercise can say, it lands on a real person's five-year-old
issue, and it is unfalsifiable to a casual reader who will not re-run anything. Have the
re-derivation done without sight of the worker's conclusion, and confirm independently that
the attachment's embedded command line says what the worker says it says.

Then check the draft's tone specifically: it must report *what the two dumps were compiled
with* and let the reader draw the conclusion. No verdict on the reporter. The recommendation
(`usability`/`docs`/`diagnostic` — the flag's DXIL contract is documented only in `--help`)
is the constructive part and should lead.

**7. An `invalid-probe` of "Unknown argument" may mean a spelling difference, not an absent
feature — and this retroactively threatens earlier history claims.**

On #3362, `v1.4.1907` was demoted to `invalid-probe` purely because it spells the flag
`-pack_optimized` / `/pack-optimized`. Re-probed with the accepted spelling it produces
layouts identical to `main`. Believing the demotion would have supported a false
"the feature did not exist that far back".

This is the same shape as finding 2 (`bisect` under-counting invalid probes): **an
unexercised release is being read as evidence.** Together they mean any prior verdict of the
form *"no release before X had this"* rests on a probe that may never have run. Please:
- add a spelling re-probe (`-`/`_`/`/` variants) before any `Unknown argument` demotion is
  believed, ideally in `triage.py` so it is not left to each worker's diligence;
- grep prior batch reports for feature-absence claims resting on `Unknown argument`
  demotions, and re-check or soften them;
- note that #3362 also demonstrates the positive discipline: **run the positive control
  across the whole release set**, because otherwise `never-repro'd` is indistinguishable
  from a dead predicate.

**8. `#3883` — I verified the predicate myself; it is sound. Do not "fix" it.**

The worker's summary says the predicate is status-code based and "never message text", which
reads as a contradiction with its own finding that `v1.7.2207+` returns plain E_FAIL
(`0x80004005`) — a code SKILL.md correctly says is *not* an internal failure. I checked.
The captures show E_FAIL accompanied by `error: llvm::cast<X>() argument of incompatible
type!`, and `is_internal_failure` applies `INTERNAL_MARKERS` as a documented backstop after
the status check. I ran the matrix directly:

| input | rc | internal failure? |
| --- | --- | --- |
| `llvm::cast<X>() argument ...` (Windows) | E_FAIL | yes |
| `cast<X>() argument ...` (Linux/CE) | E_FAIL | yes |
| ordinary syntax error | E_FAIL | no |
| `error X4000: ...` | E_FAIL | no |
| DXIL validation failure | E_FAIL | no |
| empty stderr | 0xC0000005 | yes |

So the marker regex `(?:llvm::)?cast<[^>]*>\(\) argument` is genuinely build-agnostic, and a
real fix for #3883 — emitting a proper diagnostic — would correctly score `no-repro`. The
`always-repro'd` verdict stands. The worker's *prose* was imprecise; its `match.json` note is
accurate and says exactly this. Correct the prose in the batch report, not the predicate.

**9. The `v1.5.2003` blind spot — SUPERSEDED BY USER POLICY. Read this box first.**

> **User policy (2026-08-09):** *"releases we've marked as 'prerelease' should be ignored,
> unless a bug is explicitly filed against one of those releases."*
>
> The `bisectable=0` exclusion of prereleases is therefore **correct behaviour, not a
> defect**. Boundaries are expressed in terms of **stable releases**. The worry below — that
> a boundary reported as `v1.5.2010` might "really" be `v1.5.2003` — is **void**, and no
> prior batch needs its history claims reopened on that account.
>
> What survives is only: (a) `bisect` should *state* what it skipped and why, because the
> silence is what cost two workers a hand-run and produced #6727's 20-vs-21 miscount; and
> (b) the carve-out needs implementing — if a reporter **explicitly names** a prerelease,
> that release is in scope for that issue. "Was current when filed" is **not** sufficient.

The original observation, retained because the mechanism is still worth knowing: two workers
(#3927, #6727) independently hand-ran `v1.5.2003` because `bisect` never visited it. The
catalog explains why:

```
tag           build_date   bisectable  prerelease
v1.2.0-alpha  (none)       0           1     <- no asset, correctly excluded
v1.5.2003     2020-03-25   0           1     <- HAS a working cached dxc.exe
v1.5.2010     2020-10-22   1           0
```

`v1.5.2003` is excluded for being **prerelease**, not for being unusable. My finding 2
originally described this as "never visited, indistinguishable from passed"; that mechanism
was wrong, and under the policy above the conclusion is wrong too. Finding 2's *other* half —
`bisect` under-counting genuinely trimmed invalid probes — is unaffected and still stands.

For the record: `.cache/` is fully untracked and gitignored, so the absolute paths the catalog
stores in `cached_path` never reach the repo. Verified — no redaction needed there, and the
released-compiler cache stays local-only as intended.

**10. The `godbolt-note.txt` banner is compiled, and CE embeds the source — confirmed twice.**

#3927 and #6727 hit this independently, so it belongs in SKILL.md rather than in one issue's
notes. CE compiles the banner along with the shader, and DXC embeds source text into the
module (`!dx.source.contents`; CE passes debug flags by default). A banner that names the
token it claims is **absent** makes that token appear in the panes — four false hits on
#3927, and on #6727 the token appeared in both DXC panes.

Rule: **never put a string in the banner that the note asserts is missing.** Name a
structural line instead (an `OpDecorate`, a signature row, an exit code).

#6727 then inverted the same mechanism deliberately, which is worth capturing as a technique:
embedding a token in a source comment and compiling with `-Zi -Qembed_debug` makes an
otherwise unfalsifiable `not_regex` absence clause actually able to fire. That is a general
control shape for absence predicates, and it pairs with finding 5.

## Standing constraints
- **Read-only on GitHub throughout.** Nothing posted, edited, labelled or closed.
- **Never write `#NNNN`, `GH-NNNN` or an issue/PR URL in a commit message** — those create
  real cross-references visible on the issue, which is exactly what this exercise must not do.
  Bare numbers in the subject are fine (`triage: batch 011 (6727, 2952, ...)`). Issue numbers
  in *file contents* are safe; only commit messages and issue/PR bodies create references.
- **Do not commit or push.** The orchestrator commits; the user will say when to push.
- If you are genuinely stuck, stop and say so rather than guessing.
