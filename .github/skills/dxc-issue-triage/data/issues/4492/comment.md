> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4492](https://github.com/microsoft/DirectXShaderCompiler/issues/4492).

Still reproduces on `main` (1.9.0.5433, `13730886e`). Your diagnosis is exactly right: the
element stride is 4 bytes where it should be 2.

Compiling your attached `1-mat.hlsl` unchanged:

```
;   struct struct.Test2_0
;   {
;       row_major half4x4 m_0;                        ; Offset:    0
;   } $Element;                                       ; Offset:    0 Size:    32

%7  = call %dx.types.ResRet.f16 @dx.op.rawBufferLoad.f16(i32 139, %dx.types.Handle %2, i32 0, i32 0, i8 1, i32 2)
%9  = call %dx.types.ResRet.f16 @dx.op.rawBufferLoad.f16(i32 139, %dx.types.Handle %2, i32 0, i32 4, i8 1, i32 2)
                                                        ... 8, 12, 16, ... 56 ...
%44 = call %dx.types.ResRet.f16 @dx.op.rawBufferLoad.f16(i32 139, %dx.types.Handle %2, i32 0, i32 60, i8 1, i32 2)
                                          ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
```

Sixteen loads at `0, 4, … 60` — 62 bytes of a **32-byte** element, so the last eight read
past the end. `$Element` is correct, and each load's `alignment` operand is `2`, the real
size of `half`; the same instruction carries the right scalar size and steps by twice it.

The `define` body is byte-identical to the `.asm` you attached in 2022, on v1.6.2112,
v1.7.2207, v1.7.2212 and today's `main`.

**It is not a row/column-major mix-up.** For `a[0].xy` then `a[3].zw`, DXC emits `0, 4, 56,
60` row-major (correct `0, 2, 28, 30`) and `0, 16, 44, 60` column-major (correct `0, 8, 22,
30`) — each packing's correct sequence multiplied by two.

**Stores are affected the same way, and write out of bounds.** Writing `a[0][1]` and
`a[3][3]` through an `RWStructuredBuffer`:

```
call void @dx.op.rawBufferStore.f16(i32 140, %dx.types.Handle %1, i32 0, i32 4,  half 0xH3C00, ...)
call void @dx.op.rawBufferStore.f16(i32 140, %dx.types.Handle %1, i32 0, i32 60, half 0xH4000, ...)
```

Correct is 2 and 30; the second lands 28 bytes past the element, inside the next one. That
is a silent cross-element write.

**Source.** In `TranslateStructBufMatSubscript`
([`lib/HLSL/HLOperationLower.cpp#L9244`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/HLOperationLower.cpp#L9244))
the alignment is `DL.getTypeAllocSize(EltTy)` but the stride two lines later is
`GetEltTypeByteSizeForConstBuf(EltTy, DL)`, which returns 4 for anything ≤ 32 bits
("Constant buffer is 4 bytes align", with a `TODO: Use real size…`). That cbuffer rule is
being applied to a tightly-packed structured buffer. For 32-bit types the two agree. Only
`float16_t` was measured here.

**History.** A release scan puts your shader's first bad output at v1.6.2104, but that is a
shader-shape boundary, not the bug's: v1.4.1907 and v1.5.2010 load the whole 32-byte struct
up front as four `mask=15` loads and never reach the per-element path. Reduced to the
snippet in your issue body, it reproduces on **every** release back to v1.4.1907 — as far
back as I can check. `TranslateStructBufMatSubscript` dates to the repo's first commit.

**Clang gets it right.** In the linked panes `hlsl_clang_trunk` emits `0, 8, 22, 30` —
every offset inside the 32-byte element — where both DXC panes emit `0, 4, 56, 60`. Clang
models the member as `[4 x <4 x half>]` and strides by 2. One caveat when reading the link:
Clang lays the matrix out column-major regardless of `#pragma pack_matrix`, so those two
sequences are different layouts and only the *span* is directly comparable there. Compiling
the column-major variant locally makes it like-for-like — Clang `0, 8, 22, 30` against DXC
`0, 16, 44, 60`, exactly double again.

Compiler Explorer, three panes, on a minimal restatement of your snippet:
https://godbolt.org/z/3Pe367EfM

Labels look right as they are (`bug`, `matrix-bug`, `correctness`); not suggesting
`check-in-clang`, since that comparison is above.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
