# #5668 -- DispatchMesh fails when given an empty struct

## Ground truth

`main-debug`, self-reports `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) -
1.9.0.5465 (triage, 7665270b9)`. `7665270b9` is a fork-local merge SHA that
resolves for nobody else; the citation below is the public upstream commit the
source corresponds to, proven by tree rather than by hash:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  -> 5315 files, every one under .github/skills/dxc-issue-triage/**
```

Control (proves the diff check can detect a real difference): the same
command against `89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50` reports 115
differing files outside the skill directory. **Cite
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` publicly.**

## Issue

Filed 2023-09-07 by @expipiplus1, one comment. Complete, self-contained
repro in the issue body:

```hlsl
struct S{};
[shader("amplification")]
[numthreads(1,1,1)]
void taskMain(uint tig_0 : SV_GROUPINDEX)
{
    S s;
    DispatchMesh(1U, 1U, 1U, s);
    return;
}
```

compiled `dxc a.hlsl -T as_6_6 -E taskMain`, reported against
`libdxcompiler.so: 1.7(dev;0-00000000)` on NixOS (Linux). Reported actual
behavior is a DXIL validation failure:

```
error: validation errors
a.hlsl:14:5: error: For amplification shader with entry 'taskMain', payload
size 4 is greater than declared size of 0 bytes.
```

**Repro quality: complete** -- used verbatim as `repro.hlsl`/`cmd.txt`, only
the filename changed (`a.hlsl` -> `repro.hlsl`).

**Maintainer comment (damyanp, 2024-10-10):** "We think that the validator is
correctly complaining about bad code that the compiler generated, so removing
the validation label." The root-cause read below (not disputed as a *result*,
only refined) shows the imprecise half of that sentence: the front end's own
declared-size bookkeeping is correct (0, matching the empty struct), and it is
the **validator's comparison operand**, not codegen, that is wrong -- see
"Root cause".

Cross-reference timeline (`gh api .../timeline`): no cross-reference events
on this issue.

## Result: reproduces verbatim

`out-main-debug.txt` -- `dxc -T as_6_6 -E taskMain repro.hlsl` exits
`2147500037` (`0x80004005`, E_FAIL -- an ordinary diagnosed validation
failure, not an internal failure) with:

```
repro.hlsl:7:5: error: For amplification shader with entry 'taskMain',
payload size 4 is greater than declared size of 0 bytes.
```

Identical wording and identical numbers (4 vs 0) to the quote in the issue
body.

## Predicate and controls

`match.json` is a `regex` anchored on `declared size of 0 bytes` (not on the
numeric mismatch amount, since a different empty-struct lowering size on
another release could still print a different first number for the same
defect).

- **Negative control** `control-nonempty-struct.hlsl`: `struct S{ uint x; }`
  (4 bytes) passed to `DispatchMesh` with a matching declared size --
  `variant-control-nonempty-main-debug.txt`, exit 0, full disassembly, no
  "payload size" text anywhere. `--expect no-match`, confirmed. Proves the
  predicate discriminates a size mismatch and does not fire on any
  `DispatchMesh`-with-struct-`S` call.
- **Isolation control** `-Vd` (skip validation) on the *same* empty-struct
  repro -- `variant-novalidate-main-debug.txt`, exit 0. The generated
  `out-novalidate.ll` records `!6 = !{!7, i32 0}` in `!dx.entryPoints`: the
  front end/codegen correctly declares a **0**-byte payload for `struct S{}`
  when nothing is checking it. `--expect no-match`, confirmed. This isolates
  the defect to the validator's comparison, not to front-end acceptance or to
  DXIL codegen for an empty payload.

## Root cause (source-read, not just behavioural)

`lib/DxilValidation/DxilValidation.cpp`, `ValidateAsIntrinsics` (line
~3233-3248, the AS-specific check run for every amplification shader's
`DispatchMesh` call):

```cpp
DxilInst_DispatchMesh DispatchMeshCall(DispatchMesh);
Value *OperandVal = DispatchMeshCall.get_payload();
Type *PayloadTy = OperandVal->getType();              // <-- pointer type, not pointee
const DataLayout &DL = F->getParent()->getDataLayout();
unsigned PayloadSize = DL.getTypeAllocSize(PayloadTy);
...
if (Prop.ShaderProps.AS.payloadSizeInBytes < PayloadSize) {
  ValCtx.EmitInstrFormatError(
      DispatchMesh, ValidationRule::SmAmplificationShaderPayloadSizeDeclared, ...);
}
```

`get_payload()` returns the `%struct.S*` **pointer** operand of the
`dispatchMesh` call; `OperandVal->getType()` is therefore the pointer type,
not the pointee struct type -- unlike the correctly-computed "declared" side
of the same comparison. DXIL's target datalayout declares 32-bit pointers
(confirmed in `out-main-debug.txt`'s emitted IR: `p:32:32`), so
`DL.getTypeAllocSize(PayloadTy)` on the *pointer* is a **constant 4**,
regardless of the payload struct's real size. That constant 4 is exactly the
number named in the diagnostic, for every input -- it is not derived from
`struct S{}` at all.

The value it is compared against,
`Prop.ShaderProps.AS.payloadSizeInBytes`, is computed correctly, in
`DxilModule::CollectShaderFlagsForModule`
(`lib/DXIL/DxilModule.cpp:382-393`):

```cpp
Type *payloadTy =
    dispatch.get_payload()->getType()->getPointerElementType();  // dereferences first
props.ShaderProps.AS.payloadSizeInBytes = DL.getTypeAllocSize(payloadTy);
```

which does dereference the pointer before measuring, and gives the correct 0
for `struct S{}` (confirmed by the `i32 0` in the isolation control above).

So the check is really testing "declared payload size (correct) < the
constant 4", not "declared size < actual size":

- any ordinary payload -- every payload struct with at least one ordinary
  member -- has a real size of at least 4 bytes on this datalayout, so
  `declared < 4` is false and the buggy check never fires. That is why this
  has been invisible on every non-empty payload since amplification shaders
  shipped.
- an **empty** struct is the one payload whose real declared size (0) is
  below the hard-coded 4, so `0 < 4` is true and the check fires on exactly
  this issue's input.

This is confirmed by measurement (the two controls above), not only by
reading the two functions.

**This is the same defect as #5269** (filed 2023-06-05, three months before
this issue, independently triaged in this batch with the identical
source-level finding and an equivalent control pair). Both issues report the
identical diagnostic text and the identical numeric mismatch (4 vs 0) for an
empty amplification-shader payload struct; #5269's notes independently
locate the same `ValidateAsIntrinsics` line. Recorded here as a measurement
(matching text, matching root-cause line, matching history), not asserted
without it.

## History

`bisect --linear` (v1.4.1907 floor, prereleases excluded by policy):

| release | result |
| --- | --- |
| v1.4.1907 | `invalid-probe` -- `error: invalid profile as_6_6` (predates SM 6.6) |
| v1.5.2010 | `invalid-probe` -- `error: invalid profile as_6_6` (predates SM 6.6) |
| v1.6.2104 .. v1.9.2607 (18 stable releases) | `repro`, every one |

**Always-repro'd for as long as it is checkable** -- since `as_6_6` first
shipped in a stable release (v1.6.2104, 2021-04-20), through the newest
stable release (v1.9.2607), and on `main`. Not a regression; this has never
worked. (#5269's own history uses `as_6_5` and is therefore checkable one
profile-generation earlier, back to v1.5.2010 -- consistent with one shared,
never-fixed defect rather than a version-specific one.)

## Compiler Explorer

https://godbolt.org/z/rqTqed5s8 -- `dxc_1_6_2112` (CE's oldest DXC) and
`dxc_trunk` both reproduce the identical diagnostic (verified by reading back
`api/shortlinkinfo`; full pane text in `manual-case-godbolt-verify.txt`). CE
runs Release builds and corroborates, rather than substitutes for, the Debug
ground truth and the release-matrix `bisect` above.

## Assessment

- **Status: repros.** Verbatim match to the reported diagnostic and its
  exact numbers; the finding is stronger than "still fails" -- source reading
  identifies the exact one-line defect (`ValidateAsIntrinsics` measures the
  payload pointer's alloc size instead of the pointee struct's) and explains
  why it is invisible on every non-empty payload.
- Whether DXC *should* accept a zero-byte payload is a language/policy
  question this triage does not decide (the reporter notes Vulkan permits an
  absent/empty task payload). Independent of that policy question, the
  validator's own bookkeeping is internally inconsistent: it computes the
  correct size (0) for the metadata it emits, then compares that value
  against an unrelated constant (the pointer size) rather than against the
  real payload size, to decide whether to reject it.
- **Confidence: high.** Reproduced verbatim locally and on two CE compilers;
  the discriminating source read plus two controls (non-empty payload clean,
  `-Vd` clean and declaring size 0) rule out both "this is a general AS
  regression" and "this is a front-end/codegen rejection". The same defect
  is independently confirmed in #5269 with a matching source-level finding.
