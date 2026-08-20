# #5302 -- Incorrect code for waterfall loop in VS shader

## Ground truth

`main-debug` registered at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (public upstream
`main`). Version string: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
7665270b9)`. The binary self-reports a local merge commit (`7665270b9`, `Merge remote-tracking
branch 'origin/main' into triage`) because it was built on the triage branch; that commit is
not the citable one. Verified by tree, not by the self-reported SHA:

```
git rev-parse "7665270b9^{tree}"                                          -> 7bc9ae2f0...
git rev-parse "89e2f98e29c289ae8ad9e00dd310104fea9fd7df^{tree}"           -> c6e28aae6... (different tree, as expected -- the local commit also carries the skill's own data)
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
    -> 0 files outside .github/skills/dxc-issue-triage/
git diff --name-only 7665270b9 HEAD~200   (CONTROL, must show outside-skill files)
    -> 604 files outside .github/skills/dxc-issue-triage/
git merge-base --is-ancestor 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD -> exit 0 (ancestor)
```

No compiler source differs between the local build and the cited public commit; the control
proves the diff comparison can detect a difference when one exists. Cite
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` publicly.

## Issue

Reporter's `break.hlsl` (kept verbatim as `repro.hlsl`) implements a manual waterfall loop:

```hlsl
for (;;) {
    int u = WaveReadLaneFirst(a);
    if (a == u) {
        res += mainBuf[u][b];
        break;
    }
}
```

Compiled `-T ps_6_0`, the buffer load stays inside the loop, protected by the `dx.break`
mechanism (added in PR #2795, "Conditionalize breaks to keep them in loops", to stop the
optimizer treating a break as unconditional and hoisting wave-sensitive work out of the loop
as if it were loop-invariant). Compiled `-T vs_6_0` with the *same source*, the buffer load
(and the `LoadInput` it depends on) is hoisted out of the loop into a single straight-line
pass, with no `dx.break` protection at all -- exactly the pattern PR #2795 exists to prevent.

A later comment from the reporter (2023-06-19) traces this to
`tools/clang/lib/CodeGen/CGHLSLMS.cpp`, `CGMSHLSLRuntime::EmitHLSLCondBreak`, which only
engages the `dx.break` conditional-branch mechanism for Pixel, Compute and Lib shader models:

```cpp
if (!m_pHLModule->GetShaderModel()->IsPS() && !m_pHLModule->GetShaderModel()->IsCS() &&
    !m_pHLModule->GetShaderModel()->IsLib()) {
  return CGF.Builder.CreateBr(DestBB);   // plain unconditional branch, no dx.break
}
```

## Source confirmation

This guard is unchanged from its introduction: `d3af7f123` ("Conditionalize breaks to keep
them in loops (#2795)", 2020-03-30) added exactly this three-way `IsPS()/IsCS()/IsLib()` check
with no other stage included, and the check at the cited ground-truth commit is character-for-
character the same three-way test (confirmed by reading
`tools/clang/lib/CodeGen/CGHLSLMS.cpp:5009-5011` at `89e2f98e2` directly, and by
`git log --all -S"If not a wave-enabled stage"` finding only the introducing commit and one
unrelated file-reorganization commit that moved the same text without changing it). Vertex
(and, by the same guard, Geometry/Hull/Domain/Mesh/Amplification/RayTracing-Lib-adjacent
non-Lib stages) never engages the protection PR #2795 added for PS/CS.

## Local reproduction (ground truth)

```
dxc -T vs_6_0 -E main -DOUTPUT=Z repro.hlsl
```

produces (see `out-main-debug.txt`), **identical to the reporter's quoted IR**:

```llvm
define void @main() {
  %1 = call i32 @dx.op.loadInput.i32(i32 4, i32 0, i32 0, i8 0, i32 undef)
  br label %2
; <label>:2
  %3 = call i32 @dx.op.waveReadLaneFirst.i32(i32 118, i32 %1)
  %4 = icmp eq i32 %1, %3
  br i1 %4, label %5, label %2
; <label>:5
  %6 = call i32 @dx.op.loadInput.i32(i32 4, i32 1, i32 0, i8 0, i32 undef)
  %7 = add i32 %3, 2
  %8 = call %dx.types.Handle @dx.op.createHandle(...)
  %9 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(...)
  ...
  call void @dx.op.storeOutput.i32(...)
  ret void
}
```

No `dx.break` anywhere. The contrasting `-T ps_6_0 -E main -DOUTPUT=SV_Target` compile of the
identical source (`variant-control-ps-main-debug.txt`) reproduces the reporter's PS IR exactly,
including `@dx.break.cond = internal constant [1 x i32] zeroinitializer` and the phi-based
accumulator loop.

`match.json` scores "symptom present" as `storeOutput` (anti-vacuity: rules out a failed
compile scoring free) AND no `dx.break` anywhere in the output. Primary probe (`vs_6_0`) scores
`repro`; the `control-ps` variant (`--expect no-match`, run via `--args` since the control
changes both the profile and the output semantic and so cannot reuse `cmd.txt` through
`--shader`) scores `no-repro` as declared -- proving the predicate can detect the *presence* of
the protection in the same run, on the same source, not just its absence.

## History

`triage.py bisect --issue 5302 --linear` reported `always-repro'd across v1.4.1907..v1.9.2607`
with no invalid probes flagged -- **but this headline is misleading and had to be corrected.**
`v1.4.1907` (2019-07-15) predates PR #2795 (2020-03-30) entirely, so at that release **neither**
`vs_6_0` **nor** `ps_6_0` emits any `dx.break` machinery (confirmed directly: both compile
clean with no `dx.break` in either output). The predicate's `not_contains dx.break` clause is
therefore satisfied at v1.4.1907 for a reason that has nothing to do with the reported VS-vs-PS
divergence: the whole mechanism does not exist yet for any stage. Scoring that as a
reproduction manufactures history the same way an absence predicate manufactures a "clean"
release out of a build that never reached the code under test -- v1.4.1907 is invalid evidence
for *this* issue and must be excluded, even though `bisect`'s generic `invalid-probe`
classifier (built for rejected profiles/intrinsics) does not catch it, because the compile
itself succeeds here.

A per-release matrix (`gen-release-history.py` -> `manual-case-release-history.txt`) drives
each release's own `dxc.exe` with both the VS repro command and the PS contrast command and
records `dx.break` presence for both, on all 19 stable releases from v1.4.1907 through
v1.9.2607 plus `main-debug` (21 rows total):

| release | VS has dx.break | PS has dx.break |
| --- | --- | --- |
| v1.4.1907 (2019-07-15) | no | no -- **feature absent for both stages; invalid probe** |
| v1.5.2010 (2020-10-22) | no | **yes** |
| v1.6.2104 .. v1.9.2607 (17 further stable releases) | no | yes, every release |
| main-debug (89e2f98e2) | no | yes |

Every probeable release from v1.5.2010 (the first stable release built after PR #2795 landed)
through v1.9.2607, and `main-debug`, shows the identical divergence: PS is protected, VS is
not. **The bug has reproduced, unfixed, for the entire life of the `dx.break` mechanism** --
since March 2020 -- not merely "always" in the sense of "as far back as checkable"; the
mechanism simply never covered VS. `v1.5.2003` is a GitHub prerelease and stays out of the
search by policy (no `release-policy.json` opt-in; the issue does not name it).

## Compiler Explorer

Four-pane comparison, `-T vs_6_0` and `-T ps_6_0` on both CE's oldest DXC (`1.6.2112`, itself
already past the v1.5.2010 boundary) and `dxc_trunk`:
https://godbolt.org/z/jj8fzqMTK

Both `vs_6_0` panes lack any `dx.break` reference; both `ps_6_0` panes contain
`@dx.break.cond` and the guarded branch (verified in `manual-case-godbolt-verify.txt`, lines
441-668 and 670-897 respectively; short link read back and matched the four submitted panes).
`dxc_trunk` corroborates that the divergence is present on a current build too, though as a
rolling build it is not itself citable for history. `godbolt-note.txt` deliberately avoids
spelling `dx.break` (it is compiled into the source via CE's `-Zi -Qembed_debug`, which would
manufacture a false hit in the VS panes) and instead describes the structural cue: presence or
absence of a module-level internal constant before `define void @main()` and of a phi-based
loop accumulator.

## Labels

Current: `bug`. Proposed additions: `correctness` (this is exactly what the label describes --
a shader-correctness defect, not merely a diagnostic gap) and `incorrect-code` (DXC silently
emits materially different, and per the reporter and PR #2795's own stated purpose, wrong code
depending only on shader stage; this label was used for the same class of defect on #1702).
No label removal proposed.

## Verdict

- status: `repros`
- repro-quality: `complete`
- history: `always-repro'd` across every probeable release from v1.5.2010 (the first stable
  release to ship `dx.break` at all) through v1.9.2607, and on `main-debug`; v1.4.1907 is
  invalid evidence (predates the `dx.break` mechanism entirely for every stage, not just VS)
  and is excluded from the population.
- confidence: `high` -- source-confirmed (the guard is unchanged since its introduction),
  locally reproduced byte-for-byte against the reporter's own quoted IR for both stages, and
  confirmed unfixed on `main-debug`.
- suggested action: `still-valid-keep-open`. The bug is real, understood down to the exact
  guard clause, and has never been fixed for VS (or, by the same code, GS/HS/DS/Mesh/
  Amplification and non-`lib_*` raytracing stages) since dx.break was introduced in 2020. No
  text is stale: the title and body still accurately describe current behaviour.
