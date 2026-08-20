# Issue #5417 -- notes

## Summary

`GetAttributeAtVertex(x, i)` reads of a `nointerpolation` pixel-shader input are
not counted toward that input's `Used` mask in the disassembled input
signature, even though the value is genuinely read and forwarded to an output.
Confirmed still present on `main-debug` (89e2f98e2, self-reports as
`7665270b9`, see Provenance below) and on every stable release cached by this
skill, v1.4.1907 (2019-07) through v1.9.2607 (2026-07), plus CE's oldest
(`dxc_1_6_2112`) and `dxc_trunk`. No transition anywhere in that range --
`always-repro'd`.

## Repro

Issue body's shader, transcribed verbatim into `repro.hlsl` (repro quality:
`complete` -- full source and both compile invocations are given in the report):

```hlsl
float4 VCMain(
    nointerpolation float4 Color:COLOR0)
    : SV_TARGET0
{
#ifdef USE_GET_ATTRIBUTE_AT_VERTEX
    return GetAttributeAtVertex(Color,0);
#endif
    return Color;
}
```

`cmd.txt` compiles the buggy arm: `-T ps_6_1 -E VCMain -DUSE_GET_ATTRIBUTE_AT_VERTEX repro.hlsl`
(`ps_6_1` because `GetAttributeAtVertex` requires shader model 6.1's
barycentrics; the issue's own environment banner, `dxcompiler.dll` 1.7.2212.40,
also implies at least that model). `main-debug`'s output
(`out-main-debug.txt`) reproduces the issue exactly:

```
; Input signature:
;
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; COLOR                    0   xyzw        0     NONE   float
```

`Mask` is `xyzw` (the parameter is declared and every component survives DCE),
but `Used` is blank.

## Control

`variant-no-define-main-debug.txt`, same source and target compiled with
`--args "-T ps_6_1 -E VCMain repro.hlsl"` (`--expect no-match`, i.e. the
predicate must NOT fire) -- the only change from `cmd.txt` is dropping
`-DUSE_GET_ATTRIBUTE_AT_VERTEX`, so `return Color;` runs instead of
`return GetAttributeAtVertex(Color,0);`:

```
; COLOR                    0   xyzw        0     NONE   float   xyzw
```

`Used` is `xyzw` here, confirming `match.json`'s regex discriminates on exactly
the reported difference and does not fire on ordinary use of the same input.

## `match.json`

`all_of` of (a) `contains "; Input signature:"` as an anti-vacuity check that
compilation actually produced a disassembled signature table, and (b) a
`regex` anchored on the fixed-width `COLOR` row that requires nothing but
whitespace after `float` to end-of-line (`re.MULTILINE`). The control above is
what proves clause (b) can be false; clause (a) is never independently
falsified since every probe in this issue compiles cleanly, but is included
per the skill's standing anti-vacuity guidance for absence-style clauses.

## History

`bisect --linear` (full linear scan, since the range must be shown to be
uniformly one value, not just endpoint-agreeing):

```
v1.4.1907      repro
v1.5.2010      repro
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

result: always-repro'd across v1.4.1907..v1.9.2607
(5 probeable prereleases excluded by policy: v1.5.2003, v1.8.2306-preview,
v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24; 1 release with no
usable dxc asset skipped: v1.2.0-alpha)
```

No `invalid-probe` at any stable release -- `ps_6_1` and `GetAttributeAtVertex`
were already usable at the 2019-07-15 floor, so this predates the earliest
checkable release rather than merely "since it was filed" (filed 2023-07-13).

## Source corroboration

The usage mask is computed by `MarkUsedSignatureElements` in
`lib/HLSL/DxilPreparePasses.cpp` (around line 291), which walks every
instruction in the entry function and updates `El.SetUsageMask(...)` only for
`DxilInst_LoadInput`, `DxilInst_StoreOutput`, `DxilInst_LoadPatchConstant`,
`DxilInst_StorePatchConstant`, `DxilInst_StoreVertexOutput` and
`DxilInst_StorePrimitiveOutput`. It never constructs or checks a
`DxilInst_AttributeAtVertex` (the wrapper for `dx.op.attributeAtVertex`,
opcode 137, declared in `include/dxc/DXIL/DxilInstructions.h`). The
disassembly in `manual-case-godbolt-verify.txt` shows the entry point does
call `@dx.op.attributeAtVertex.f32` four times and forward each result to
`@dx.op.storeOutput.f32` -- so the intrinsic is fully lowered and its result
is genuinely used by the function, it is simply invisible to this one pass.
This is the strong form of evidence the skill asks for: a field the pass could
consult (the opcode is present in the IR right next to the ones it does
check) is provably never read by that pass, rather than an output
observation alone.

## Compiler Explorer

`https://godbolt.org/z/zWTG5Wrxv` (`dxc_1_6_2112`, CE's oldest DXC, and
`dxc_trunk`), args `-T ps_6_1 -E VCMain -DUSE_GET_ATTRIBUTE_AT_VERTEX`.
Both panes show the same blank `Used` column on the `COLOR` row and the
`call float @dx.op.attributeAtVertex.f32(...)` / `storeOutput` sequence,
confirming the defect predates CE's oldest DXC and survives to current
`main`. `godbolt-note.txt` names the exact row and column to check. Full pane
text archived in `manual-case-godbolt-verify.txt`; shortlink read back and
matched what was sent.

## Thread / labels

Maintainer `tex3d` confirmed on 2023-09-07 this is a legitimate bug: the mask
feeds inter-stage signature-linkage validation, so an upstream stage's
matching output could wrongly be treated as droppable. `damyanp` (2023-09-06)
says the motivating report came from a developer wanting to use *reflection*
to see which vertex attributes survive dead-code elimination -- the same
`Used`/mask data this issue is about is exactly what a reflection API such as
`ID3D12ShaderReflection` would expose, so the `reflection` label (currently
absent) fits and is proposed. A 2025-09-06 comment says it is still wanted.
No text on the issue is stale; the reported behaviour is unchanged today.

One pre-existing cross-reference on this issue's timeline
(`2024-03-25T17:24:40Z microsoft/hlsl-specs#181`), predating this triage.

## Provenance

`main-debug` is registered at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(public upstream). The local build's HEAD (`ced72eee3`) self-reports version
`7665270b9`, a merge commit (`Merge remote-tracking branch 'origin/main' into
triage`) whose only content on top of `89e2f98e2` is under
`.github/skills/dxc-issue-triage/`:
`git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df 7665270b9`
touches only files under that directory (5315 files, all under the skill
tree), and `git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD
-- . ':!.github/skills/dxc-issue-triage'` is empty. So no compiler source
differs from the cited public commit.

## Suggested action

`still-valid-keep-open`. Real, maintainer-confirmed, always-reproduces since
before the oldest checkable release, no fix landed in five and a half years
of releases.
