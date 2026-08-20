# Issue #5587 — Bitfield initialization unclear — notes

## Ground truth

`main-debug`, cited commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(2026-08-12, "[HLSL] Add LinAlg descriptor I/O offset, stride and layout
coverage (#8762)"), registered in `.cache/compilers/main-debug.json`.
`dxc --version` reports `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) -
1.9.0.5465 (triage, 7665270b9)` — the binary self-reports the fork-local
merge commit `7665270b9` ("Merge remote-tracking branch 'origin/main' into
triage"), which is not the public commit to cite. Verified by tree, not by
self-reported SHA:

```
git diff --name-only 7665270b9 89e2f98e2      # 0 files outside .github/skills/dxc-issue-triage
git diff --name-only 89e2f98e2~50 89e2f98e2   # CONTROL: 9+ files outside it (azure-pipelines.yml, docs/, include/dxc/..., ...)
```

The build's compiler source tree is identical to public
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` outside this skill's own data
directory, and the control (an older commit) shows real differences in
compiler source, confirming the diff is discriminating rather than merely
empty by construction. `git merge-base --is-ancestor 89e2f98e2... HEAD`
also exits 0. `89e2f98e2` is the correct commit to cite publicly.

## Repro

`repro.hlsl` / `cmd.txt` reproduce the issue's `test.hlsl` and command line
(`dxc -T cs_6_6 -HV 2021 -E main test.hlsl`) verbatim — repro quality
`complete`. `control-reordered.hlsl` is the same struct with the two
bitfield members swapped (`uint32_t rest : 30;` before
`SomeEnum field1 : 2;`), which is what the reporter says compiles cleanly.

## Predicate

`match.json` is a `regex` on the exact diagnostic quoted in the issue body:
`cannot convert from 'literal int' to 'SomeBitfield'`. This is a
diagnostic-quality issue whose reported symptom *is* the diagnostic text
(see the skill's step-6 guidance on this shape), so quoting it verbatim is
correct rather than a generic "cannot convert" pattern that would also
match unrelated conversion errors.

## Result on ground truth

`out-main-debug.txt`: exit 0, **no-repro**. The struct-to-`SomeBitfield`
cast from `0` compiles cleanly with the original (unreordered) field
order. The emitted DXIL's `rawBufferStore` call is
`i32 0, i32 undef, i32 undef, i32 undef, i8 1, i32 4` for
`(index, value0, value1, value2, value3, mask, alignment)` — i.e. it
stores a concrete `0` into the struct's single 32-bit storage word (mask
`1` selects only that lane), which is the correct DXIL for
`(SomeBitfield)0` on a 32-bit-wide bitfield struct. This is not a compile
that merely avoided the error while emitting garbage.

`variant-reordered-main-debug.txt` (`control-reordered.hlsl`, `--expect
no-match`): also exit 0, no-repro, confirming the expectation. The
reordered struct behaves the same as the original order now — the
asymmetry the issue is about (works reordered, fails in the reported
order) is gone on both sides, not merely shifted.

## History

`bisect --issue 5587`:

```
v1.4.1907      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.5.2010      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2104      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2106      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2112      repro
v1.9.2607      no-repro
v1.8.2403.2    repro
v1.8.2505      no-repro
v1.8.2407      repro
v1.8.2502      repro

result: fixed-in v1.8.2505 (last repro: v1.8.2502; 4 release(s) skipped as unprobeable;
5 probeable prerelease(s) excluded from the search by policy)
```

`out-v1.6.2106.txt` confirms the four skipped releases are a genuine
`invalid-probe`, not a hidden fix: v1.4.1907 through v1.6.2106 all answer
`dxc failed : Unknown HLSL version: 2021` (exit 1) — `-HV 2021` itself was
not supported until v1.6.2112, so those four releases never reached the
code under test. `out-v1.6.2112.txt` is the oldest release that can run
this repro at all, and it reproduces the reported error exactly:
`error: cannot convert from 'literal int' to 'SomeBitfield'`
(exit `2147500037` = `0x80004005`/E_FAIL, an ordinary diagnosed error, not
an internal failure). `out-v1.8.2502.txt` (2025-02-20) still reproduces
verbatim. `out-v1.8.2505.txt` is clean (exit 0), with the same
zero-storing `rawBufferStore` shape seen on `main-debug`. Binary search
therefore correctly brackets the fix between v1.8.2502 and v1.8.2505.

The bisection floor for this repro is v1.6.2112 (the first stable release
with `-HV 2021` support), not the usual v1.4.1907 floor — HLSL 2021 itself
postdates the older releases, and bitfields are an HLSL-2021-and-later
feature, so no earlier release could ever have shown this symptom. The
issue was filed 2023-08-23 against `dxcompiler_xs.dll: 1.7 -
2310.2307.12501.10025` (a ~2023-07 build); binary search did not sample a
release from exactly that date, but v1.6.2112 (2021-12-08, well before
filing) and v1.8.2403.2/v1.8.2407/v1.8.2502 (2024-2025, well after filing)
all reproduce, so the failure is confirmed on both sides of the reporter's
filing date under the monotonicity assumption `bisect`'s binary search
relies on.

## Fix attribution

The fix window (`v1.8.2502..v1.8.2505`) holds 162 commits. I searched for
an exact fix commit (diffs of `tools/clang/lib/Sema/SemaHLSL.cpp` and
`tools/clang/lib/AST/HlslTypes.cpp` — the files implementing HLSL's
struct/vector cast flattening — across the window, and commit-message
greps for bitfield/init/flatten/convert keywords) and did not find one
that plausibly explains this specific fix; nothing in the window's commit
titles or the diffs of the flattening-related files mentions bitfields or
struct-cast initialization. I am **not** naming a specific commit as the
fix. The attribution is release-level only: fixed somewhere within those
162 commits, dated between 2025-02-20 (v1.8.2502) and 2025-05-24
(v1.8.2505). This
does not weaken the does-not-repro verdict itself, which rests on directly
running the repro against `main-debug` and the bracketing releases, not on
source attribution.

## Compiler Explorer

`godbolt --issue 5587` (default compilers `dxc_1_6_2112`, `dxc_trunk`):
`dxc_1_6_2112` reproduces the exact quoted diagnostic (exit 5); `dxc_trunk`
compiles cleanly (exit 0), and its `rawBufferStore` first value operand is
a concrete `0` (see `manual-case-godbolt-verify.txt` line ~85), corroborating
the local `main-debug` finding on Compiler Explorer's Release/Linux build.
Link: https://godbolt.org/z/xG8Kj4v58 (short-link read-back verified: no
warning was printed for a pane/argument/source mismatch).

CE's oldest DXC (1.6.2112) is also the repro's own bisection floor here, so
this pane happens to show the very earliest release this repro could ever
target — not merely "CE cannot date older than 1.6.2112" as usual, but
"CE's floor coincides with the repro's own floor" for this particular
issue.

## Design-question aspect (not adjudicated here)

The comment thread (llvm-beanz, mstrgram, damyanp) treats the underlying
cause as HLSL's struct-cast/initializer-list "flattening" behaving like a
vector initializer rather than C/C++ aggregate-initialization rules, and
points at a longer-term redesign proposal
(`hlsl-specs` PR "0005-strict-initializer-lists", and the related
`hlsl-specs#310`). No comment claims the specific order-dependent
compile failure reported here was ever fixed; the thread reads as an open
design discussion, not a tracked bug-fix promise. This triage only
measures the reported compiler behavior (the cast now compiles, and
compiles identically regardless of field order) and does not weigh in on
whether HLSL should adopt C++ initialization rules more broadly — that is
a language-design decision for the `hlsl-specs` discussion, not something
a compiler probe settles.

## Labels

Current: `bug`, `hlsl2021`. Both remain accurate — this was a real bug
report about an HLSL2021 feature, now fixed. No label change proposed.

## Independent draft review (step 10)

`comment.md` was reviewed by a separate model (`gpt-5.3-codex`, via a
sub-agent briefed with `comment.md`, `notes.md`, `expected.md` and
`issue.json`) for concision, unsupported speculation, stale quantifiers,
and point-scoring tone. It flagged 7 wording tightenings (no factual
errors, no numeral/count discrepancies) and confirmed the draft does not
overstate the fix's commit-level attribution and makes no fix/timeline
promise. All 7 suggestions were accepted and applied to `comment.md`.
Per this task's instructions, `verdict.json`'s `reviewed_by` field is left
**pending** rather than recorded, despite the review having been
performed and its outcome being documented here.

## Text staleness

Not stale in a way that would mislead a reader: the issue body accurately
describes what `dxc` did in 2023, and none of the four comments (the most
recent from 2024-10-10, a "related" cross-link) claim the underlying
compile failure was subsequently fixed. A reader relying on the issue text
would correctly believe the described failure occurred as reported; they
would just not know (nothing in the thread says) that it no longer does.
Not flagging `--text-stale`.
