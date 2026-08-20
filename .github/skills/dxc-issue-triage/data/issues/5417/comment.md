> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5417](https://github.com/microsoft/DirectXShaderCompiler/issues/5417).

Still reproduces on current `main` (89e2f98e2). Compiling the reported shader
with `-DUSE_GET_ATTRIBUTE_AT_VERTEX` still leaves the `COLOR` row's `Used`
column blank while `Mask` is `xyzw`:

```
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; COLOR                    0   xyzw        0     NONE   float
```

The same source compiled without the define shows `Used` as `xyzw` for the
identical row, so this is specific to reads through `GetAttributeAtVertex`.

Reproduces on every cached stable release back to v1.4.1907 (2019-07,
`ps_6_1`/`GetAttributeAtVertex` already usable there), through v1.9.2607, and
on Compiler Explorer's oldest DXC (`dxc_1_6_2112`) and `dxc_trunk`:
https://godbolt.org/z/zWTG5Wrxv. No release ever marks this input used.

Source-level cause: `MarkUsedSignatureElements`
(`lib/HLSL/DxilPreparePasses.cpp`) computes the `Used` mask by scanning for
`LoadInput`/`StoreOutput`/`LoadPatchConstant`/`StorePatchConstant` and their
vertex/primitive variants -- it never looks at `AttributeAtVertex`
(`dx.op.attributeAtVertex`), even though the disassembly shows the entry point
does call it and forwards every result to `storeOutput`. The value is fully
lowered and used; this one pass just never checks that opcode.

Given @tex3d's confirmation that this mask feeds inter-stage signature
validation, and that the original motivation was reflecting on which inputs
survive dead-code elimination, suggest adding the `reflection` label
alongside the existing `bug`/`correctness`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
