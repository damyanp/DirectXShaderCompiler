# Method notes — #4096

Observations for collation. Nothing here changes `SKILL.md` or `triage.py`; a per-issue
session does not write shared state.

## 1. `-HV` pinning turned a would-be false history into a clean one, in both directions

The repro needs HLSL 2021 (member `operator` declarations). Without `-HV 2021`, the four
pre-2021 releases fail with an ordinary parse error on `operator bool()`, which is *not* one
of `classify`'s feature-absence markers — so they would have scored `no-repro` and
`bisect --linear` would have reported a transition at v1.6.2112 that is an artefact of the
default language version, not a change in behaviour. With `-HV 2021` they answer
`dxc failed : Unknown HLSL version: 2021`, which the classifier does recognise, and they are
correctly demoted.

`SKILL.md` already says "Pin the language version of any repro older than the current
default", citing #2202 where the *newer* default broke an *older* repro. This is the mirror
case — the repro is newer than the old releases' default — and pinning fixes it for a
different reason: it converts an unrecognised parse error into a recognised driver-level
rejection. Worth noting that the existing rule earns its keep in both directions.

## 2. A "diagnostic is the symptom" issue where the marker rule did *not* misfire

#3055's trap (`SKILL.md` step 6) is that on a diagnostic-quality issue the invalid-probe
markers and the symptom are the same observation. It did not fire here, and the reason is
worth writing down because it is a cheap thing to check in advance: the symptom text
(`is not contextually convertible to 'bool'`) shares no substring with any marker, and the
predicate carries no absence clause, so `_is_absence_predicate` is false. When designing a
predicate for a diagnostic-quality issue, checking those two properties up front took under a
minute and removed the whole class of concern.

## 3. `godbolt --source` cannot be used for a *second* link without losing the first

`--source` is remembered in `godbolt-source.txt` and rewrites the stored link, so an issue
that wants (a) a published link showing the reporter's exact shader and (b) a measurement on a
transformed shader has to choose. Here the reporter's shader is the right thing to publish —
but on its own it could not answer the question, because Clang compiles it to an empty
`main()` and an empty `main()` cannot say whether the operator ran.

Two workers in batch 008 wrote their own CE client for a different reason (the first-line
summary), and `triage.py` absorbed that. This is a third reason to want one, and it suggests
the general shape: **a labelled CE probe**, analogous to `run --shader X --label Y`, writing
`variant-godbolt-<label>.txt` without touching the published link. `probe-clang.py` in this
issue directory is a 90-line stand-in that reuses `triage.ce_compile` by importing `triage.py`
directly, which works fine and might be worth making a supported entry point.

## 4. "Does it still reproduce" really was the uninteresting half

The reported symptom is present on every probeable release and on `main`; that took two runs
and told nobody anything they did not already know in 2021. The three findings that matter all
came from following the *resolution*:

- the construct is now a hard error at the declaration, from a change merged four months
  before this triage;
- the operator body has never executed in any shipped compiler that accepted the declaration,
  which the reporter's own shader cannot show because both candidate conversions agree on it;
- the successor front end already implements the requested behaviour.

The last one needed a discriminating shader on the Clang pane. A plain Clang pane on the
reporter's repro exits 0, and "Clang compiles it" would have been a true statement that
suggested the wrong conclusion — Clang also compiles it while *ignoring* the operator, for the
C-style-cast spelling. The general lesson, which I think generalises past this issue: when a
Clang pane **succeeds**, that is not yet evidence either. `SKILL.md` documents the control
discipline for a Clang *error* ("A Clang error is not evidence until you have a control",
#1702). The success direction has the same hazard and is easier to miss, because a green pane
reads as a result. An acceptance claim needs a shader whose *output* distinguishes the two
possible reasons for acceptance.

## 5. Cross-issue material, deliberately kept out of the draft

Recorded here for collation to check rather than asserted in `comment.md`:

- PR #8206's stated purpose is `Fixes #5103`, a separate issue asking DXC to diagnose cast
  operators instead of silently ignoring them. #5103 was closed COMPLETED 2026-04-14.
- #6081 ("Conversion operators do not work") was closed 2024-10-29 as a duplicate of #5103.
  Its thread carries llvm-beanz's 2023-11-30 statement that these will be resolved by adopting
  C++ overload-resolution rules in a future HLSL language version, and names
  `microsoft/hlsl-specs` proposals 0007 and 0008.
- `microsoft/hlsl-specs` PR #37 (cross-referenced into #4096 on 2023-04-06) carries
  llvm-beanz's assessment that new operator overloads will be HLSL 202x features and will
  depend on the 202x overload-resolution rework (hlsl-specs PR #34), quoted verbatim in
  `notes.md` from `discussion_r1158553249`, 2023-04-05. That is the clearest statement of the
  design position and it is not in this issue's own thread — it was only reachable through the
  cross-reference timeline, which is another datapoint for `SKILL.md`'s "read the
  cross-reference timeline during step 1, not only at collation". Caveat recorded in
  `notes.md`: no comment body in PR #37 currently contains the string "4096", so the
  cross-reference *event* is the link I can evidence, and the quoted comment is about
  operators on built-in types rather than this conversion specifically.
- `microsoft/hlsl-specs` #281 (prefix/postfix increment operator overloading, milestone
  HLSL 202y) is adjacent but is a different operator category.

Whether any of these are duplicates of #4096 is a judgement for collation. My own reading is
that they are not — #4096 is about the *implicit* conversion in a `bool` context, #5103/#6081
about explicit casts — but that reading is exactly the kind of claim a single-issue session
cannot check.

## 6. `check_paths.py` and per-issue helper scripts

`check_paths.py` flags absolute machine paths anywhere under `data/`, including inside
generated `manual-case-*.txt` transcripts. A per-issue helper that prints the compiler path it
invoked will trip it. `measure-history.py` and `probe-clang.py` here avoid it by resolving the
repo root from the script's own location and rendering paths through a `display()` helper that
rewrites the prefix to `<repo>/`, so the transcript is still copy-checkable without embedding
anyone's drive layout. Worth doing by default in any ad-hoc measurement script, since the
transcript is the artefact a human reads.

## 7. Redirecting the path gate's own output into an issue directory re-imports every leak

Near-miss worth writing down, because it is easy and silent. The gate reports the whole tree,
so its output contains other workers' absolute paths verbatim, in the JSON-escaped form the
gate itself rejects. Saving that report into an issue directory to grep it therefore *creates*
a failing file in a directory that was clean, attributed to the wrong worker, on a path nobody
authored. I did this, spotted it, and deleted the file before re-running.

The safe shapes are to pipe the gate's output straight to a filter without ever landing it on
disk, or to write scratch outside the skill tree. If a worker ever does need to keep the
report, it should not live under a per-issue directory. This may be worth one line in the
step-11 hygiene instructions, since the natural way to answer "are any of these hits mine?" is
exactly the unsafe one.

Related: verifying a *clean* result needs the same control discipline as any other negative.
"No hits in my directory" is only meaningful once the query has been shown to find something,
so I ran the matcher against a fixture containing all four spellings (raw and JSON-escaped, for
both the project and home-directory prefixes) and confirmed 4/4 before trusting the zero.
`check_paths.py` does this internally in `validate_matcher()`, which is a good pattern; an
ad-hoc grep does not, and that is where a false clean comes from.

## 8. Not committed

Artifacts are written but not committed; a batch commit message naming issue numbers is a
documented hazard, and committing is a batch-level step. Everything needed to re-derive the
verdict is on disk in `data/issues/4096/`.
