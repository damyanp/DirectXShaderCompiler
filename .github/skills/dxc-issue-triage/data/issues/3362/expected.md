# #3362 — expected symptom (written before running any compiler)

Issue: "pack-optimized issue with domain shader", filed 2021-01-19 by `turanszkij`.
One comment, 2024-04-11, from `damyanp` (MEMBER): *"Unfortunately we are unlikely to be able to
spend time on this now. However, we'd happily look at PR's addressing this issue."* — i.e. the
issue was acknowledged and left open, not diagnosed and not declared by-design.

## What the reporter says happens

A domain shader compiled with `-pack-optimized` gets a signature layout that does not match the
pixel shader that consumes it, so `ID3D12Device::CreateGraphicsPipelineState` fails at runtime:

```
D3D12 ERROR: ... Domain Shader - Pixel Shader linkage error: Signatures between stages are
incompatible. Semantic 'CLIP' of the input stage has a hardware register component mask that
is not a subset of the output of the previous stage. [ ... CREATEGRAPHICSPIPELINESTATE_SHADER_LINKAGE_REGISTERMASK ]
```

The signature struct is said to be shared between stages via a header:

```hlsl
struct PixelInput
{
    float4 pos  : SV_POSITION;
    float  clip : SV_ClipDistance0;
    float4 pre  : PREVIOUSPOSITION;
    float3 nor  : NORMAL;
};
```

Quoted tables (all three are also in the attached `disasm.zip`, unpacked under `attach/`):

* **DS output, `-pack-optimized`** — `PREVIOUSPOSITION` r0 `xyzw`, `SV_Position` r1 `xyzw`,
  `SV_ClipDistance` **r2 mask `w`**, `NORMAL` r2 `xyz`.
* **DS output, no `-pack-optimized`** — `SV_Position` r0, `SV_ClipDistance` **r1 mask `x`**,
  `PREVIOUSPOSITION` r2, `NORMAL` r3.
* **PS input** (reporter labels it "when using `pack-optimized`") — `SV_Position` r0,
  `SV_ClipDistance` **r1 mask `x`**, `PREVIOUSPOSITION` r2. No `NORMAL` row at all.

So the claimed defect is: the DS puts `SV_ClipDistance` in `r2.w` while the PS reads it from
`r1.x`, and the register/component masks therefore do not agree.

## What "this reproduces" means for the compiler

The runtime error is not compiler-observable, so the compiler-side symptom is the signature
table. Reproduction = **for a domain shader and a pixel shader whose interstage signature is
the same declaration, compiled with the same `-pack-optimized` flag, the DS output signature
and the PS input signature disagree on the register and/or component mask of at least one
element** (in the report, `SV_ClipDistance`).

Concretely I expect to look for, in the DS `; Output signature:` table:

```
; SV_ClipDistance          0      w        2  CLIPDST   float      w
```

against a PS `; Input signature:` table that puts `SV_ClipDistance` at register 1 mask `x`.

## Predictions to test (each can falsify the "compiler bug" reading)

1. **Both stages given `-pack-optimized`, identical struct.** If the two tables agree, the
   reporter's mismatch is a consequence of how the two shaders were compiled, not of DS
   packing. If they still disagree, it is a compiler bug.
2. **VS→PS control with the same struct and the same flag.** If VS/PS agree where DS/PS do
   not, the defect is domain-shader specific (the stage's second, patch-constant signature is
   the obvious suspect).
3. **The reporter's own attachment.** The three pasted command lines are recorded at the top of
   each dumped disassembly; check whether the PS was in fact compiled with `-pack-optimized`
   and whether its input struct really is the same four-element struct.

## Repro quality (as filed)

`partial` — the issue gives the struct, three signature tables, the runtime error and an
attachment containing the full disassemblies and the exact command lines, but **not** the HLSL
sources. The domain shader (its `[domain]` attribute, its patch-constant input and the hull
shader it pairs with) has to be reconstructed. Whatever I write is therefore
`agent-constructed` around a real, well-evidenced report.
