# #5491 — DXC does not eliminate wave intrinsic calls even when the result is unused

**Verdict: `repros`** — confirmed on `main` and on every stable release back to the bisection
floor. Not a regression: nothing has ever behaved differently.

Ground truth: `build/Debug/bin/dxc.exe`. The binary self-reports
`1.9.0.5465 (triage, 7665270b9)` on a local branch called `triage`, which is not a public
commit. Per SKILL.md, cite the public upstream commit instead:
**`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`**, which is the tree the source corresponds to —
verified with the controlled diff in `manual-ground-truth-version.txt`: `git diff --name-only`
between that commit and the local build's HEAD shows **zero** files outside
`.github/skills/` (the triage workspace) differ, while the same check against a commit 50
revisions earlier shows real differences (`.github/copilot-instructions.md`,
`azure-pipelines.yml`, `docs/DXIL.rst`, …), proving the check is not vacuous. This is also the
exact SHA already registered as `main-debug` in the local triage cache
(`.cache/compilers/main-debug.json`).

Issue filed 2023-08-03 by @dmpots, 4 comments. `expected.md` was written before anything ran.

## Where each claim's evidence lives

| claim in this file | backing file |
| --- | --- |
| ground-truth compiler identity; tree-equivalence control | `manual-ground-truth-version.txt` |
| the source citations, quoted verbatim via `git show` | `manual-source-citations.txt` |
| primary repro on ground truth | `out-main-debug.txt` (`cmd.txt`, `match.json`) |
| control that the predicate does *not* fire when the result is used | `variant-control-used-main-debug.txt` (`control-used.hlsl`, `--expect no-match`) |
| release history | `out-v1.4.1907.txt` … `out-v1.9.2607.txt` (`bisect --linear`) |
| Compiler Explorer corroboration | `manual-case-godbolt-verify.txt` |

`reindex` was **not** run — it rewrites the shared `issues`/`runs` tables and this triage
touches only issue 5491's directory. `triage.py audit --issue 5491` was run instead (see
bottom of this file) as the read-only completeness check.

## What was tested

`cmd.txt` is the reporter's own command, translated from `/` to `-` flag spelling (no other
change): `-T ps_6_0 -E main repro.hlsl`. `repro.hlsl` is the reporter's 4-line shader verbatim.

```
[RootSignature("")]
void main(int a : A) {
  (void)WaveReadLaneFirst(a);
}
```

## Confirmed on ground truth

```
$ dxc -T ps_6_0 -E main repro.hlsl
[exit] 0
define void @main() {
  %1 = call i32 @dx.op.loadInput.i32(i32 4, i32 0, i32 0, i8 0, i32 undef)  ; LoadInput(inputSigId,rowIndex,colIndex,gsVertexAxis)
  %2 = call i32 @dx.op.waveReadLaneFirst.i32(i32 118, i32 %1)  ; WaveReadLaneFirst(value)
  ret void
}
[...]
; Function Attrs: nounwind
declare i32 @dx.op.waveReadLaneFirst.i32(i32, i32) #1
attributes #1 = { nounwind }
```

Identical in shape to the reporter's 2023 output (`e09a454eb`, v1.6.2104.52-era): the wave call
is present, its result (`%2`) is never referenced by anything before `ret void`, and — new in
this triage — the *declared* attributes on the callee show why: `nounwind` only, no `readnone`
or `readonly`.

## Why: this is not an oversight, it is the declared attribute working as designed

