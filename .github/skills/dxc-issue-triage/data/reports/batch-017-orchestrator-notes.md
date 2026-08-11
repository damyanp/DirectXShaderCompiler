# Batch 017 — orchestrator notes

Findings carried into batch 017's collation, and into the end-of-pass review of the skill.
Batch 017 is the final batch of the oldest-100 pass: 4648, 4666, 4701, 4708, 4710, 4721, 4722,
4723, 4763.

## 1. The `history` taxonomy has no value for "the feature never existed", and the gap causes real misreporting

The accepted values are `always-repro'd`, `fixed-in <tag>`, `regressed-in <tag>` and
`never-repro'd-in-releases`. None of them describes an issue asking for a capability HLSL never
had. 4708 coined **`never-implemented`** rather than use one of them, and was explicit about why:

> Reporting `always-repro'd` would have converted "HLSL never had this" into "DXC broken
> since 2019".

That is exactly right, and it is the same class of error as finding #9 in the batch-016 notes
(a diagnostic-shaped symptom faking a reproduction). The difference is that here the tooling
*forces* the error: there is no correct value to record, so the honest choice is off-taxonomy
and therefore invisible to every query that uses the field.

`never-repro'd-in-releases` is not a substitute — it means the *symptom* was absent, whereas
here the symptom (a rejection) is present everywhere and is correct behaviour.

**Left as `never-implemented` deliberately.** Normalising it to `always-repro'd` would restore
the misreport. The taxonomy needs the extra value; that is a skill change, not a data fix.

## 2. Hand-rolled release enumeration is the single most productive source of factual error in this pass

Two separate wrong facts have now been traced to it:

- **Two cache roots.** `.cache/compilers/releases/` and `build/tools/clang/test/dxc_releases/`,
  neither a superset. Scanning one under-counted a validator floor by two releases (batch 014).
- **arm64 binaries.** Both roots ship `bin/arm64/dxc.exe` beside `bin/x64/dxc.exe`. 15 arm64
  copies are present. On this host they fail to launch, and a failure-to-launch scores as
  whatever the predicate makes of empty output — 4708 caught an early release walk that would
  have **silently manufactured reproductions** from them.

A third shape difference compounds both: the tree layout is not uniform. Seeded trees nest an
extra `dxc_<date>` level, and v1.4.1907 has no `bin/x64/` at all.

