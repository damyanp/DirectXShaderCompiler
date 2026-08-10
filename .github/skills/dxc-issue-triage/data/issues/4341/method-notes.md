# Method notes — #4341

Observations about the method, for collation to promote or discard. Nothing here changes
`SKILL.md` or `triage.py`; this session wrote only inside `data/issues/4341/`.

## 1. The `-HV 2021` hazard resolved the *opposite* way here, and the same measurement settled it

The brief warned that an inherited `-HV 2021` has manufactured a false feature floor before,
and that proving the flag inert on a neighbouring issue recovered four releases. On #4341 the
identical measurement — repro with the flag and without, on every release — showed the flag
is **load-bearing**: on v1.6.2112 … v1.7.2212.1, dropping it yields `'operator' is a reserved
keyword in HLSL`, so removing it would have *destroyed* four valid probes rather than
recovering any. The default moved to 2021 somewhere in v1.7.2212.1 … v1.7.2308, after which
the flag is inert.

The transferable point is that the *measurement* generalises and the *conclusion* does not.
"`-HV 2021` was inherited from the title, therefore suspect it" is right; "therefore drop it"
is not. `SKILL.md` already says "Verify the option is load-bearing, or compare with and
without it" — this is a case where the verification came back positive, and it may be worth
saying so explicitly, because the existing worked examples (#3835, #3362) both end in the
flag being dropped or re-spelled and read as though that is the expected outcome.

A cheap generalisation: when the flag under suspicion selects a **language mode**, the
with/without comparison should be run per release rather than only on ground truth. On `main`
alone the flag is inert (default is already 2021), which is exactly the observation that would
have justified deleting it — and would have been wrong for two thirds of the probeable range.

## 2. "Not selected" vs "rejected" needs two predicates, not one predicate and a narrative

The brief asked to distinguish "the overload is not selected" from "the overload is
rejected". Designing the repro so the two produce different *values* (seed `1.0`, write
`9.0`, return the slot) is necessary but not sufficient: a single predicate scoring `no-repro`
still cannot say which of "fixed" and "silently discarded" happened, because both compile
cleanly.

What made it falsifiable was a **mirror predicate** — `match-write-lands.json`, matching the
DXIL a landed write produces — bisected separately. Primary `always-repro'd` plus mirror
`never-repro'd` over the same 16 releases jointly rule out the silent-discard state at every
release, and both statements are re-scorable by `reindex` forever. Neither alone does.

`SKILL.md` documents `any_of` for "one defect with several signatures" and a second
`match-*.json` for "the reported symptom differs from current behaviour". This is a third
use — **a predicate whose job is to make the complement of the primary observable** — and it
is cheap, because the mirror's controls are the primary's controls with the expectations
swapped. Possibly worth a line under "An issue may need more than one predicate".

## 3. A feature-presence control run on *every* release turned an ambiguous demotion into a fact

`bisect` demoted four releases on `Unknown HLSL version: 2021`, which `SKILL.md` says is
ambiguous on its own. Running `variant-getter-read.hlsl` (the smallest shader using the
feature at all) on all 20 releases in the same matrix showed repro and control failing
together on exactly those four and the control clean on the other 16. That is one script and
about 40 extra compiles, and it converts "the tool trimmed four releases" into "these four
releases cannot express the construct, and the other sixteen demonstrably can". Folding the
control into the same generated matrix as the `-HV` comparison made it nearly free.

## 4. A CE source reshaped for a control pane needs the transformation verified in *both*
directions, and `--source` makes that easy to skip

CE gives every pane one source, so the Clang control had to be a preprocessor guard
(`-DCONTROL_NO_ASSIGN`) rather than a second file. `SKILL.md`'s #8527 rule ("run the
transformation on a case that is known-good and confirm it still passes") applied directly,
and `triage.py run --shader` / `--args` covered both arms without hand-running anything:
subject reproduces, control compiles clean, both captured. Worth noting that the *control*
arm needs `--args` rather than `--shader`, because `-D` is a flag change rather than a source
change — and `--args` must then repeat the filename.

## 5. Housekeeping observed, not touched

- `git status` shows `scripts/check_paths.py`, `scripts/test_predicates.py` and
  `scripts/triage.py` as modified. This session did not edit them. Flagging it because
  `SKILL.md` says `git status` on `scripts/` after the parallel phase should be empty, and a
  mid-batch predicate change would retroactively affect verdicts other workers have already
  written.
- An untracked `repro.hlsl` sits at the **repository root** (a structured-buffer/child-array
  shader, created 2026-08-10 12:13, not from this issue). Left alone as another worker's
  in-flight file, but a stray repro at the repo root is the kind of thing that gets committed
  by accident.

## 6. Cross-issue observation (draft deliberately silent)

llvm-beanz's comment says "We have a bunch of related issues that will need to be addressed"
and points at hlsl-specs proposal 0007. If other issues in this or an adjacent batch land on
HLSL operator overloading, const instance methods, or reference support, they are plausibly
the same language gap — but this session measured only #4341 and cannot check that. Collation
should decide; `comment.md` makes no cross-issue claim.
