# #2792 — notes

**Title:** Need to report error when use constant which has offset bigger than
root constant size.
**Filed:** 2020-03-25 · **Labels:** `bug` · **Comments:** 0
**Ground truth:** `main-debug`,
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`
(verified against the expected string before anything else was run).

**Verdict: `repros` · `complete` · `always-repro'd` v1.4.1907..v1.9.2607 ·
suggested action `enhancement-not-bug`.**

---

## 1. What the issue asks for

The body is 250 characters: a complete (though unfenced) shader plus one
sentence. `RootConstants(b0, num32BitConstants = 1)` reserves one 32-bit word at
`b0`; the cbuffer bound there declares `float a; float b;`, so `b` sits at 32-bit
offset 1 — one word past the block. The reporter wants an error.

The symptom is therefore the **absence** of a diagnostic, which inverts the usual
shape and drives most of the method choices below. `expected.md` was written
before any compiler ran.

## 2. Repro and command

`repro.hlsl` is the issue body transcribed verbatim. `cmd.txt` is
`-T ps_6_0 -E main repro.hlsl` — the profile is inferred from
`float main() : SV_Target` and `ps_6_0` is the oldest that expresses it, which is
also what keeps every release in the bisection range probeable. No
`cmd-as-filed.txt`: the issue states no command line, so nothing was departed
from.

Repro quality is **`complete`**. The issue supplied source that runs as-is; only
the profile had to be supplied. It is not `prose-only` — the body has no
` ``` ` fence, which is a markdown fact, not a repro fact.

## 3. Ground truth

`out-main-debug.txt`: **exit 0, no diagnostic**, and the DXIL contains the
out-of-bounds read.

```
;       float a;                                      ; Offset:    0
;       float b;                                      ; Offset:    4
;   } cb;                                             ; Offset:    0 Size:     8
...
  %2 = call %dx.types.CBufRet.f32 @dx.op.cbufferLoadLegacy.f32(i32 59, %dx.types.Handle %1, i32 0)
  %3 = extractvalue %dx.types.CBufRet.f32 %2, 1
```

The cbuffer is 8 bytes; the root constant block reserves 4. `extractvalue …, 1`
is component 1 of the first cbuffer row — 32-bit offset 1, the word past the end.
**Reproduces.**

## 4. Predicate, and why it is shaped that way

`match.json` is `all_of` of three clauses, in this order:

1. `regex extractvalue %dx\.types\.CBufRet\.f32 [^,\n]+, 1\b` — **positive
   anchor**, the out-of-bounds read itself;
2. `not_regex (?i)\b(?:error|warning)\b` — the absence;
3. `nonzero_exit` inverted — exit 0.

Clause 1 is the load-bearing one. An absence clause is satisfied for free by a
compile that never started, and clause 1 makes that impossible: no rejected,
crashed or unparsed compile emits that line. The broad wording of clause 2 is
deliberate — the diagnostic being asked for does not exist in any DXC, so
SKILL.md's usual advice ("write the diagnostic text into `match.json` rather than
approximating it") has nothing to write. Broad-and-negated errs toward
*under*-reporting, which is the safer direction.

`[^,\n]+` rather than `%\d+` because v1.4.1907 names the handle
`%cb_cbuffer` and numbers the values differently; that release still matches.

### Controls — three, all captured, all re-checked by `reindex`

| capture | `--expect` | result | what it establishes |
| --- | --- | --- | --- |
| `variant-in-bounds-main-debug.txt` | `no-match` | `no-repro` ✔ | A **fully correct** shader (one float, `num32BitConstants = 1`, reads it) compiles clean and exit 0, but emits `extractvalue …, 0`, so the predicate does not fire. This is the check batch 002 shipped without: an absence-only predicate would have matched a correct shader and been indistinguishable from a bug that reproduces everywhere. |
| `variant-rs-register-mismatch-main-debug.txt` | `no-match` | `no-repro` ✔ | Root signature binds `b1`, cbuffer is at `b0`. dxc emits `error: Shader CBV descriptor range (RegisterSpace=0, NumDescriptors=1, BaseShaderRegister=0) is not fully bound in root signature.` and exits `0x80004005`. Predicate does not fire — **and** this proves root-signature-vs-shader validation actually runs under these exact arguments, so the missing size check is a gap *in* that validation, not validation failing to run. |
| `variant-rootconst-fits-main-debug.txt` | `match` | `repro` ✔ | **Identity control** (same shape as #1803). The repro with `num32BitConstants = 2`, i.e. entirely correct. The predicate fires, and the sameness is the finding — see §5. |

Two further captures validate the Compiler Explorer restatement:
`variant-compute-translation-main-debug.txt` (`--expect match`, scores `repro`)
and `variant-compute-in-bounds-main-debug.txt` (`--expect no-match`, scores
`no-repro`) — the transformation still reproduces, and removing the overrun still
makes the symptom go away, so the restatement measures the issue and not itself.

## 5. The strongest single piece of evidence: identical output

`repro.hlsl` (`num32BitConstants = 1`, out of bounds) and
`control-rootconst-fits.hlsl` (`num32BitConstants = 2`, correct) produce
**byte-identical** compiler output — same DXIL, same `shader hash:
7141c725ffb072dc89da3f675a30d39a`, same empty diagnostics. Diffing the two
captures below their headers leaves only the echoed filename.

Both shaders differ *only* in the root signature string, and the root signature
lives in a separate container part, so identical DXIL is expected — the point is
that **nothing else changed either**: no diagnostic, no exit-code difference.
`num32BitConstants` is not compared against anything.

## 6. Corroboration from source — the field is parsed and never read

Stronger than the output observation. `Num32BitValues` appears in
`lib/` and `tools/` in exactly these places:

| location | use |
| --- | --- |
| `tools/clang/lib/Parse/HLSLRootSignature.cpp:747` | parsed out of the attribute |
| `lib/DxilRootSignature/DxilRootSignatureSerializer.cpp:247,424` | serialised / deserialised |
| `lib/DxilRootSignature/DxilRootSignatureConvert.cpp:102` | version conversion |
| `lib/DxilRootSignature/DxilRootSignature.cpp:334` | printed back as text |
| `lib/HLSL/DxilPatchShaderRecordBindings.cpp:1144` | DXR shader-record layout |

**No validator reads it.** In particular
`lib/DxilRootSignature/DxilRootSignatureValidator.cpp:554` registers a root
constant like this:

```cpp
case DxilRootParameterType::Constants32Bit:
  AddRegisterRange(iRP, ROOT_CONSTANT, (unsigned)-1,
                   DxilDescriptorRangeType::CBV, Visibility, 1,
                   pSlot->Constants.ShaderRegister,
                   pSlot->Constants.RegisterSpace, DiagPrinter);
