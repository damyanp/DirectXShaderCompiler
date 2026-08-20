# Issue #5059 -- HLSL loop optimization results in an unsupported i33 type

## Summary

The root defect is real, present in every dxc build tested (v1.4.1907
through current main-debug), and has never been fixed: LLVM's SCEV pass
rewrites the loop

```hlsl
uint processed = 0;
uint result    = 1;
while (processed != input) { result += processed; processed++; }
```

into a closed-form multiply of the overflow-guarded shape
`((input-1)*(input-2))/2` (this loop always converges to `result =
input*(input-1)/2 + 1`), and to guard against 32-bit overflow of the
intermediate product it widens the operands by one bit to `i33`, which
DXIL does not support (only i1/i8/i16/i32/i64 are legal integer widths).

What has changed, very recently and precisely, is not the defect but how
loudly it fails. Through `v1.9.2602.24` (built 2026-05-27) the illegal
`i33` reached the disassembly and dxc exited 0 -- a silent correctness
bug. Starting at `v1.9.2607` (built 2026-07-29), and still true on
main-debug, the DXIL validator's `Types.IntWidth` rule now rejects the
module with `error: Int type 'i33' has an invalid width.` and dxc exits
`0x80004005` -- an ordinary diagnosed validation failure. This is a
`changed-behavior` verdict, not `does-not-repro`: the shader still cannot
be correctly compiled today, it simply fails loudly (well before its
undefined-behavior original) instead of silently.

## Ground truth

Registered `main-debug` at `<repo>/build/Debug/bin/dxc.exe`,
`git_commit` recorded as `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
`dxc --version` self-reports `1.9.0.5465 (triage, 7665270b9)` --
a different SHA, expected for a local/rewritten-history working branch
per SKILL.md. Verified this is genuinely the registered commit's DXC
source (not a stale/mismatched build) with a controlled tree-diff:
`git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
touches only files under `.github/skills/dxc-issue-triage/*` (5315 files,
all triage data, zero DXC source), while a control diff against an
unrelated old release (`upstream/release-1.8.2407`) shows thousands of
real source changes outside that path -- proving the check can detect a
genuine mismatch and did not find one here.

## Timeline read

Filed 2023-02-24 by sooknarine against `-T lib_6_3 i33.hlsl -Fc
i33.dxil.txt` (no `-E`, `CSMain` has no `[shader("compute")]` attribute).
pow2clk posted a godbolt link 2023-11-02. damyanp commented on 2024-09-25
that it "no longer repros," then **two minutes later** posted a corrected
comment ("previous link was bad; this one shows a repro") -- confirmed via
the full GitHub timeline (`closed` at 17:19:43Z, `reopened` at 17:21:11Z,
matching the two comments exactly). This is not a real fix-then-regress
event; it is a single maintainer catching their own bad godbolt link
within minutes, and the thread's *current, final* position is "reproduces."
No cross-referenced issues/PRs exist in the timeline (not a duplicate).

The bad link (`x5aP3b41T`) used `-T lib_6_3` with no `-E`; the corrected
link (`x8er4WYeE`) used `-T cs_6_3 -ECSMain`. This distinction turned out
to matter independently of the godbolt mixup (see below).

## The as-filed command is a dead end on current main

The reporter's literal command, `-T lib_6_3 i33.hlsl -Fc i33.dxil.txt`, no
longer reaches the bug on main-debug at all: `CSMain` carries
`[numthreads]`/`[RootSignature]` but no `[shader("compute")]` attribute,
so in library-target mode it is not recognized as an entry point. dxc
exits 0 with only "attribute ignored without accompanying shader
attribute" warnings, and the emitted `-Fc` disassembly
(`i33.dxil.txt` in this directory) contains an *empty* library (`!4 =
!{null, !"", null, null, null}` -- no entry points at all). Verified this
same command *did* reach the bug at `v1.4.1907` (2019-07), so somewhere in
the intervening ~7 years library-mode entry-point recognition tightened;
that transition is a distinct, secondary, unexplored finding, not dated
here. The actually-working repro, matching the maintainer's corrected
link, is `-T cs_6_3 -ECSMain repro.hlsl` (`cmd.txt`); this was run as a
labelled hypothesis variant (`--hypothesis --expect no-match`) and
confirmed "supported" (`variant-as-filed-main-debug.txt`).

## Predicate design (two predicates, bisected separately)

Per SKILL.md's guidance for a symptom that differs from current
behaviour, this issue uses **two** predicates rather than one combined
`any_of`, specifically so the release where the shape changed is visible
instead of being absorbed into a single "always-repro'd" line:

- `match.json` -- the *reported* (silent) shape: `\bto i33\b` in the
  disassembly text. On a successful compile, plain `dxc` (no `-Fc`
  needed) writes full text disassembly to stdout -- verified across
  every tested era, not assumed -- so this predicate is satisfied purely
  by the primary `cmd.txt` command's stdout.
- `match-caught.json` -- the *current* (caught) shape: the validator's
  exact message, `Int type 'i33' has an invalid width`. Exit code on
  match is `0x80004005` (E_FAIL); per SKILL.md's exit-code table this is
  an ordinary diagnosed validation failure, not `internal_failure`.