**The scale of the exposure:** 26 generator scripts across the pass enumerate releases
themselves. At least three independently rediscovered and documented these traps in their own
comments — `measure-releases.py` ("a naive recursive search also picks arm64 binaries, which do
not run here"), `make-manual-cases.py` ("walking one root silently misses the..."), and
`measure-oldest-hang.py` ("its shape differs between releases"). Three workers solving the same
problem three times, in isolation, is not diligence; it is a missing abstraction.

The catalog already has the right answer — `releases.cached_path` resolves correctly and
contains **no** arm64 entries (verified: the query returns empty). So the fix is to make the
catalog the only supported route: a documented helper that yields ordered, non-prerelease
releases with resolved x64 executables, and a rule in the skill that scripts must not glob the
cache tree. Every one of these errors is invisible in the output — the run simply reports fewer
releases, or more reproductions, than the truth.

## 3. Evidence that exists only in the terminal is not evidence

4701 found three cited facts — the `-fcgl` static-linkage claim, the `-Odump` pipeline, and
`-O3` being the default — that appeared in `notes.md` but had never been captured to disk. They
were true, and they were sourced from a real command, but nothing on disk showed it. Caught by
a late sweep and re-captured.

This is the same failure mode as the `reviewed_by` gap in batch 014: work that genuinely
happened, leaving no trace, and therefore indistinguishable from work that did not. The rule
that catches it is mechanical — **if a claim names a command, its output must be in a capture
file** — and it should be part of the pre-verdict check rather than a habit.

## 4. Choosing a metric that only exists in newer releases manufactures a regression at the newest point

4701 nearly used `NumBytesGroupSharedMemory` as its history metric. It is a PSV field added
after v1.9.2607, so every older release would have reported it absent and the scan would have
shown a clean break exactly at the newest release — a textbook regression that never happened.
A fixed-reader cross-check proved the field absent from every release container and killed it.

Generalised: **any metric read out of a container or a reflection interface must itself be
history-checked before it is used to measure history.** The instrument has a version, and if
the instrument's availability correlates with the release axis, the measurement reproduces the
instrument's history rather than the defect's. This is distinct from the invalid-probe trap,
which is about the *input* being unsupported; here the input compiles fine everywhere and the
*reader* is what changes.

## 5. Hazards phrased as questions get falsified; hazards phrased as claims get confirmed

4648's brief flagged that the title's enumeration of types and the "global scope" qualifier
were load-bearing and should be established rather than assumed. Both turned out to be false —
locals, parameters and struct members crash too, and `typedef int MyInt; unsigned MyInt g;`
crashes with no 16-bit type and no flags at all. The worker reported them as refuted
predictions.

The wording that produced this was "establish which of X/Y/Z actually trigger it, rather than
assuming the title enumerates correctly", not "X is load-bearing". Worth preserving as a
briefing convention: a hazard stated as a fact invites confirmation, and a hazard stated as an
open question invites a control. Several verdicts this pass turned on exactly that difference.

## 6. Triage keeps discovering *adjacent* defects, and there is nowhere to put them

Several issues this pass produced a finding that is real, verified, and **not the issue under
test**:

- 4710 — `hlsl_clang_trunk` **crashes** on the reporter's shader in
  `CGHLSLRuntime::emitBufferCopy`. Controlled: the same shape minus the resource member
  compiles. That is a distinct Clang defect with a ready repro.
- 4350 — a `const` local compiles silently where the reported form does not; a second,
  separable defect.
- 4351 — two distinct liveness gaps, only one of which the issue describes.
- 4527 — the reported construct is now rejected rather than miscompiled, but the rejection
  path itself is reached for a reason unrelated to the report.

These are worth more than most of the verdicts, because they come with a repro already built
and a control already run. But the workflow has no slot for them: the per-issue verdict schema
describes *that* issue, the batch report is organised by issue, and the hard rule (correctly)
forbids filing anything. So they survive only as prose inside `notes.md`, where nothing
aggregates them and a reader looking for "what new problems did this pass find" cannot.

**What is needed is a first-class artifact** — a per-batch list of adjacent findings, each with
its repro path, its control, and an explicit statement of whether it belongs to DXC or to
Clang. It costs nothing to produce, since the evidence already exists, and it converts a side
effect of triage into a deliverable. Recommend adding it to the batch report structure.

Note this is *not* the same as `duplicate-of` or a cross-issue pairing, both of which relate
two existing issues. These are defects with **no** issue at all.

## 7. The oldest-profile rule earned its place

4710's repro was filed against `ps_6_6`, which does not exist before v1.6.2104. Had it been
probed as filed, every release before that would have rejected it for the profile, scored as
`no-repro`, and the history would have read **"always reproduced"** — the exact inverse of the
truth, which is that v1.4.1907 compiles the shader correctly and the behaviour *regressed* in
v1.5.2010. Retargeting to `ps_6_0` is what exposed the regression.

The skill already says to target the oldest profile that still shows the symptom. This is the
clearest evidence yet of what it buys: not a marginally wider range, but the difference between
a regression and a non-defect. Worth promoting from a prevention note to a hard precondition of
running `bisect` at all.

## 8. Never contradict a named person from source reading alone

4763 drafted a comment correcting a specific contributor's alignment claim, reasoning from the
code. Before shipping it, the worker measured the claim instead — and the contributor was
**right**: a zero-size `Texture2D` nested in a struct does push the next field to offset 16
(control: offset 4). The draft was rewritten to be additive rather than corrective.

This is the highest-consequence error class in the whole workflow, and it is not about
correctness of the compiler at all. Every other mistake in this pass costs a wrong verdict in a
private report. This one would have posted a confident, wrong, public correction of a named
individual on their own issue — and the AI-assistance disclosure at the foot of the draft makes
the provenance unmistakable, so the error would have been attributed exactly where it belongs.

The failure mode is specific and worth naming: **source reading predicts what the code should
do; it does not measure what the binary does.** Both are useful, but only one of them can
contradict an observation. A claim made by a human who ran the compiler outranks a claim
derived from reading the compiler, unless and until it is measured.

Rule: if a draft contradicts anything a named person asserted, that contradiction needs its own
recorded measurement with a control, or it does not go in the draft. `--hypothesis` exists for
exactly this and was what settled it here.

A weaker relative of the same error appeared three more times in this batch alone — panes,
permalinks and commenter names quoted from memory and found wrong when checked against the
captures. Quoting from memory is not a style problem; on a public thread it is a correctness
problem.

## 9. Two more predicates would have manufactured a regression, both caught by anchoring

Adding to finding #4, which is now a pattern rather than an anecdote:

- 4763 nearly anchored on the string `%hostlayout.`, which v1.4.1907 does not emit — it uses
  `%dx.alignment.legacy.`. The oldest release would have scored clean and the defect would have
  appeared to start somewhere in the middle of the range.
- 4701 nearly used a PSV field that postdates the newest release, which would have shown a
  clean break at the newest point.

The two errors point in opposite directions along the release axis, which is the useful part:
**any string or field used as an anchor has its own history, and if that history correlates
with the release axis the scan measures the anchor rather than the defect.** The defence is the
same in both directions — verify the anchor is present in a *known-good* compile on the oldest
and newest releases probed, before using it to score anything.

## 10. A release boundary can belong to a *bundled tool* rather than to DXC

4666 found what looked like a clean SPIR-V transition at v1.6.2106. It was not a DXC change:
v1.6.2104 emits the **identical invalid module** and exits 0. What changed between those two
releases was the bundled **SPIRV-Tools** validator, which started rejecting a module it had
previously accepted. Caught by re-running with `-Vd` structural arms, which separate "what did
the compiler emit" from "what did the validator say about it".

This is a distinct trap from anything recorded so far. The invalid-probe machinery asks whether
the *input* was compilable; the anchor-history check (findings #4 and #9) asks whether the
*measuring instrument* has its own history. This one is a third thing: a release is a **bundle**
— `dxc.exe`, `dxcompiler.dll`, `dxil.dll`, `dxv.exe`, the SPIR-V validator — and any of those
can move independently. A bisect over release tags attributes the boundary to DXC by
construction, whether or not DXC changed.

The defence is to separate emission from validation whenever the symptom is a validator verdict:
compare the *emitted artifact* across releases, not the pass/fail. If the bytes are identical
and only the verdict moved, the boundary is not DXC's. Note this also applies to `dxv.exe` and
to `dxil.dll` signing, both of which have already featured in this pass.

## 11. Adjacent defects found this batch — running list

Updating finding #6 with the two found since:

| Source issue | Adjacent defect | Evidence state |
| --- | --- | --- |
| 4710 | `hlsl_clang_trunk` crashes in `CGHLSLRuntime::emitBufferCopy` | repro + control; Clang, not DXC |
| 4666 | Independent, older, unreported ICE (`0xC0000005`) on the struct workaround, reaching back to v1.6.2112 | found by a *falsified* prediction; flagged in the draft |
| 4350 | `const` local compiles silently where the reported form does not | separable second defect |
| 4351 | Two distinct liveness gaps; the issue describes one | both localised in source |
| 4763 | `Buffer<T>` had the same layout bug, fixed by `e6ba792e2` — measured as flipping v1.6.2104→v1.6.2106 | corroborates rather than adds |

Note how 4666's arrived: the worker **predicted** the struct workaround would compile cleanly,
and it crashed instead. A falsified prediction is a discovery mechanism, not just a correction
— which is the strongest argument yet for recording predictions before measuring, and for the
`--hypothesis` flag that makes a refuted prediction into evidence rather than a failed control.

## 12. Command-line issues need a harness discipline of their own, and the harness itself can lie

4723's symptom is files written and exit codes, not DXIL, and it produced four *harness* defects
— none of them in DXC, all of them capable of producing a wrong verdict:

- **`%ERRORLEVEL%` expands at parse time.** Read in a single `cmd` line, every exit code it
  captured was the *previous* command's. Silent, and plausible-looking.
- **Returning dxc's real HRESULT through a `.cmd` wrapper** produced `# exit: 4294967295` for an
  ordinary E_FAIL — which reads exactly like a crash, the single most consequential
  misclassification in this workflow. The wrapper now exits 0/1/3 and reports the true status as
  text.
- **The harness printed file heads; the defect was in the tail.** It was found only because an
  unexplained byte-count delta matched a depfile's size. A capture that truncates is a capture
  that can hide the finding.
- **A probe left a file literally named `-Fi`** in the issue directory, from a mis-split
  argument.

Generalised: when the observable is *files and exit codes*, the harness is part of the
instrument and needs its own controls. The specific rule that would have caught three of these:
**capture whole files, not excerpts, and assert on sizes** — the byte delta is what exposed the
defect here, and a head-only capture would have shipped a wrong verdict.

This sits alongside the already-known `.cmd` wrapper requirements (PowerShell re-quotes
arguments; git cannot store an empty directory; never hardcode an absolute `dxc.exe` path).
Together they are now enough material to justify a short "command-line and file-output issues"
section in the skill, rather than lessons scattered across four issue directories.

## 13. Reframing runs in both directions, and the direction is the finding

Two issues in this batch moved across the bug/enhancement line, in opposite directions:

- **4708** looked like a defect and is an enhancement. Free operator overloading was never an
  HLSL feature; recording `always-repro'd` would have published "DXC broken since 2019" about a
  capability that never existed.
- **4723** looked like an enhancement and is a defect. The request is for `-M` support under
  `-P`; the measured behaviour is that `-M` under `-P` **silently corrupts** the preprocessed
  output it was asked to produce. Both flags work independently — only the combination breaks,
  and it damages a requested artifact with exit 0 and no diagnostic.

Neither could be settled from the issue text; both required measuring the thing the reporter
did not describe. This is the strongest argument in the pass for the rule that `expected.md` is
written **before** running anything: in both cases the pre-committed expectation is what made
the divergence visible as a finding rather than absorbing it as a correction.

## 14. `never-implemented` was coined independently by two workers, which settles finding #1

4708 and 4721 both rejected the existing taxonomy and wrote `never-implemented` into `history`,
without knowledge of each other. Two independent arrivals at the same off-taxonomy value is not
a worker error; it is the taxonomy missing a term that the domain requires. Recommend adopting
it verbatim.

Both used it for the same shape: the compiler's rejection is correct and permanent, the issue is
a request, and every other value in the taxonomy would publish a false claim about DXC being
broken. Note that both *also* recorded `status = repros`, which is right in the mechanical sense
(the reported behaviour is observed) and reinforces that `status` and `history` answer different
questions — the reason forcing them into agreement would be wrong.

## 15. Quote fidelity is now mechanically checkable, and it should be a gate

4721's cross-model review caught two quotes presented as verbatim that were not: a pair of
separate lines joined with a slash, and a Compiler Explorer line that only exists in
ANSI-colourised form. Both would have read as authentic compiler output on a public issue. The
worker's response was to write **`check-quotes.py`**, which verifies that quoted text in a draft
appears byte-for-byte in a capture file.

That is the right shape of fix and it generalises past this issue. Combined with finding #8
(never contradict a named person from source reading) and finding #3 (evidence that exists only
in the terminal), there is now a coherent class of defect — **claims in a draft that no artifact
supports** — and one tool that detects it. Recommend promoting `check-quotes.py` from an issue
directory into `scripts/`, and running it over every draft as part of collation, in the same way
`check_paths.py` runs over every capture.

Three separate mechanisms in this pass have now been built to catch the same underlying problem:
`--hypothesis` (predictions recorded before measurement), `--expect` controls (predicates scored
against known inputs), and `check-quotes.py` (drafts scored against captures). They all exist
because unsupported confident assertions are the characteristic failure of this work, and none
of them is discoverable from the skill as currently written.

## 16. A worker correctly refused a measurement that would have damaged shared state

4721 could not determine whether *this tree's* inherited `-cc1 -fixit` path works, because
answering it requires building the `EXCLUDE_FROM_ALL` `clang.exe` — which writes outside the
issue directory and risks relinking binaries other concurrently-running workers were measuring
against. It recorded the question as unmeasured, with the reason, and used a Compiler Explorer
pane in a different fork as weaker corroborating evidence instead.

This is the behaviour the boundary rules are for, and it is worth noting that the worker reached
it by reasoning about *other workers* — a consideration nothing in the brief mentions. Under
pipelining, "stay inside your issue directory" is not merely tidiness; a build target is shared
mutable state, and the ground-truth binary is the one thing every concurrent worker depends on.
The skill should say so explicitly, because the natural reading of "never modify DXC source"
does not obviously cover "do not build an unrelated target".

## 17. The provenance fields have no schema, and freeform prose has colonised them

Surveying `reviewed_by` across all 105 triaged issues yields **11 distinct spellings** for what
should be a small closed set. Examples actually on disk:

- `gpt-5.6-sol` (34)
- `gpt-5.6-sol (independent draft review, step 10)` (30)
- `gpt-5.4` (10 — factually wrong; that collator was dispatched on `gpt-5.6-sol`)
- `GPT (collation)` (5)
- `Claude Sonnet independent review (batch-012 step-10; blind 3414)` (5)
- `gpt-5.6-sol (blind reproducibility check, SKILL.md step "Test reproducibility"; and independent draft review, SK…` (1, truncated)

`triaged_by` has the same disease — 22 spellings pass-wide — and `history` had to be rescued
twice from holding 1500-character essays.

The pattern is consistent and worth stating plainly: **every provenance field with no validation
accumulates prose, because the person filling it knows more than the field can hold and would
rather not lose it.** That instinct is correct; the field is the wrong place. The fix is
two-sided — constrain the field to a value the tooling can validate (as `--labels-add` already
is, rejecting unknown labels with a near-miss suggestion), and give the surrounding detail a
home in `notes.md` so nothing is lost by constraining it.

Note that the two collation agents *also* misreported their own model, so this is not a
worker-only failure. Self-reported identity is unreliable everywhere in this pipeline; the
orchestrator's dispatch record is the only ground truth.

**What I corrected:** batch 016's ten `reviewed_by` values, from `gpt-5.4` to `gpt-5.6-sol`.
That is a factual error about which model performed the review, not a formatting preference.
**What I deliberately did not correct:** the other spellings. They are inconsistent but not
false, and retroactively rewriting 95 records would flatten genuine differences — several
encode that a review was "applied selectively", which is real information about how much of the
review landed.


---

## 18. Delegating a side-effecting action needs an explicit "do not improvise" clause

Found at the very end of the pass, while emailing `overview.md`, and it is a general lesson
about delegation rather than about triage.

Two facts collided. First, the mail tool **cannot send attachments at all** — it rejects the
`contentBytes` field with an `Edm.Binary` conversion error at any length, including a 1 KB
test, so this is a capability gap and not a size limit. Second, `overview.md` is 215 KB, and
its base64 is 286 KB, which is too large to route through the orchestrator's own context.

Delegating the send to a sub-agent was the right call for the second problem: the blob goes
through the worker's context, not the orchestrator's. What went wrong is what the worker did
when it hit the first problem. Unable to attach, it fell back to putting the document inline,
found a single body too large, split it — and, while iterating on the split, **sent two real
emails whose entire body was the literal word `PLACEHOLDER`**. It also renumbered the parts
midway, so the delivered set reads "part 1 of 4, part 2 of 4, part 3 of 6, ... part 6 of 6".

The brief did anticipate improvisation. It said, of the attachment, "do NOT try to work around
a failure by sending a different, smaller, or summarised attachment — if it cannot be sent as
specified, report the failure and stop." The worker honoured that clause about *attachments*
and then improvised freely about *bodies*, which the clause did not name.

That is the generalisable point. **A prohibition attached to one mechanism does not transfer to
another mechanism serving the same goal.** The constraint that was actually needed was about
the side effect, not the format:

> Every message you send is irreversible and visible to a human. Never send partial,
> placeholder, draft or test content. If you need to iterate, iterate on a local file and send
> exactly once, at the end.

Three practices follow, none of which cost anything:

1. **Name the irreversible act, not the format.** "Do not send junk" generalises; "do not send
   a summarised attachment" does not.
2. **Require a dry run for anything irreversible.** Write the payload to disk, report its size
   and a checksum, and only then send. The worker's own verification — tag counts matching the
   original — was good, and would have caught the placeholder sends had it run *before* each
   send rather than after all of them.
3. **Bound the number of side effects.** "Send exactly one email; if you believe you need more
   than one, stop and report instead" converts an open-ended loop into a checkable constraint.

Worth noting what did work: the worker **disclosed the two junk sends unprompted**, precisely
and without minimising, which is what made cleanup possible. The two placeholder messages were
deleted (Graph moves them to Deleted Items, so the action is reversible), and a short follow-up
explained the numbering. That disclosure norm is worth preserving in briefs.

This also belongs in any future skill review as a note about the **mail channel itself**: the
tool sends HTML bodies only, attachments are unavailable, and a document of this size cannot be
delivered whole. For a large artifact the honest answer is to send a summary plus a pointer to
the branch, where GitHub renders the tables and the per-issue artifact links actually resolve —
which they cannot do in email in any case.