```

`Num32BitValues` is not passed at all: the block is recorded as a CBV range of
**one register**. The matching shader-side check (same file, `case
PSVResourceType::CBV:`) asks only `FindCoveringInterval(...)` and reports "is not
fully bound in root signature" when no range covers the register. Register
coverage, never size.

### Which mechanism would own the check

Worth stating precisely, because DXIL validation and root signature validation
are different things and this sits between them.

The existing shader/root-signature pairing check is
`VerifyRootSignatureWithShaderPSV`, called from
`lib/DxilValidation/DxilContainerValidation.cpp:1136,1252` and
`tools/clang/tools/dxcvalidator/dxcvalidator.cpp:135` — i.e. it **is** part of
DXIL container validation, which is why the `b1` control's output begins `error:
validation errors`.

But it works from PSV data, and `PSVResourceBindInfo0`
(`include/dxc/DxilContainer/DxilPipelineStateValidation.h:240`) is
`{ResType, Space, LowerBound, UpperBound}`; `PSVResourceBindInfo1` adds
`{ResKind, ResFlags}`. **No cbuffer size is carried**, so the validator cannot
perform this check on the data it currently reads — it would need a PSV format
change.

The alternative home is the HLSL front end, where the `[RootSignature("…")]`
attribute and the cbuffer layout are both in hand at compile time and no format
change is needed. That also fits the issue's wording ("report error when use
constant…"). **Which of the two is a design decision for maintainers**; the
measurable facts are that the check exists in neither, and that the container
validator's current inputs cannot express it.

## 7. History

`bisect --linear`, all 20 releases, **no probe skipped as `invalid-probe`**:

```
v1.4.1907 v1.5.2010 v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212
v1.7.2212.1 v1.7.2308 v1.8.2403 v1.8.2403.1 v1.8.2403.2 v1.8.2405 v1.8.2407
v1.8.2502 v1.8.2505 v1.8.2505.1 v1.9.2602 v1.9.2602.24 v1.9.2607     -> all repro
```

`--linear` rather than the default: a plain bisect short-circuits once both
endpoints agree, and full coverage is the stronger claim for "this check has
never existed". v1.4.1907's capture is the same clean exit-0 compile with the
same `extractvalue …, 1`.

**The floor is v1.4.1907 (2019-07)**, the oldest release shipping a usable `dxc`.
So `always-repro'd` means "for as long as it is possible to check", which happens
to reach back before the issue was filed (2020-03).

## 8. Compiler Explorer

