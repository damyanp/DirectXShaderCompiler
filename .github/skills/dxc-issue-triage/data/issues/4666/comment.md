> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#4666](https://github.com/microsoft/DirectXShaderCompiler/issues/4666).

Still reproduces on `main` (`dxcompiler.dll: 1.10(5433-ab540090)`). It is a regression, and the
boundary is **v1.7.2207**: the five stable releases through v1.6.2112 accept the repro; all
15 later releases reject it.

Repro, v1.6.2112 next to trunk: https://godbolt.org/z/1Mbe8oPcj

```text
repro.hlsl:12:61: error: variable has incomplete type 'SamplerState [2]'
```

The three tested non-templated builtin types—`SamplerState`,
`SamplerComparisonState`, and `ByteAddressBuffer`—fail in array parameters;
the tested templated texture types compile. Scalar parameters also compile.
The reported struct workaround is really declaration ordering: an earlier
declaration that requires type completion suppresses the error, while the same
declaration later, or a typedef that merely names the array, does not.

That points at the on-demand completion introduced by #4317, which made builtin object types
start life incomplete and be completed by `HLSLExternalSource::CompleteType`, and the array-element
completion added in `Sema::RequireCompleteTypeImpl` by #4379. Both land inside the
v1.6.2112 → v1.7.2207 window. The test added with #4379,
`tools/clang/test/HLSLFileCheck/hlsl/template/complete-array-parameter.hlsl`, covers
`Texture2D f[2]` only—the working templated case. Intermediate commits were not
built, so this is a lead rather than a bisect.

**On the SPIR-V half.** It still reproduces, but the module has been invalid for longer than it
looks. v1.6.2104 emits the same `%Test = OpTypeStruct %_arr_type_sampler_uint_2` and exits 0,
because its bundled SPIRV-Tools predates `VUID-StandaloneSpirv-None-04667`. So the apparent
v1.6.2106 boundary is a validator upgrade, not a compiler change — DXC has emitted this for as
long as it can be measured. Reproducing it also needs `[noinline]`; otherwise the helper is
inlined and the struct type is never emitted.

**Adjacent defect:** suppressing inlining on the struct workaround crashes the
current Debug build with `Internal compiler error: LLVM Assert`. Replacing the
sampler array with a scalar produces an ordinary resource-pointer diagnostic,
so the array in the aggregate is the discriminating variable.

**Labels:** suggest adding `type-system` and `diagnostic` — correct code is rejected because of an
inconsistency in when builtin object types are completed. `spirv` is right for the second half but
the primary symptom is front-end and shows up identically for DXIL, so this may need an owner
outside the SPIR-V area.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
