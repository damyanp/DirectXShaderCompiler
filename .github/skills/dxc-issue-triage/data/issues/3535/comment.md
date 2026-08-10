> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3535](https://github.com/microsoft/DirectXShaderCompiler/issues/3535).

Still accurate on `main` (1.9.0.5433, `13730886e`): there is no way to get
`mPos` / `mColor` from reflection, and the reason is stronger than "no API for
it" — the names are never emitted, so there is nothing an API could return.

**Why no call can reach them.** `ID3D12ShaderReflectionType` is the only
interface that names struct members, and the only methods on
`ID3D12ShaderReflection` that lead to one are `GetConstantBufferByIndex`,
`GetConstantBufferByName` and `GetVariableByName`. Nothing takes a signature
parameter index and returns a type. So @aclysma's observation is right about
the method — `CShaderReflectionType::GetMemberTypeName` does return the member
name, from `fieldAnnotation.GetFieldName()`
([DxilContainerReflection.cpp:796](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilContainerReflection.cpp#L796),
[:1318](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilContainerReflection.cpp#L1318)) — but it
can only be reached through a constant buffer or a named variable, so it
cannot be called for `VertexIn`. (It is probably also not a bug:
`DxilContainerTest.cpp` compiles the same shader with `d3dcompiler` and
asserts DXC returns the identical string, so it matches FXC.)

**Why the data is not there either.** Compiling your shader with a constant
buffer added alongside it, `-Qkeep_reflect_in_dxil` shows the reflection type
table naming the cbuffer struct's fields (tag 6 is the field-name tag):

```
!dx.typeAnnotations = !{!7, !13}
!7 = !{i32 0, %struct.CbStruct undef, !8, %Params undef, !11}
!9 = !{i32 6, !"cbAlpha", i32 3, i32 0, i32 7, i32 9}
```

There is no matching entry for `VertexIn`, and `%struct.VertexIn` is not in
the module's type list at all — entry-point struct parameters are scalarised
into signature elements during lowering, so nothing survives to annotate. The
input signature is metadata keyed by semantic:

```
!11 = !{i32 0, !"POSITION", i8 9, i8 0, !12, i8 0, i32 1, i8 3, i32 0, i8 0, !13}
```

The mapping you want does exist earlier: at `-fcgl`, before lowering, one
annotation carries both halves —

```
!14 = !{i32 6, !"mPos", i32 3, i32 0, i32 4, !"POSITION", i32 7, i32 9}
```

So supporting this is two pieces of work — preserve the annotation through
lowering, then design a way to expose it — not a descriptor field addition.

**This is not new.** Driving `ID3D12ShaderReflection` (via `dxa
-dumpreflection`) against every stable release from v1.4.1907 to v1.9.2607,
with each release's own `dxcompiler.dll`, no release reports the member names.
Nothing regressed.

**A workaround, if you control the compile.** `-Zi` keeps the names in debug
info:

```
!32 = !DICompositeType(tag: DW_TAG_structure_type, name: "VertexIn", ...)
!34 = !DIDerivedType(tag: DW_TAG_member, name: "mPos", scope: !32, file: !1, line: 32, baseType: !24, size: 96, align: 32)
```

Not reflection, and not something you would ship, but a code generator that
runs its own compile step can read it.

[Compiler Explorer](https://godbolt.org/z/aYqW8oeWE) — DXC 1.6.2112, DXC
trunk, and FXC. Look at the input-signature tables (semantics only) against
the buffer-definitions blocks (member names), in **both** compilers. Note that
CE appends `-Zi -Qembed_debug`, so the DXC panes contain `mPos` in debug
metadata and embedded source, and FXC's `// Initial variable locations:`
comment names `vin.mPos` too — none of that is reflection.

Suggested labels: `reflection`, `enhancement`, `api`. Whether to preserve and
expose parameter member names is a design decision for the reflection API, not
something this triage can settle.
[#2952](https://github.com/microsoft/DirectXShaderCompiler/issues/2952) asks
for a different missing piece of reflection data and may be worth tracking
alongside.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