Two negative controls discriminate the predicate from "any bounded loop
fails":
- `control-trivial.hlsl` -- a single load/store, no loop at all.
- `control-nonclosedform.hlsl` -- the same while-loop trip-count shape as
  the repro, but accumulating memory loads instead of a closed-form
  arithmetic series (so SCEV has nothing overflow-guarded to widen).

Both controls score `no-repro` under **both** predicates
(`variant-control-trivial-main-debug{,--match-caught}.txt`,
`variant-control-nonclosedform-main-debug{,--match-caught}.txt`),
confirming the predicates fire on the reported loop shape specifically,
not on any loop or any compile.

## Ground-truth run and full linear history

`triage.py run --issue 5059` (uses `match.json`): main-debug scores
**no-repro** (`out-main-debug.txt`, exit `0x80004005`, the caught shape).
`triage.py run --issue 5059 --match match-caught.json`: main-debug scores
**repro** (`out-main-debug--match-caught.txt`).

`triage.py bisect --issue 5059 --linear` (full linear scan, not just
endpoint agreement, given the thread's own close/reopen back-and-forth
was itself worth double-checking) against `match.json`:

```
v1.4.1907 .. v1.9.2602.24   repro       (19 releases, silent shape)
v1.9.2607                   no-repro    (validator now blocks it)
```

The same linear scan against `match-caught.json` is the exact mirror
image:

```
v1.4.1907 .. v1.9.2602.24   no-repro
v1.9.2607                   repro
```

(5 prereleases excluded from history by policy: v1.5.2003, v1.8.2306-preview,
v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24; v1.2.0-alpha
skipped, no usable asset.) main-debug matches `v1.9.2607`'s shape exactly.
Combined: the *underlying defect* is `always-repro'd` (some shape of it
fires on every one of the 20 catalogued stable releases and on
main-debug, with zero invalid probes -- a full, clean, non-oscillating
release history in both directions), while the *reported wording
specifically* transitioned once, cleanly, at `v1.9.2607`.

Confirmed with `-Vd` (skip validation) that main-debug's compile pipeline
still internally generates the same `i33` sequence even with the
validator disabled (`manual-case-vd-skip-validation.txt`): `%7 = zext i32
%6 to i33`, `%10 = mul i33 %7, %9`, `%11 = lshr i33 %10, 1`, `%12 = trunc
i33 %11 to i32` -- the root SCEV widening is unchanged; only the
validator's strictness changed.

## Attribution of the validator-behavior change (strong, not certain)

Release build dates bracket the transition precisely:
`v1.9.2602.24` (published 2026-06-03, built 2026-05-27) still shows the
silent shape; `v1.9.2607` (published 2026-07-29, built 2026-07-29) is the
first catalogued release to show the caught shape. That two-release
window (no intervening catalogued release exists) is the release-level
fact this triage stands behind.

Source archaeology finds a very plausible, but not conclusively
build-dated, source: PR #8207 ("[Validation] Make validator reject
unsupported llvm integer sizes", commit `90ae8d807`, merged 2026-03-10,
fixing #6563) added exactly this class of check -- it extended
`ValidateType`'s existing width check (which previously only walked
aggregate/struct member types) to also run on the raw operand types of
ordinary instructions via `ValidateFunctionBody`, which is precisely the
code path a bare `mul i33 %7, %9` goes through. However, `90ae8d807`'s
merge date (2026-03-10) precedes `v1.9.2602.24`'s build date (2026-05-27)
by over two months, and that release still shows the silent shape -- so
either release-branch cuts lag `main` (the likely explanation, not a
second independent behavioral change) or something scopes the check away
from this exact case until later. `git log --all -S "has an invalid
width"` on `utils/hct/hctdb.py` also surfaces the registered ground-truth
commit itself, `89e2f98e2` (PR #8762, "[HLSL] Add LinAlg descriptor I/O
offset, stride and layout coverage"), which re-adds the whole
`add_valrule_msg` table including `Types.IntWidth` -- consistent with a
large validation-rule-table refactor rather than a second behavioral
change. Given the ambiguity, this triage states the measured release
bracket as the authoritative, direct evidence and cites both PRs as
plausible source-level contributors without claiming either is proven to
be the exact release-affecting commit (no commit was built and tested
directly to settle this, per SKILL.md's confidence guidance).

## Compiler Explorer

Published `cmd.txt`'s exact args (`-T cs_6_3 -ECSMain`) against
`dxc_1_6_2112` (old, silent shape, exit 0) and `dxc_trunk` (current,
caught shape, exit 5, `error: Int type 'i33' has an invalid width.`):
https://godbolt.org/z/PGGE6r8s9 -- `godbolt-note.txt` explains what to
look for in each pane; both panes' full text captured locally in
`manual-case-godbolt-verify.txt`. Shortlink read back and verified to
render the annotated source and match the local capture.

## Labels

Current: `bug, dxil, correctness, validation`. Ran `triage.py labels
--refresh` (58 labels) then `triage.py labels --issue 5059`: no additions
or removals proposed against the live taxonomy. All four current labels
remain accurate (a real bug, DXIL-level, a correctness defect, and now
also literally a validation-diagnosed one); no change recorded.

## `reviewed_by`

Left unset, as instructed -- independent review is a batch-level step
(step 10) performed separately, not by this same session.
