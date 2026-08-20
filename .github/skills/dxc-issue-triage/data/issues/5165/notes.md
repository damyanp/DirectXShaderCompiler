# Notes -- #5165

"Validation error on switches having 8 cases: 'I8 can only used as immediate value for
intrinsic'"

Filed 2023-04-20 by @mbenoitea. Body quotes:

```
error: validation errors
D:\local\Temp\cdb50d40-be4c-454a-83de-dc5763aaf698.hlsl:8:2: error: I8 can only be used as
immediate value for intrinsic or as i8* via bitcast by lifetime intrinsics.
note: at '%4 = trunc i32 %3 to i8' in block '#0' of function 'ShaderDomain_Cs'.
Validation failed.
```

The only external repro is a Shader Playground link
(`https://shader-playground.timjones.io/6953c16efbd7c9eac2aa77def27b78e4`), which is dead:
`shader-playground.timjones.io` does not resolve (DNS failure, tried both `curl` and
`web_fetch`). No file attachment carries the source.

damyanp (MEMBER) commented 2024-09-24: *"This doesn't look like a validation issue - the
optimizer is generating invalid code."* This reframes the issue: the validator is working
exactly as designed (catching illegal IR); the defect is upstream, in codegen/optimization.
No cross-reference events exist on this issue as of this triage (`gh api
.../issues/5165/timeline`), confirming no duplicate or successor issue is linked, and confirms
this triage session created none either.

## Repro

