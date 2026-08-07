> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2792](https://github.com/microsoft/DirectXShaderCompiler/issues/2792).

Still reproduces on `main` (1.9.0.5433, `ab5400907`) and in all 20 release probes back to
v1.4.1907. Every probe exits 0 and codegens the out-of-bounds read; none diagnoses it.

The repro from the description compiles clean, exit 0, no diagnostic:

```
;   } cb;                                             ; Offset:    0 Size:     8
  %2 = call %dx.types.CBufRet.f32 @dx.op.cbufferLoadLegacy.f32(i32 59, %dx.types.Handle %1, i32 0)  ; CBufferLoadLegacy(handle,regIndex)
  %3 = extractvalue %dx.types.CBufRet.f32 %2, 1
```

The cbuffer is 8 bytes, the root constant block reserves 4, and `extractvalue …, 1`
is the read of the word past the end.

Compiler Explorer, all three panes agreeing: **https://godbolt.org/z/d5zcrTPjP**
(restated as a compute shader so `hlsl_clang_trunk` can lower it; the pixel form
behaves the same in DXC).

**No validator compares `num32BitConstants` against the cbuffer size.** Changing it
from `1` to `2` — making the shader entirely correct — produces identical
disassembly and the same shader hash. In `DxilRootSignatureValidator.cpp` a root
constant block is registered as a CBV range of one register and `Num32BitValues`
is not passed in; the field is parsed, serialised and printed, but no validator
reads it.

Nearby checking does run, so this is a gap in it rather than its absence — binding
`b1` while the cbuffer sits at `b0` is rejected:

```
error: Shader CBV descriptor range (RegisterSpace=0, NumDescriptors=1, BaseShaderRegister=0) is not fully bound in root signature.
```

That check is `VerifyRootSignatureWithShaderPSV`, which reads PSV bind info
(`ResType, Space, LowerBound, UpperBound`) — no cbuffer size is carried there, so
it cannot make this comparison from the data it reads today. The front end has
both the `[RootSignature(...)]` string and the cbuffer layout in hand. Which
should own the check is a design call.

`hlsl_clang_trunk` does not diagnose it either, but that is weak evidence: it
also accepts the `b1`/`b0` mismatch above, so its silence is "not implemented
there either" rather than an independent judgement.

**Labels:** suggest adding `diagnostic`, `enhancement` and `check-in-clang`. Since
no probed release has this check and nothing regressed, `bug` may be worth
dropping — though the neighbouring case being an error makes "oversight" a fair
reading too. That removal is a suggestion; I may be missing history behind the
label. Whether the right diagnostic is an error or a warning, and whether the
D3D12 spec makes this invalid or undefined, are product decisions and not
something this triage measured.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
