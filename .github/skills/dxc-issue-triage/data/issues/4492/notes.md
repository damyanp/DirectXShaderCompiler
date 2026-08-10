# #4492 — Broken codegen for loading elements from FP16 matrix types in StructuredBuffer

**Status: reproduces on `main`.** Verdict evidence below; every file named here is in
`<repo>/.github/skills/dxc-issue-triage/data/issues/4492/`.

Ground truth: `<repo>/build/Debug/bin/dxc.exe`, a clean Debug build of `main` at
`13730886e`, self-reporting `1.9.0.5433`. (The version string embeds a fork-local SHA,
`ab5400907`; captures are left verbatim because they are evidence.)

---

## 1. The claim, and what was measured

The reporter says that indexing a `float16_t4x4` inside a `StructuredBuffer` element
produces loads spaced 4 bytes apart instead of 2, so the accesses walk off the end of the
buffer element. That is exactly what happens, and it is still happening.

`repro.hlsl` is the attached `1-mat.hlsl`, byte-identical (SHA-256 verified). On `main`:

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

Sixteen loads at byte offsets `0, 4, 8, … 60`, spanning **62 bytes of a 32-byte element**.
The correct sequence is `0, 2, 4, … 30`. Every offset is exactly double.

Three things make this unambiguous rather than a reading of unfamiliar output:

- `$Element` is reported as **32** bytes, so the buffer layout itself is right. Only the
  access offsets are wrong.
- The `alignment` operand of each load is **2** — the true size of `half`. The same
  instruction therefore carries the correct scalar size *and* steps by twice it. It is
  internally inconsistent, which is a stronger signal than any external expectation.
- The last eight loads are past the element entirely.

The compiler exits 0 and DXIL validation passes. Nothing downstream catches this.

## 2. Not a row/column-major mix-up

A plausible alternative explanation for "wrong offsets in a matrix" is a packing
disagreement. It is not that. The doubling holds in *both* packings
(`manual-case-release-matrix.txt`, and derived from the type, not from output):

| shader | packing | DXC emits | correct |
|---|---|---|---|
| `minimal-matrix.hlsl` | `#pragma pack_matrix(row_major)` | `0, 4, 56, 60` | `0, 2, 28, 30` |
| `minimal-matrix-colmajor.hlsl` | default (column-major) | `0, 16, 44, 60` | `0, 8, 22, 30` |

Both rows are the correct sequence for their own packing, multiplied by two. A packing bug
would permute the offsets; this scales them.

## 3. Stores are wrong the same way — and write out of bounds

The issue is filed as a load bug. It is not limited to loads. `store-matrix.hlsl` writes
`a[0][1]` and `a[3][3]` of the same type in an `RWStructuredBuffer`:

```
call void @dx.op.rawBufferStore.f16(i32 140, %dx.types.Handle %1, i32 0, i32 4,  half 0xH3C00, half undef, half undef, half undef, i8 1, i32 2)
call void @dx.op.rawBufferStore.f16(i32 140, %dx.types.Handle %1, i32 0, i32 60, half 0xH4000, half undef, half undef, half undef, i8 1, i32 2)
```

Correct is 2 and 30. The second store lands 28 bytes past the end of the element — inside
the *next* element of the buffer. A silent cross-element write is a materially worse
symptom than a bad read, and it is worth recording on the issue even though the reporter
did not hit it.

## 4. Controls: the measurement is of the compiler, not of the harness

This is a wrong-code issue, so the predicate has to read emitted DXIL, which means it can
fail by measuring the disassembler. Both predicates (`match.json`, `match-store.json`) are
three-clause: an anchor self-test, an element-size self-test, and only then the symptom.

`control-half-vec-array.hlsl` and `control-store-half-vec-array.hlsl` replace `half4x4 a`
with `half4 v[4]` — the same 32 bytes, the same buffer, the same instructions, no matrix.
They score `no-match` with span exactly 32 on **all 21 compilers**, load and store
directions alike. So the predicate is not merely detecting "16-bit accesses in a structured
buffer"; it discriminates the matrix path specifically.

`manual-case-release-matrix.txt` scores 5 shaders × 21 compilers × 2 predicates
clause-by-clause. Across all 210 evaluations the element-size self-test is `1` every time
and there are zero parse warnings, so no `no-match` anywhere in this triage is a
disassembler-formatting artefact. The anchor clause is `0` exactly where it should be — a
load-only shader scored against the store predicate, and vice versa (63 and 42 rows).

## 5. History — the bisect boundary is a *shader-shape* boundary, not the defect's

`bisect --linear` over all 20 stable releases gives one clean transition: the reporter's
shader is clean on v1.4.1907 and v1.5.2010, and reproduces from **v1.6.2104** through
v1.9.2607 and `main`. No invalid probes.

**That is not when the bug was introduced, and reporting it that way would be wrong.**
Cutting the repro down to the snippet in the issue body (`minimal-matrix.hlsl`) reproduces
on **every** release checked, v1.4.1907 included.

The reason is visible in the old captures: on v1.4.1907/v1.5.2010 the reporter's shader
loads the whole 32-byte struct up front as four vectorised `mask=15` loads at 0, 8, 16, 24
and resolves the `switch` from registers, so the per-element matrix-subscript path never
runs. At v1.6.2104 *both* the repro and the control switched from vectorised to scalar
per-element loads — the control stayed correct at `0, 2, … 30`; only the matrix path picked
up the wrong stride.