`repro.hlsl` is agent-constructed (the reporter's exact shader is unrecoverable) but
independently reconstructs the exact reported failure mode from source-code analysis, not from
guessing at the missing shader:

```hlsl
RWStructuredBuffer<uint> buf : register(u0);

[numthreads(1,1,1)]
void ShaderDomain_Cs(uint3 id : SV_DispatchThreadID)
{
    uint x = buf[0];
    bool result;
    switch (x)
    {
    case 0: result = true; break;
    case 1: result = true; break;
    case 2: result = true; break;
    case 3: result = true; break;
    case 4: result = true; break;
    case 5: result = true; break;
    case 7: result = true; break;
    default: result = (buf[1] != 0);
    }
    buf[0] = result ? 1 : 0;
}
```

Command: `-T cs_6_0 -E ShaderDomain_Cs repro.hlsl` (`cmd.txt`).

## Root cause (source-level, corroborated by the repro)

`lib/DxilValidation/DxilValidation.cpp`'s `TypesI8` rule (~line 3733-3757) rejects any
i8-typed value used for anything other than an immediate to an intrinsic or a bitcast to `i8*`
for a lifetime marker. That rule is not itself the bug (per damyanp's comment, and confirmed
here) -- it is correctly rejecting IR that should never have been generated.

The IR comes from LLVM's `SwitchToLookupTable` optimization in
`lib/Transforms/Utils/SimplifyCFG.cpp`. That function builds two independently-sized bitmaps:

1. **`BitMapKind`** (the *result* bitmap, used when the switch's results all fit in a small
   integer register). Its width was **fixed** for illegal-width cases (i9/i17/i26/i33/i40/i48)
   by commit `3bb9beee2` / PR #8444 ("[SimplifyCFG] Fix illegal-width bitmap from switch lookup
   table"), which rounds that bitmap's width up to >= 16 bits. `git merge-base --is-ancestor
   3bb9beee2 HEAD` succeeds against the registered ground truth (89e2f98e2...), so this fix is
   present. It closed a **different, unrelated, and much more recently filed** issue, #8421
   (DXC 1.10.2605.2, an `i26` failure) -- confirmed via `gh api .../issues/8421`; #8421 is not
   connected to #5165 and is not affected by this triage.
2. **The "hole check" mask** (used when the lookup table has holes -- `TableHasHoles = true`
   -- AND the default case's result is not a compile-time constant -- `HasDefaultResults =
   false` -- so `NeedMask = true`). Its width is computed independently, at
   `SimplifyCFG.cpp` ~line 4240-4265:

   ```cpp
   uint64_t TableSizePowOf2 = NextPowerOf2(std::max(7ULL, TableSize - 1ULL));
   ...
   Value *MaskIndex = Builder.CreateZExtOrTrunc(TableIndex, MapTy, "switch.maskindex");
   ```

   When `TableSize` (max case value - min case value + 1) is <= 8, this yields exactly **8**,
   producing an illegal `i8` truncation that the `TypesI8` rule then rejects. This code path
   was **not** touched by #8444/PR #8444 and carries no `// HLSL Change` marking it as
   HLSL-modified -- it is the unpatched sibling of the bug class #8444 fixed for the result
   bitmap, still present verbatim in the registered ground truth.

Why a naive repro (e.g. a contiguous 0-7 switch, or a 20-case switch) does not trigger this:
DXC's `SimplifyCFG` runs with a `TargetTransformInfoWrapperPass` backed by no real target
machine, so `TargetTransformInfoImplBase::isTypeLegal()` always returns `false`.
`ShouldBuildLookupTable()`'s `HasIllegalType` therefore saturates `true` for essentially any
result type, and the transform only proceeds when the earlier `AllTablesFitInRegister`
short-circuit is true -- i.e. only for small-width results (matching why upstream's own
regression test, `dxil_switch_bitmap_legal_types.ll`, uses `i1`/bool results). The repro
therefore needs: a `bool` switch result, a case-value **gap** (so `TableHasHoles`), a spread
<= 8 (to hit exactly i8), and a **non-constant default** (so `HasDefaultResults` is false and
`NeedMask` is forced true). Case set `{0,1,2,3,4,5,7}` (gap at 6, spread 0-7 -> TableSize 8)
satisfies all four.

## Predicate and controls

`match.json`: `I8 can only\s+(?:be\s+)?used as immediate value for intrinsic` (regex). See
`method-notes.md` for why the predicate was loosened after an initial version produced a false
`regressed-in v1.5.2010` result by missing v1.4.1907's older wording.

- `control-no-holes.hlsl`: same 7-case bool switch, contiguous case values 0-6 (no gap), same
  non-constant default. `--expect no-match`: scored `no-repro` (exit 0) on main-debug both
  before and after the predicate fix. Isolates "holes" as a necessary condition.
- `control-const-default.hlsl`: same holes (0-5,7; gap at 6), but a **constant** `false`
  default. `--expect no-match`: scored `no-repro` (exit 0) on main-debug both before and after
  the predicate fix. Isolates "non-constant default" as a necessary condition.

Both controls pass under the corrected predicate exactly as they did under the original,
confirming the wording fix did not broaden the predicate into matching unrelated i8
diagnostics -- it only widened acceptable phrasing of the *same* diagnostic.

## History

`triage.py bisect --issue 5165 --linear` (linear scan, all 20 stable releases probed
individually, `v1.2.0-alpha` skipped as having no usable asset, and 5 prereleases excluded by
policy): **`always-repro'd` across v1.4.1907..v1.9.2607** (the full stable-release floor to
the newest cataloged release), and confirmed further on `main-debug` (commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). No release ever produced a clean compile of this
repro. v1.4.1907's own capture differs only in wording (see Method notes /
`out-v1.4.1907.txt`), not in substance -- it shows the identical rule firing on the identical
shader, from block `switch.hole_check` (the pre-refactor block name for what is labelled
`block '#2'` in later releases' `note:` lines).

Because #8444's fix (present in ground truth) addressed a sibling code path, its presence does
not affect this issue's history at all: the `NeedMask` hole-check path was never touched, so
this defect predates and postdates that fix identically.

## Compiler Explorer

`triage.py godbolt --issue 5165` (default panes: `dxc_1_6_2112`, `dxc_trunk`):
`https://godbolt.org/z/qPfqjxxnY`. Both panes reproduce the exact validator text and
`trunc`-note shape (see `manual-case-godbolt-verify.txt`); shortlink read-back
(`GET /api/shortlinkinfo/qPfqjxxnY`) confirms both compilers, arguments and source match what
was intended to publish. `godbolt-note.txt` states what to look for. This corroborates the
local bisection result (v1.6.2112 reproduces) on CE's independent Linux Release build.

## Labels

Current: `bug`. Proposed addition: `correctness` ("Bugs that impact shader correctness") --
this is a miscompile of otherwise-valid HLSL by the optimizer, not a validator defect and not
a case of the compiler mishandling genuinely-incorrect input (`incorrect-code` does not apply).
No maintainer statement or issue text argues for a different label; `validation` was
considered and rejected per damyanp's own comment that this is not a validation-layer bug.

## Verdict

- Status: `repros` (confirmed on ground truth, matching the issue's reported diagnostic and
  the maintainer's "optimizer generating invalid code" framing).
- Repro quality: `agent-constructed` (reporter's shader is unrecoverable; reconstructed from
  source-level root-cause analysis and independently confirmed to reproduce the exact wording
  and instruction shape reported).
- History: `always-repro'd` (v1.4.1907 through main-debug at the registered ground-truth
  commit; linear-scanned, not merely endpoint-checked).
- Confidence: high -- root cause is identified at the exact source line
  (`SimplifyCFG.cpp`'s `NeedMask` hole-check mask-width computation), the repro reproduces the
  issue's own quoted diagnostic and instruction shape verbatim, two independent negative
  controls isolate both necessary preconditions, and CE independently corroborates on a
  separate Linux Release build.
- Suggested action: `still-valid-keep-open`. This is a live, always-reproducing optimizer bug
  with a known, narrow fix shape (the `NeedMask` mask-width computation should use the same
  >= 16-bit rounding that #8444 already applied to the sibling `BitMapKind` path), not
  something this triage should assert has been dispositioned.
- `--text-stale`: not applicable. The issue title/body still accurately describe current
  behavior (only the *validator's own wording* changed between v1.4.1907 and v1.5.2010 -- not
  the issue's description of it), and damyanp's 2024-09-24 comment remains accurate.
- `reviewed_by`: intentionally left pending. Step 10's cross-model draft review is a
  batch-level task performed at collation for batch-019, not per-issue.
