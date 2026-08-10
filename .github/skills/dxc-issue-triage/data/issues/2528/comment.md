> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2528](https://github.com/microsoft/DirectXShaderCompiler/issues/2528).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`), and on all 20 releases from
v1.4.1907 (2019-07) to v1.9.2607 — the whole checkable range, which starts before this was
filed. The repro in the body works as written.

**Compiler Explorer:** https://godbolt.org/z/EaYncchW3 (FXC, DXC 1.6.2112, DXC trunk; the
banner says which pane shows what).

`dxc -T vs_6_0 -E main` on the shader in the body:

```
error: validation errors

repro.hlsl:10: error: Not all elements of output SV_Position were written.
repro.hlsl:10: error: Not all elements of SV_Position were written.
Validation failed.
```

Adding `-Vd` shows the module behind that error:

```
; Output signature:
;
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; SV_Position              0   xyzw        0      POS   float      w

define void @main() {
  call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 3, float 1.000000e+00)  ; StoreOutput(outputSigId,rowIndex,colIndex,value)
  ret void
}
```

One `storeOutput`, and no `loadInput` at all — `x`, `y` and `z` are neither read nor written.
Empty the body and the same shader emits four `loadInput`/`storeOutput` pairs, so writing one
component is what suppresses the rest. FXC on the identical file at `/T vs_5_0` gives
`mov o0.xyz, v0.xyzx` / `mov o0.w, l(1.000000)`, with `Used = xyzw`.

### On the impact question

Re: [the 2024 note](https://github.com/microsoft/DirectXShaderCompiler/issues/2528#issuecomment-2176615654)
about real-life scenarios — `SV_Position` makes this loud, because that element *must* be fully
written, so the validator catches it and you get a compile error. On an ordinary varying there is
no such rule, and the same omission exits 0 with no diagnostic:

```hlsl
struct V { float4 pos : SV_Position; float4 uv : TEXCOORD0; };
void main(inout V v) { v.uv.x = 1; }
```

`dxc -T vs_6_0 -E main` **exits 0**, no diagnostic, validation passes:

```
; Output signature:
;
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; SV_Position              0   xyzw        0      POS   float   xyzw
; TEXCOORD                 0   xyzw        1     NONE   float   x

  call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 0, float 1.000000e+00)  ; StoreOutput(outputSigId,rowIndex,colIndex,value)
```

`TEXCOORD0` is declared `xyzw` but only `.x` is written, so `.yzw` reach the consumer
undefined. FXC emits `mov o1.x, l(1.000000)` / `mov o1.yzw, v1.yyzw`. This shape reproduces on
v1.4.1907 too.

### Labels

Suggest adding **`correctness`** — the varying case emits a shader with undefined output
components and no diagnostic. Keep `bug` and `fxc-disagrees`: FXC and DXC were run on the same
files and agree on all three controls, differing only on the two partial-write cases.

**`check-in-clang`** is currently unanswerable: `hlsl_clang_trunk` rejects
`inout float4 pos : SV_Position` with `attribute 'SV_Position' only applies to a field or
parameter of type 'float/float1/float2/float3/float4'`, and that same error fires on the
known-good empty-body control. Worth re-checking once Clang supports `inout` semantic
parameters.

No removals.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
