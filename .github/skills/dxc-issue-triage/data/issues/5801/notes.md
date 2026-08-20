# #5801 — Sample immediate offset range is not diagnosed or validated in SM 6.7

## Ground truth

`main-debug`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, version string
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`.

## Symptom (see `expected.md`, written before any probe ran)

The reporter's `repro.hlsl` calls `T2D.Sample(S, coord, int2(12, -14))`. `-8..7` is the only
legal range for an immediate (constant) texture-access offset. At `-T ps_6_6` and earlier this
is rejected both by the front end/legalizer (`error: Offsets to texture access operations must
be between -8 and 7.`) and, for a hand-built `.ll` module skipping HLSL entirely, by
`DxilValidation` directly (`%dxv`: `offset texture instructions must take offset which can
resolve to integer literal in the range -8 to 7.`). At `-T ps_6_7` and later, the issue claims
neither check fires and the out-of-range constant reaches the final DXIL untouched.

## Root cause (read from source, not inferred)

Two independent guards were both given an unconditional `SM 6.7+` bypass when SM 6.7 added
"Advanced Textures" / programmable (non-constant) offsets, apparently intending to stop
flagging a *non-constant* offset value (now legal) but instead also silencing the
*constant-out-of-range* case that was never legalized by that feature:

- `lib/HLSL/DxilLegalizeSampleOffsetPass.cpp:88-90`
  (`DxilLegalizeSampleOffsetPass::runOnFunction`):
  ```cpp
  // If 6.7 or more, permit remaining "illegal" offsets
  if (DM.GetShaderModel()->IsSM67Plus())
    return true;
  ```
  This return skips `FinalCheck`, the only place that emits
  `"Offsets to texture access operations must be between -8 and 7."` — for *any* remaining
  illegal offset, constant or not.

- `lib/DxilValidation/DxilValidation.cpp:369-381` (`ValidateResourceOffset`'s `ValidateOffset`
  lambda):
  ```cpp
  auto ValidateOffset = [&](Value *Offset) {
    // 6.7 Advanced Textures allow programmable offsets
    if (pSM->IsSM67Plus())
      return;
    if (ConstantInt *cOffset = dyn_cast<ConstantInt>(Offset)) {
      int Offset = cOffset->getValue().getSExtValue();
      if (Offset > 7 || Offset < -8) {
        ValCtx.EmitInstrError(CI, ValidationRule::InstrTextureOffset);
      }
    } else {
      ValCtx.EmitInstrError(CI, ValidationRule::InstrTextureOffset);
    }
  };
  ```
  Same shape: the `IsSM67Plus()` early return is unconditional, so a `ConstantInt` offset is
  never range-checked once SM 6.7+ is targeted — the comment's own rationale ("programmable
  offsets") only justifies skipping the `else` branch (a non-constant offset), not the
  `ConstantInt` branch directly above it.

This confirms maintainer python3kgae's 2023-10-12 comment attributing the bug to
[PR #4260](https://github.com/microsoft/DirectXShaderCompiler/pull/4260) ("Implement Shader
Model 6.7", merged 2022-02-15): both call sites still read exactly this way at ground truth, so
neither guard was ever narrowed to the non-constant case the comment describes.

## Repro and controls

`cmd.txt`: `-T ps_6_7 -E main repro.hlsl`, `repro.hlsl` copied verbatim from the issue body.
`match.json`: `all_of[exit==0, not_contains "Offsets to texture access operations must be
between -8 and 7"]` — the exit-0 clause is required per the skill's absence-predicate warning,
so an unrelated compile failure can't be scored as "the range check is silently skipped".

- **Primary probe** (`out-main-debug.txt`): exit 0, clean disassembly, `Sample(...)` operands
  `i32 12, i32 -14` embedded verbatim in the final DXIL — **repro**. This is the identical DXIL
  shape (same op, same literal offsets) the reporter attached from their own `1.7.2308.7` build.
- **Negative control, same shader at `-T ps_6_6`** (`variant-control-sm66-main-debug.txt`,
  `--expect no-match`): exit `0x80004005` (E_FAIL, an ordinary diagnosed error — not a crash),
  `error: Offsets to texture access operations must be between -8 and 7.` — confirms the
  predicate's `not_contains` clause can and does fail when the diagnostic is present, i.e. it
  is not vacuously satisfied. Control passed as declared.
- **Compiler Explorer** (`godbolt.txt`, `manual-case-godbolt-verify.txt`,
  link https://godbolt.org/z/WT19a1jbM): `dxc_1_6_2112` (CE's oldest DXC, predates SM 6.7)
  correctly rejects the profile (`invalid profile ps_6_7`, exit 5); `dxc_trunk` reproduces —
  exit 0, `i32 12, i32 -14` reach the disassembly unchanged. Corroborates the local Debug
  ground truth on an independent Linux Release build. `godbolt-note.txt` names the structural
  location (the `Sample` op's offset operands) rather than quoting the diagnostic text, since
  the note is compiled into the shared source and would otherwise manufacture a hit.

## History (`triage.py bisect --issue 5801`)

```
v1.4.1907 / v1.5.2010 / v1.6.2104 / v1.6.2106 / v1.6.2112   invalid-probe (profile ps_6_7 did
                                                             not exist yet -- "invalid profile
                                                             ps_6_7", exit 0x80004005)
v1.7.2207                                                   repro
v1.9.2607                                                   repro
result: always-repro'd across v1.7.2207..v1.9.2607
```
5 prereleases (v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, v1.10.2605.2,
v1.10.2605.24) were excluded from the search by policy; the issue names none of them.
v1.4.1907 through v1.6.2112 correctly demote to `invalid-probe`: SM 6.7 did not exist before
v1.7.2207 (the shader model that introduced the very bypass under test), so those releases
never reached the code under test rather than having fixed it — there is no earlier stable
release that *could* have shown this symptom. v1.7.2207 is the oldest SM-6.7-capable stable
release and already reproduces, matching the two source citations above (both guards shipped
unconditionally with SM 6.7 itself in PR #4260, not added later). Every probeable stable
release from v1.7.2207 onward reproduces, with no clean release in between — this is not a
regression, it is a gap present since the feature it rides in on was introduced, and it
remains present at ground truth (`89e2f98e2`) and on `dxc_trunk`.

## Assessment

- **Status:** `repros`.
- **History:** `always-repro'd` (since SM 6.7's introduction in v1.7.2207 — the bisection floor
  for this particular symptom, since no earlier release can even target the profile).
- **Repro quality:** `complete`.
- **Confidence:** `high` — root cause read directly from both guard sites, both still present
  verbatim at ground truth, both corroborated by the compiled probe and by a second,
  independent, Linux Release build (Compiler Explorer trunk).
- **Text-stale:** none. The issue's title and body still accurately describe current behaviour
  in every particular checked (front-end diagnostic absent, DXIL validation absent, out-of-
  range offset reaches final DXIL) — nothing has since narrowed or widened the gap.
- **Suggested action:** `still-valid-keep-open`. This is a real, currently-reproducing
  correctness gap in both the legalizer and the validator with an identified, still-present
  root cause in two named source locations; nothing in the thread indicates it was
  intentionally accepted as permanent behaviour, and PR #4260's own comment code
  ("6.7 Advanced Textures allow programmable offsets") reads as a bypass meant for *non-constant*
  offsets that was applied one branch too broadly.
- **Labels:** current `bug, sm6.8, validation` are all still accurate (this is a bug; pow2clk's
  2023-10-03 comment that it is "relevant to 6.8 because of the SampleCmp* variants that take
  offsets" was not independently re-verified here — no SM 6.8-specific probe was run, since
  ground truth's `IsSM67Plus()` guards already cover 6.8 by construction; and this is squarely a
  `DxilValidation`/legalizer defect). Proposing to add `sm6.7`: the label exists in the live
  taxonomy, is currently absent from the issue, and names the shader model that both root-cause
  guards key off of and where the gap first became reachable (v1.7.2207) — `sm6.8` alone does
  not record that the defect originates one shader model earlier.

## Method notes

- No crash/assert is involved, so the ordinary `internal_failure` guidance does not apply here;
  the symptom is a missing diagnostic on an otherwise-successful compile, which is the
  absence-predicate shape the skill discusses at length. The mandatory positive anchor here is
  "compile exit 0", not a printed artifact, since the interesting absence is a *diagnostic*, not
  a DXIL construct.
- `dxv.exe` is not built alongside `main-debug` in this environment (`build/Debug/bin/` has no
  `dxv.exe`), so the issue's second, validator-only `.ll` + `%dxv` `RUN:` line was not run as a
  standalone validator invocation. It was not needed: `dxc` runs `DxilValidation` by default
  (no `-Vd` passed anywhere in `cmd.txt`), so the primary probe's exit-0 result already requires
  that the validator did not reject the module either, and `ValidateResourceOffset`'s
  `IsSM67Plus()` guard was read directly from source rather than inferred. Recorded here rather
  than promoted to `SKILL.md`, since it is specific to this environment's build outputs rather
  than a general method gap.
