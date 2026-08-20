# Notes: #5744 -- ddx_fine/ddy_fine should not be allowed to sink into flow control

## Issue summary

Filed 2023-09-18. Reports that `ddx_fine`/`ddy_fine` (marked `ReadNone` in DXIL/
LLVM IR the same as any other side-effect-free unary op) can have their calls
moved ("sunk") by the optimizer into a conditional `if` block when the *result*
is only used there, even though the call was written unconditionally. Because
derivative intrinsics read neighboring-thread (quad) values, once the call
only executes for lanes that take the branch, the read observes
partially-uninitialized quad state. The issue's own repro is the runtime GPU
test `ExecutionTest::HelperLaneTest` / `hcttest exec-filter *HelperLaneTest`
(`ShaderOpArith.xml`'s `HelperLaneTestNoWave` data, with the `-opt-disable
sink` workaround removed), which needs a GPU adapter to observe. Two comments
(2024-01-07/08) confirm `-opt-disable sink` as a workaround; no fix landed on
this issue directly.

## Cross-reference timeline (read during step 1)

`gh api repos/microsoft/DirectXShaderCompiler/issues/5744/timeline` lists:
- 2023-09-18/21: PRs #5745 and #5769 (same day / days after filing) --
  "Fix HelperLaneTest" / "... (release branch version)" -- both add
  `-opt-disable sink` to the test's compile args as a *workaround*, and both
  explicitly say "Separate issue has been filed to track down the root of the
  problem: #5744". They do not fix the compiler.
- 2023-09-26: #5667, the issue these PRs actually closed --
  `ExecutionTest::HelperLaneTest failing on AMD, Nvidia and Qualcomm GPUs`,
  itself closed by #5745/#5769's workaround, not a compiler fix.
- 2024-10-22: four `llvm/llvm-project` issues (#99096-99098, #101558). These
  are Clang/LLVM HLSL-frontend implementation checklists for `ddx`/`ddx_coarse`/
  `ddx_fine` builtins and unrelated resource-lowering work; GitHub's
  cross-reference matched on the intrinsic names in their checklists, not on
  any discussion of this defect. Not relevant to root cause.

None of the timeline events represent a fix landing against #5744 itself.

## The actual fix: PR #8707, for duplicate issue #8001

`microsoft/DirectXShaderCompiler#8001` ("[SM6.9] Derivative Calls Incorrectly
Sunk Into Conditional Branches", filed later, describing the identical defect
in near-identical words: "DXC's optimizer sinks `ddx`/`ddy` calls into
conditional branches when the result is only used inside that branch... This
breaks quad semantics...") was fixed by commit `28d9915fa0` / PR #8707 ("Mark
derivative operations as convergent", merged 2026-07-31T16:59:01Z, `Fixes
#8001`). The commit message states plainly: "Previously, the various
derivative operations were not marked as convergent, which allows their
results to be sunk into conditional branches. This change fixes that and
removes the workaround for this issue from the execution tests." That last
clause -- removing the `-opt-disable sink` workaround from the execution
tests -- is exactly the repro step #5744 itself specifies
("remove `-opt-disable sink` from the shader compile arguments... Run
`hcttest exec-filter *HelperLaneTest`"), which corroborates that #8707 is the
root-cause fix for #5744's own report, not merely for #8001's later
restatement of it. #8707 also added a release note
(`docs/ReleaseNotes.md`, "Bug Fixes" section) crediting only `#8001`; #5744 is
not named anywhere in the fixing commit, PR, or release note.

Source confirmation: `OP::IsDxilOpConvergent` (`lib/DXIL/DxilOperations.cpp`)
now returns true for `DerivCoarseX`/`DerivCoarseY`/`DerivFineX`/`DerivFineY`
(opcodes 83-86); `CreateTrivialDxilCall` (`lib/HLSL/HLOperationLower.cpp:427`)
adds `Attribute::Convergent` to the call site whenever
`OP::IsDxilOpConvergent(Opcode)` is true -- this is new code added by
`28d9915fa`, per `git log -S IsDxilOpConvergent`, which returns only this one
commit.

## Repro

Not a shader from the issue body verbatim -- the issue's own snippet is a
fragment of a much larger execution test file
(`tools/clang/unittests/HLSLExec/ShaderOpArith.xml`) that this workflow
cannot run against a GPU. Instead, used the *exact* HLSL source from
`microsoft/DirectXShaderCompiler#8001`'s own repro
(https://godbolt.org/z/PMK9EoTnK, a public Compiler Explorer link off a public
issue in this repo, so safe to reuse and re-publish): a `[numthreads(2,2,1)]`
compute shader that reads `WaveGetLaneIndex()`, computes `ddx(value)`
unconditionally, and only stores the result inside `if (LaneIndex == 3)`.
#8001 is the later duplicate of #5744 that happens to carry the fix and a
directly-runnable repro, so using its source measures the same defect #5744
reports without inventing a new construction. `repro.hlsl`/`cmd.txt` record
this as `-T cs_6_6 -E main repro.hlsl`.

This *is* compiler-verifiable without a GPU: the sink is a static code-motion
decision visible in the disassembled DXIL/LLVM IR. `match.json` is a regex
requiring the literal derivative-op call site (`= call ... i32 8[3-6],` for
opcodes 83-86, i.e. `DerivCoarseX`/`Y`/`DerivFineX`/`Y`) to appear textually
after a `br i1` -- i.e., that the call itself, not merely a reference to its
already-computed result, was placed inside the conditional successor block.

**Predicate false-positive found and fixed during triage:** an earlier
version of `match.json` matched the bare substring `DerivFineX` after
`br i1`. On the oldest release, v1.4.1907, dxc's disassembler keeps
source-derived SSA names (`%DerivFineX` as the *value's name*, not just a
comment), so a later, entirely legitimate *use* of that already-computed
value inside the conditional block (a correctly-conditional UAV store of the
result) recurs as the substring `DerivFineX` after `br i1` even though the
call was never sunk on that release -- this scored `repro` when the true
answer was "no sink happened, only its result was stored conditionally,
which is correct." Anchoring on the full call-site idiom
(`= call ... i32 8[3-6],`) rather than the op's name fixed this; see
`match.json`'s `note` and this issue's `method-notes.md`.

## Results

Ran `triage.py run --issue 5744` against `main-debug`
(89e2f98e29c289ae8ad9e00dd310104fea9fd7df, includes `28d9915fa`, confirmed
by `git merge-base --is-ancestor`) -- **no-repro**. `out-main-debug.txt` shows
`%5 = call float @dx.op.unary.f32(i32 83, float %4) ; DerivCoarseX(value)`
computed before `%6 = icmp ...` / `br i1 %6, ...`; the call stays in the
entry block, unconditional, exactly as expected once fixed.

Ran `triage.py bisect --issue 5744 --linear` (linear scan since the bisection
floor v1.4.1907 and v1.5.2010 are `invalid-probe`, not a real clean endpoint --
see below -- so a binary search's short-circuit-on-endpoint-agreement would
be comparing the wrong things):

```
v1.4.1907      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.5.2010      n/a (never compiled the repro -- profile, flag or feature unsupported)
v1.6.2104      repro
v1.6.2106      repro
v1.6.2112      repro
v1.7.2207      repro
v1.7.2212      repro
v1.7.2212.1    repro
v1.7.2308      repro
v1.8.2403      repro
v1.8.2403.1    repro
v1.8.2403.2    repro
v1.8.2405      repro
v1.8.2407      repro
v1.8.2502      repro
v1.8.2505      repro
v1.8.2505.1    repro
v1.9.2602      repro
v1.9.2602.24   repro
v1.9.2607      repro
```

`v1.4.1907`/`v1.5.2010` reject `-T cs_6_6` outright (`error: invalid profile
cs_6_6`, confirmed in each capture's header:
`# invalid-probe-reason: output matched the feature-absence marker "invalid
profile"...`) -- SM 6.6 postdates both releases, so they never reached the
code under test and are correctly excluded, not counted as "fixed". Every
release that *can* compile the repro, from v1.6.2104 (2021-04-20) through
v1.9.2607 (2026-07-29, the newest published stable release, built two days
*before* the fixing commit), reproduces. **No shipped stable release contains
the fix; it exists only on `main` as of `28d9915fa` (2026-07-31).**

Confirmed the sink directly in `out-v1.6.2104.txt`:
`%7 = call float @dx.op.unary.f32(i32 83, float %4) ; DerivCoarseX(value)` is
inside `; <label>:6 ; preds = %0`, the successor block of `br i1 %5, label
%6, label %10` -- the call itself was moved into the branch that only
`LaneIndex == 3` takes.

## Compiler Explorer corroboration

`triage.py godbolt --issue 5744 --compilers "dxc_1_6_2112,dxc_trunk"` --
https://godbolt.org/z/vrMMYWr31 (link read back and verified to match what
was sent). `dxc_1_6_2112` (CE's oldest, Release build, Dec 2021) shows the
same sink: `%DerivCoarseX = call float @dx.op.unary.f32(i32 83, float %2) ...`
appears inside the block that follows `br i1 %3, label %4, label %7`.
`dxc_trunk` (CE's rolling build) shows the call *before* the branch --
`dxc_trunk` already carries the fix, consistent with `main-debug`. Full pane
text in `manual-case-godbolt-verify.txt`; see `godbolt-note.txt` for what the
banner tells a reader to check.

CE's `-Zi -Qembed_debug` debug-info flags (appended to every DXC pane per
this skill's standing note) add a wrinkle worth recording: the pre-fix pane's
`llvm.dbg.value` for the source variable `derivative` is emitted *before*
`%DerivCoarseX`'s own defining `call` line in the text (a forward reference
through debug metadata, not a real operand-dominance violation), which is why
this write-up anchors on the real call site rather than on debug-info
ordering.

## Labels

`bug, correctness` (current) accurately describe a confirmed, always-reproducing
correctness defect across every runnable stable release; no addition or
removal proposed.

## Verdict

- Status: **does-not-repro** on `main-debug` (fixed by `28d9915fa`, upstream
  of ground truth).
- History: **fixed-in main** (not yet in any numbered release); always
  reproduced in every stable release that can compile the repro
  (v1.6.2104..v1.9.2607); v1.4.1907/v1.5.2010 are invalid probes (predate SM
  6.6), not evidence of an earlier fix.
- Repro quality: `agent-constructed` (reused verbatim from public issue
  #8001, not built from #5744's own execution-test fragment, which this
  workflow cannot run against a GPU).
- Confidence: high for "the sink no longer happens on `main`" (direct,
  repeated static evidence plus CE's independent `dxc_trunk`); high for "this
  is the same defect #5744 reports" (identical mechanism, and #8707's commit
  message describes removing the exact workaround #5744's own repro steps
  ask to remove) but not textually confirmed by a maintainer statement tying
  #5744 to #8707/#8001 -- #5744 was never referenced by the fix.
- Suggested action: `duplicate-of #8001`, closable as fixed once a maintainer
  confirms the linkage -- #8001 already carries the fix and its own closure;
  #5744 remains open only because nothing ever cross-linked it to #8001 or
  #8707.
- `text_stale`: not applicable in the narrow sense (the issue's description
  of the defect is still accurate as a description of the *mechanism*), but
  its implicit claim "no fix has landed" is now false. Not marking
  `--text-stale` because the issue body itself was never edited/updated with
  an inaccurate claim -- the whole issue simply predates its own fix by
  nearly three years, which is stated directly in the verdict summary and
  draft comment instead.
