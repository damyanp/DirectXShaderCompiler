# #4168 — expected symptom

Written **before** running any compiler, per SKILL.md step 2.

Issue: "Can't get cbuffer's variables from a linked shader" (gongminmin, 2022-01-03),
labels `bug`, `reflection`, `shader-linking`.

## What the issue says

Body:

> Reflect a linked shader, the D3D12_SHADER_BUFFER_DESC::Variables of its cbuffers are 0.
>
> Traced a little bit. The DxilStructAnnotation of that struct is NULL, causing the variables
> of that cbuffer can't be reflected.

Comment 2022-01-22:

> The problem is mutateCandidates(). It mutate the type in modules. But in
> DxilLinkJob::AddGlobals(), it gets the mutate type to search the annotation, which always
> fail.

Comment 2022-01-23 — this is the one that pins the configuration:

> My usage is compile modules in lib_6_x profile, and link to ps_6_0. There are 2 problems in
> reflecting the linked shader.
>
> Problem 1: The type of a GlobalVariable is mutated, but the type in
> DxilTypeSystem::m_StructAnnotations is not. As a result, in DxilLinkJob::AddGlobals, it
> can't find a cbuffer's annotation from a mutated type. Override the type with resource's
> HLSLType can fix this. However, it still doesn't work end-to-end due to problem 2.
>
> Problem 2: During linking, in DxilMDHelper::LoadDxilResourceBase, it only load the HLSLType
> for SM6.6+. In my case, the link profile is ps_6_0, which doesn't have the type mutation. So
> a cbuffer doesn't have HLSLType here, then no annotation. This causes the variables in the
> cbuffer is not reflect-able.

## Reported configuration

| | |
| --- | --- |
| library compile | `-T lib_6_x` |
| link target | `ps_6_0` |
| observed | reflected cbuffer of the **linked** shader has `Variables == 0` |
| root cause claimed | `DxilStructAnnotation` for the cbuffer struct is null after linking |

`lib_6_x` matters: `kOfflineMinor = 0xF` (`include/dxc/DXIL/DxilShaderModel.h:47`), so `lib_6_x`
is shader model 6.15 and `IsSM66Plus()` is true for it. That is what makes
`DxilMutateResourceToHandle` run on the library
(`lib/HLSL/DxilPromoteResourcePasses.cpp:272-280`) and what makes the reporter's
lib-above-6.6 → shader-below-6.6 direction the interesting one.

## Repro quality

`prose-only` as filed: no shader, no command line, no attachment. The 2022-01-23 comment
names the two profiles, so the *configuration* is the reporter's; the HLSL source and the
exact command chain are mine. The committed repro is therefore **agent-constructed against a
reporter-specified configuration**, and the write-up must say so.

## Is this observable from the command line at all?

Open question at the time of writing; the answer must come from evidence, not from wanting
one. The report is about `D3D12_SHADER_BUFFER_DESC::Variables`, an `ID3D12ShaderReflection`
field, and `dxc.exe` never calls that interface. Two candidate routes:

1. **`dxa -dumpreflection`.** `DxaContext::DumpReflection` (`tools/clang/tools/dxa/dxa.cpp:416`)
   loads the container through `IDxcContainerReflection`, asks for the DXIL part's
   `ID3D12ShaderReflection`, and hands it to `hlsl::dump::D3DReflectionDumper`. That dumper
   *does* read the field under test: `Dump(D3D12_SHADER_BUFFER_DESC&)` prints
   `Num Variables: <Desc.Variables>` (`lib/DxilContainer/D3DReflectionDumper.cpp:115`) and
   enumerates `GetVariableByIndex` only `if (Desc.Variables)`
   (`D3DReflectionDumper.cpp:280-288`). So the reported number is printed verbatim, and the
   absence of variable records is visible in the same dump. If `dxa` can read a `dxl` output
   container, this is a real CLI route to the exact field.
2. **Disassembly of the linked module.** `!dx.typeAnnotations` carrying (or not carrying) a
   struct annotation for the cbuffer type is the underlying cause the reporter names. This is
   corroborating evidence, not the reported symptom.

If neither route reaches the field, `not-compiler-verifiable` is the honest verdict and must
be recorded as such rather than replaced by a probe of something adjacent.

## What "this reproduces" means

Given a single-cbuffer library compiled `-T lib_6_x`, linked to `ps_6_0` with `dxl`, and the
linked container dumped with `dxa -dumpreflection`:

**repros** — the dump names the cbuffer (`D3D12_SHADER_BUFFER_DESC: Name: CB0`) and reports
`Num Variables: 0`, with no `ID3D12ShaderReflectionVariable` records under it.

**does-not-repro** — the same dump reports `Num Variables: 2` and lists both variables
(`m`, `f`) with their types.

**changed-behavior** — the chain now fails somewhere it did not before (link error, dumper
failure, crash), i.e. the cbuffer variables are still unavailable but for a different reason.

**inconclusive / not-compiler-verifiable** — no CLI route reaches
`D3D12_SHADER_BUFFER_DESC::Variables` for a linked container.

## Predicate plan

Primary predicate (`match.json`) must be an `all_of`, because the reported symptom is an
**absence** (`Variables == 0`) and SKILL.md's absence rules apply in both directions:

- positive anchor 1: the dump reached the constant buffer at all —
  `D3D12_SHADER_BUFFER_DESC: Name: CB0`. Without this a failed compile, a failed link or a
  dumper that printed nothing scores as a perfect reproduction.
- positive anchor 2: the shader really has the cbuffer bound — `Name: CB0` with
  `Type: D3D_SIT_CBUFFER` in `Bound Resources`. This is the anti-vacuity clause: a shader that
  never declared a cbuffer must not satisfy the predicate for free.
- the symptom itself: `Num Variables: 0`.

Controls, both required:

- **negative control** (`--expect no-match`): the *same source* compiled straight to `ps_6_0`
  by `dxc` with no library and no link step, dumped the same way. Reflection there is known to
  work, so the predicate must not fire. This is the control that proves the predicate
  discriminates rather than matching every reflection dump.
- **instrument control** (`--expect no-match`): the `lib_6_x` library container itself,
  dumped before linking. If the library dump already shows `Num Variables: 0`, the defect is
  not in the linker and the whole framing changes.

## Prior-art note (source only; not a measurement)

`tools/clang/test/HLSLFileCheck/hlsl/linker/resources/preserve_cb_types.hlsl` exists in the
tree and checks exactly this shape (`lib_6_x` → `vs_6_5/6_6/6_7`, reflection dump,
`Num Variables: 2`). It was added by `bf015d2e1` ("Fix loss of buffer type info with libraries
and linker (#5197)", 2023-05-10), together with the two source changes the reporter's comment
predicts: a `CopyTypeAnnotation(res->GetHLSLType(), ...)` in `DxilLinkJob::AddGlobals` and a
change in `LoadDxilResourceBase`. That test targets `vs_6_5`, **not** the reporter's `ps_6_0`,
and the current `LoadDxilResourceBase` still reads the HLSL type only under
`m_pSM->IsSM66Plus()` (`lib/DXIL/DxilMetadataHelper.cpp:732`). So the source suggests a fix
exists, and the measurement must decide whether the reporter's own `ps_6_0` configuration is
covered by it. Predicting the answer here would be the mistake; the probe decides.