`match.json`'s predicate anchors on the structural fact that the call line is immediately
followed by `ret void` with nothing in between (register-name-independent, so it is not
disturbed by a different compiler's SSA numbering) — proven by `control-used.hlsl`
(`--expect no-match`), where the identical `WaveReadLaneFirst` call instead feeds a `sitofp`
and a `storeOutput` before `ret void`, and the predicate correctly scores `no-repro`.

`lib/DXIL/DxilOperations.cpp:1063-1070` declares every wave DXIL opcode's memory attribute as
`Attribute::None` (`manual-source-citations.txt`), in contrast to e.g. `loadInput` a few lines
away in the same table, which is `ReadNone`. `DxilOperations.cpp:6744-6760` shows that
attribute is what becomes the emitted LLVM function's `FnAttr` — `Attribute::None` means only
`NoUnwind` is ever added, never `readnone`/`readonly`. Standard LLVM dead-code elimination only
removes an unused call to an external function it can prove has no side effects
(`readnone`/`readonly` + no other observable effect); a plain `nounwind` declaration gives it no
such proof, so the call is conservatively kept regardless of whether the result is used. The
captured DXIL itself (`out-main-debug.txt`) shows exactly this: `declare i32
@dx.op.waveReadLaneFirst.i32(i32, i32) #1` / `attributes #1 = { nounwind }` — no `readnone`.

This reads as a **deliberate, if unhelpfully coarse, conservatism**, not a bug nobody looked at.
`WaveSensitivityAnalysis.cpp:27-34` documents the underlying reason wave-op results cannot be
treated like ordinary pure values: they depend on *which lanes are active* at that program
point, so moving, sinking or otherwise reasoning about them like a pure function can produce
wrong results elsewhere in the shader even when this particular call's own return value goes
unused. @llvm-beanz's comment on this issue — *"I'm not convinced there isn't a correctness bug
lurking here too"* — is exactly this concern, from a maintainer, at filing time.

The project does have a mechanism that removes wave ops when it can prove the surrounding
*control-flow region* is dead: `tools/clang/test/HLSLFileCheck/passes/EraseDeadRegion/
wave_intrinsic_dead_loop.hlsl` asserts that a wave op inside a provably-unreachable loop **is**
erased (`CHECK-NOT: br i1`, i.e. the whole loop is gone). That is a different code path
(`EraseDeadRegion`, guarding a structural control-flow proof) from what this issue asks for —
removing a single call whose *result value* merely goes unused in straight-line code. PR #5559,
linked from this issue, is itself a workaround against that different mechanism deleting a wave
op it should not have, on the grounds that a "read only" assumption elsewhere was wrong — filed
after #4174's loop-deletion fix, unmerged, and explicitly described by its author as possibly
incomplete. This repository's own history search (`git log --all`) does not resolve a clean
ancestry for the #4174 fix commit against the current tree, consistent with SKILL.md's warning
that history rewrites can orphan a SHA without changing the tree it produced — so no specific
commit or commit count is cited here. What is directly verifiable is that the test asserting the
loop-deletion behaviour (`wave_intrinsic_dead_loop.hlsl`) exists in the ground-truth tree, and
that PR #5559 is a real, unmerged, on-the-record instance of the surrounding area being
harder to get right than "just mark wave ops readnone" would suggest.

## History

`bisect --linear` (chosen over binary search per SKILL.md: nothing in this thread's history
claims monotonic behaviour, and `--linear` is the only way to make a population claim like
"none of N releases"):

```
skipped 1 release (no usable dxc asset): v1.2.0-alpha
skipped 5 prereleases from search by policy: v1.5.2003, v1.8.2306-preview,
  v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24
v1.4.1907 … v1.9.2607   repro  (20/20 probeable stable releases)
result: always-repro'd across v1.4.1907..v1.9.2607
```

Every probeable stable release from the bisection floor (2019-07) through the newest
catalogued release (2607) reproduces; none was an `invalid-probe` (`ps_6_0` and
`WaveReadLaneFirst` have existed since Shader Model 6.0, i.e. since before the bisection
floor). Combined with the ground-truth result, this is `always-repro'd` for as long as it is
possible to check — a longstanding, unfixed behaviour rather than a regression.

## Compiler Explorer

<https://godbolt.org/z/1T6e4zWsf> — `dxc_1_6_2112` (CE's oldest DXC build) and `dxc_trunk`, both
re-verified after publishing (`manual-case-godbolt-verify.txt`, shortlink `GET` returns HTTP
200). Both panes show the identical shape: `%WaveReadLaneFirst = call i32
@dx.op.waveReadLaneFirst.i32(...)` immediately followed by `ret void`. `dxc_1_6_2112` also
prints the harmless `DXIL.dll not found` signing warning on stderr, which is unrelated to the
symptom.

No Clang pane attempted: this is a codegen/optimization question about DXIL lowering, not a
front-end parsing or diagnostic question, so a Clang-vs-DXC comparison would not bear on it.

## Duplicates and related threads (read, not re-litigated)

- **#5177** (`WaveActiveMax(0)` under `#if DEADCODE`, same symptom) was closed by a maintainer
  on 2023-10-03 as a duplicate of this issue, confirmed via the cross-reference timeline
  (`gh api .../issues/5491/timeline`). Discussion continues here.
- **PR #5559** ("Workaround for wave loop getting deleted") is linked from this issue's first
  comment but is **closed, unmerged** (`mergedAt: null`). Its own description is the *opposite*
  direction of this report — preventing a wave op from being wrongly deleted from a loop, on
  the grounds that a "read only" assumption used elsewhere was wrong — and says explicitly "this
  might be the full fix, but requires more investigation." It does not resolve this issue and is
  evidence the surrounding design question is still open, not evidence of a fix.
- **#5302** and **#5034** are named in the same maintainer comment as "breadcrumbs" from a quick
  skim, not asserted duplicates; the reporter (@dmpots) rebuts #5302's relevance in a follow-up
  comment (different root cause: `dx.break` only applied to PS/CS/LIB targets), and the
  maintainer agrees. Neither is re-investigated here — that assessment is already on the public
  thread and is not this triage's finding to repeat or second-guess.

## Labels

Current: `bug`, `performance`, `dxil`. `labels --issue 5491` proposes no change. All three
already fit: this is a real defect (`bug`), specifically a missed optimisation rather than wrong
output (`performance`), and it is about DXIL-level codegen (`dxil`). Not proposing
`correctness`: the observed behaviour (keeping a demonstrably-unused call) does not itself
produce incorrect output; the correctness *risk* is on the other side, in how a fix might be
implemented, and is already covered by prose above rather than a label on this report.

## Limits of this triage

- Only the exact reported shape (a single wave-intrinsic call whose result is discarded in
  straight-line code, no loop) was measured. The broader question — under what conditions a
  wave op's result truly has no observable effect on other lanes, and whether that condition is
  decidable cheaply enough for a general DCE rule — was not, and is exactly the "correctness
  bug lurking here" the maintainer's original comment flags. This triage measures the symptom
  and its structural cause; it does not evaluate a fix.
- History is release-granular, not commit-granular: since every probeable release already
  reproduces, there is no fix-boundary to attribute to a commit.