**https://godbolt.org/z/d5zcrTPjP** — `dxc_1_6_2112`, `dxc_trunk`,
`hlsl_clang_trunk`, all `-T cs_6_0 -E main`. Verified by refetching the shortlink
and recompiling the source stored *in* it; panes captured in
`manual-case-ce-panes.txt` §2. All three exit 0 and emit `extractvalue …, 1`; the
DXC panes show `Size: 8`.

The link publishes `compute-translation.hlsl`, not `repro.hlsl`. Clang's DXIL
backend cannot lower any shader writing `SV_Target` — the pixel repro gives
`Unsupported intrinsic llvm.dx.store.output.f32 for DXIL lowering`, and so does a
one-line `float main() : SV_Target { return 0; }`, so a pixel Clang pane is stage
noise, not evidence. The compute restatement is checked both ways (§4) and
`repro.hlsl` remains the stage-accurate local evidence.

**Read the Clang pane carefully.** Clang does parse and check root signatures — a
malformed one gives `<source>:7:31: error: invalid parameter of RootSignature` —
but it also **accepts** a root signature binding `b1` while the cbuffer sits at
`b0`, which DXC rejects. So Clang has no root-signature-vs-shader checking yet at
all, and its clean pane means "not implemented there either", not an independent
judgement that the shader is fine. Both controls are in
`manual-case-ce-panes.txt` §1.

Pane noise that is *not* about the shader: `dxc_1_6_2112` prints `warning:
DXIL.dll not found … will not be signed`, and `hlsl_clang_trunk` prints an unused
`-Qembed_debug` argument warning. Both are Compiler Explorer's environment. The
first draft of `godbolt-note.txt` claimed "no error, no warning" and was wrong
for that reason; corrected before publishing.

## 9. Bug or feature request?

**Feature request** — `enhancement-not-bug` — on this evidence:

- the check has **never** existed, in any release back to the v1.4.1907 floor,
  and no code anywhere reads `Num32BitValues` for validation. Nothing regressed;
- the emitted DXIL is a faithful translation of the HLSL. The mismatch is between
  the shader and the root signature the author attached to it, which is exactly
  the class of thing `VerifyRootSignatureWithShaderPSV` exists to check — this is
  a gap in that check, not a miscompilation;
- the issue's own title is phrased as a request: "**Need to report** error
  when…".

Against that: DXC already rejects the neighbouring mistake (register not covered)
with an error, so a user could reasonably read the size case as an oversight in a
feature that is otherwise present. That is a fair reading, and it is why the draft
presents `enhancement` as a proposal rather than a correction.

Not asserted here, because it was not measured: whether D3D12 defines reading past
a root constant block as an error or as undefined behaviour, and therefore whether
the right diagnostic is an error or a warning. That is a product/language
decision and the draft says so.

## 10. Labels

Current: `bug`.

- **add `diagnostic`** ("Issues for diagnostics") — the issue is precisely a
  request for a diagnostic.
- **add `enhancement`** ("Feature suggestion") — per §9.
- **add `check-in-clang`** ("See if this repros in clang as well") — already
  checked, and the answer is on record: Clang does not diagnose it, and has no
  root-signature-vs-shader checking at all. The label still earns its place as
  routing, since whoever implements this should implement it in both front ends.
- **remove `bug`** ("Bug, regression, crash") — proposed, not asserted. Reason
  from the issue itself: the title is a request, the body describes unchecked
  behaviour rather than a malfunction, and 21 measured compilers behave
  identically so nothing regressed. The issue has **0 comments**, so there is no
  maintainer position in the thread being contradicted — but the label may have
  been applied deliberately, and the draft says the removal is a suggestion.

**Deliberately not proposed: `validation`.** Its description is "Related to
validation or signing" and SKILL.md records that it means *DXIL validation*
specifically, so it mislabels a request for a compile-time diagnostic. The
genuinely ambiguous part is that the neighbouring check *does* live in container
validation (§6) — but it cannot perform this one on the data it reads, so
applying the label would assert a mechanism the evidence does not support. Left
for a maintainer.

## 11. Confidence and limits

**High** for the measurement: 21 compilers, five captured controls, and the
source path is short enough to read end to end.

Limits, stated plainly:

- The predicate cannot see the root signature — dxc's default disassembly does
  not include the RTS0 part — so it is scoped to `repro.hlsl`'s fixed root
  signature and says "this input was accepted silently with the out-of-bounds
  access codegen'd". `control-rootconst-fits.hlsl` is what makes that limit
  visible rather than hidden, and is itself the §5 finding.
- Not tested: whether the D3D12 runtime, debug layer or `dxv` rejects the
  resulting container. This triage measures the compiler only.
- `dxc_trunk` on Compiler Explorer is a rolling build; the claim made about it is
  the class of behaviour (clean compile, no diagnostic), not a pinned symptom.
