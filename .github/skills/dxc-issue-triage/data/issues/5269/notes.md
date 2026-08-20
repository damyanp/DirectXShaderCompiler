# #5269 -- Amplification shader: support for empty payload

## Ground truth

`main-debug`, self-reports `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465
(triage, 7665270b9)`. The self-reported commit `7665270b9` is a fork-local merge that
resolves nowhere public. Its tree is byte-identical to public upstream
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` outside this skill's own directory:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  -> only .github/skills/dxc-issue-triage/** paths differ
```

Control (proves the diff check can detect a real difference): the same command against
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50` reports 115 differing files outside the
skill directory. **Cite `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` publicly.**

## Issue

Filed 2023-06-05, no comments. Reporter says an amplification shader (`-T as_6_5`) whose
payload `struct` declares **no members** fails DXIL validation:

> For amplification shader with entry 'main', payload size 4 is greater than declared
> size of 0 bytes.

and says Vulkan permits an absent/empty task-shader payload, which complicates
cross-compiling engines that target both APIs. The reporter's repro is a link to a
third-party site, `shader-playground.timjones.io`, which is unreachable from this
environment (`WebFetchBlockedUrlError: No such host is known`). Cross-reference timeline
(`gh api .../timeline`) shows one external cross-reference,
`KhronosGroup/SPIRV-Cross#1974` (2023-06-18); it is a different repo's tracking issue and
adds no DXC-side information.

**Repro quality: agent-constructed.** `repro.hlsl` is written from the issue's own
description and this repository's existing amplification-shader test pattern
(`tools/clang/test/CodeGenHLSL/mesh-val/amplification.hlsl`), not copied from the
reporter's shader:

```hlsl
struct Payload
{
};

[numthreads(32, 1, 1)]
void main()
{
    Payload pld;
    DispatchMesh(32, 1, 1, pld);
}
```

## Result: reproduces verbatim

`out-main-debug.txt` -- `dxc -T as_6_5 -E main repro.hlsl` exits `0x80004005` (E_FAIL, an
ordinary diagnosed validation failure, not an internal failure) with:

```
repro.hlsl:9:5: error: For amplification shader with entry 'main', payload size 4 is
greater than declared size of 0 bytes.
```

Identical wording to the quote in the issue body, including the number 4.

## Root cause (source-read, not just behavioural)

`lib/DxilValidation/DxilValidation.cpp`, `ValidateAsIntrinsics` (the AS-specific check
run for every amplification shader's `DispatchMesh` call):

```cpp
Value *OperandVal = DispatchMeshCall.get_payload();
Type *PayloadTy = OperandVal->getType();                 // <-- pointer type, not pointee
const DataLayout &DL = F->getParent()->getDataLayout();
unsigned PayloadSize = DL.getTypeAllocSize(PayloadTy);
...
if (Prop.ShaderProps.AS.payloadSizeInBytes < PayloadSize) {
  ValCtx.EmitInstrFormatError(..., ValidationRule::SmAmplificationShaderPayloadSizeDeclared, ...);
}
```

`get_payload()` returns the `%struct.Payload*` pointer operand; `OperandVal->getType()`
is therefore the **pointer type**, not the pointee struct type -- unlike the correctly
written sibling check 40 lines below in the same function, which does
`cast<PointerType>(...)->getPointerElementType()` before measuring. DXIL's target
datalayout declares 32-bit pointers (`p:32:32`, confirmed in every captured `.ll`), so
`DL.getTypeAllocSize(PayloadTy)` on the *pointer* always evaluates to a constant **4**,
regardless of the payload struct's real size. That constant 4 is exactly the number the
reported diagnostic names.

The declared size compared against it,`Prop.ShaderProps.AS.payloadSizeInBytes`, is
computed correctly elsewhere (`DxilModule::CollectShaderFlagsForModule`, which does strip
the pointer) from the real struct type -- 0 for an empty struct, confirmed by the emitted
`!dx.entryPoints` metadata tuple `!6 = !{!7, i32 0}` in `variant-control-novalidate-main-debug.txt`.

So the check is really comparing "real declared payload size" against "the constant 4",
not against the real payload size at all:
- any ordinary payload (every existing test in this repo, and every real Vulkan-style
  payload with at least one member) has a real size of at least 4 bytes, so
  `declared < 4` is false and the buggy check never fires -- which is why this bug has
  gone unnoticed on every non-empty payload since mesh shaders shipped.
- an **empty** struct is the one case whose real size (0) is smaller than the pointer-size
  constant (4), so `0 < 4` is true and the check fires on exactly the input this issue is
  about.

This is confirmed, not merely argued: `control-nonempty-payload.hlsl` (a 4-byte, one-`uint`
payload -- the same shape as this repo's existing `mesh-val/amplification.hlsl` test) compiles
clean (`--expect no-match`, confirmed), and `-Vd` (skip validation) on the empty-struct repro
itself also compiles clean and emits the same `!6 = !{!7, i32 0}` size-0 tuple
(`variant-control-novalidate-main-debug.txt`, `--expect no-match`, confirmed) -- proving the
defect is entirely in this one validator comparison, not in front-end acceptance or DXIL
codegen for an empty payload.

## History

`bisect --linear` (`v1.4.1907` floor, prereleases excluded by policy):

| release | result |
| --- | --- |
| v1.4.1907 | `invalid-probe` -- predates SM 6.5 / mesh shaders (`as_6_5` unavailable) |
| v1.5.2010 .. v1.9.2607 (19 stable releases) | `repro`, every one |

**Always-repro'd for as long as it is checkable** -- i.e. since amplification shaders were
first shipped in a stable release (v1.5.2010), through the newest stable release
(v1.9.2607) and on `main`. Not a regression; this has never worked.

## Compiler Explorer

https://godbolt.org/z/WfqfzrK91 -- `dxc_1_6_2112` (CE's oldest DXC) and `dxc_trunk` both
reproduce the identical diagnostic (verified by reading back
`api/shortlinkinfo`; full pane text in `manual-case-godbolt-verify.txt`). CE runs Release
builds and corroborates rather than substitutes for the Debug ground truth and the
release-matrix `bisect` above.

## Assessment

- **Status: repros.** Verbatim match to the reported diagnostic; the finding is stronger
  than "still fails" -- source reading identifies the exact one-line defect
  (`ValidateAsIntrinsics`'s first payload-size check measures the pointer, not the
  pointee) and explains why it is invisible on every ordinary (non-empty) payload.
- Whether DXC *should* accept a zero-byte payload (matching Vulkan task-shader semantics,
  per the reporter) is a language/spec question this triage does not decide. But
  regardless of that policy question, the validator's own declared-size bookkeeping is
  internally inconsistent -- it computes 0 for the payload in the metadata it emits, then
  compares that 0 against the wrong operand's size to decide whether to reject it. That
  inconsistency is a defect independent of the empty-payload policy question.
- **Confidence: high.** Reproduced verbatim locally and on two CE compilers; the
  discriminating source read plus two controls (non-empty payload clean, `-Vd` clean)
  rule out both "this is a general AS regression" and "this is a front-end/codegen
  rejection".