So: the defect is older than any checkable release (v1.4.1907 is the bisection floor);
v1.6.2104 is where the reporter's shader shape started reaching it. Consistent with source
history — both functions in §7 date to `6ee4074a4`, the repository's first commit.

## 6. Reporter-instance fidelity

The reporter attached their own DXIL (`attachment/3-mat.dxil.asm`).
`compare-attachment.py` compares it mechanically against release captures rather than
eyeballing it: the whole `define void @testStructuredBufferMatrixLoad2` body is
**byte-identical** (whitespace-normalised) on v1.6.2112, v1.7.2207, v1.7.2212 **and today's
`main` Debug build**, with the same 16 offsets. Four years, no change. This is the
reporter's exact instance, not a lookalike reconstruction.

## 7. Root cause in source

`lib/HLSL/HLOperationLower.cpp`, `TranslateStructBufMatSubscript` (line 9233), lines
9244–9247 verbatim:

```cpp
  Constant *alignment = hlslOP->GetI32Const(DL.getTypeAllocSize(EltTy));

  Value *EltByteSize = ConstantInt::get(
      baseOffset->getType(), GetEltTypeByteSizeForConstBuf(EltTy, DL));
```

For `half`, `getTypeAllocSize` gives **2** and `GetEltTypeByteSizeForConstBuf` gives **4**.
Two adjacent lines disagree about the size of the same type, and the emitted instruction
carries both: the correct one as `alignment`, the wrong one as the stride.

The offset is then `baseOffset + idx * EltByteSize`, and that `idxList` feeds both
`GenerateRawBufLd` and `GenerateStructBufSt` — which is why loads and stores are wrong
identically.

`GetEltTypeByteSizeForConstBuf` (line 8092) returns 4 for anything ≤ 32 bits, under the
comment *"Constant buffer is 4 bytes align"* and a `TODO: Use real size after change
constant buffer into linear layout`. That is the cbuffer rule, and it is being applied to a
structured buffer, which is tightly packed. The function is even in a source region opened
by a `// Constant buffer.` comment.

For 32-bit element types the two happen to agree, which is why only 16-bit matrices are
affected. Note this predicts `int16_t`/`uint16_t` matrices are broken too — that is
*inferred from source*, not measured here; only `float16_t`/`half` was tested.

## 8. Clang does not share the defect

`hlsl_clang_trunk` compiles the same file and gets it right
(`manual-case-clang-comparison.txt`, generated by `ce-clang-probe.py`):

| | `minimal-matrix-colmajor.hlsl` | highest byte touched |
|---|---|---|
| `dxc_trunk` | `0, 16, 44, 60` | 62 — past the end of the 32-byte element |
| `hlsl_clang_trunk` | `0, 8, 22, 30` | 32 — inside it |

Exactly double, again. Clang models the member as `%struct.Data = type { [4 x <4 x half>] }`
— an array of vectors, i.e. the shape of the passing control in §4 — and strides by 2.

Two care points, both measured rather than assumed:

- Clang emits the *same* offsets with and without `#pragma pack_matrix(row_major)`, so it
  is not acting on the pragma and only the column-major row above is an apples-to-apples
  comparison. The row-major file is reported for completeness, not as a Clang finding.
- The skill's rule that a Clang *error* needs a control has a converse: a Clang *success*
  needs one too. `ce-clang-probe.py` compiles an inline 16-bit compute shader with no
  matrix on both compilers first; both emit an f16 access at alignment 2, so
  `-enable-16bit-types` is genuinely in effect and the f16 offset lists mean something.

This is a genuine cross-compiler difference, not a stage-support artefact — the repro is
already a compute shader, where Clang's support is complete.

## 9. Assessment

- **Status:** reproduces, `complete` repro, `high` confidence.
- **Suggested action:** still-valid-keep-open. The issue is accurate, the repro is minimal
  and self-contained, and the fix is a one-line size query in a function whose neighbouring
  line already computes the right value.
- **Labels:** `bug`, `matrix-bug`, `correctness` are all correct; no change proposed.
  Deliberately **not** adding `check-in-clang` — that comparison was run and is in §8.
- **Issue text is not stale.** The body's diagnosis ("4B between each element") is exactly
  right, and no comment contradicts it (the thread has none).
- One thing the issue does not say, and should: the same wrong offsets are used for
  **stores**, so this can silently corrupt a neighbouring buffer element.

## 10. Reproducing this

```
cd <repo>/.github/skills/dxc-issue-triage
python scripts/triage.py run --issue 4492                 # ground truth + predicate
python scripts/triage.py bisect --issue 4492 --linear     # release history
python data/issues/4492/measure.py                        # release matrix + controls
python data/issues/4492/compare-attachment.py             # attachment fidelity
python data/issues/4492/ce-clang-probe.py                 # Clang comparison (network)
```

Compiler Explorer: https://godbolt.org/z/3Pe367EfM — panes recorded in
`manual-case-godbolt-verify.txt`. CE's oldest DXC is 1.6.2112, already inside the broken
range, so the link corroborates today's behaviour but cannot show the v1.6.2104 boundary.
