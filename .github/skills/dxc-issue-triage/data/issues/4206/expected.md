# #4206 — expected symptom (written before running anything)

**Issue**: "Incorrect 'D3D_SVF_USED' flag with fields in $Globals_cbuffer"
(microsoft/DirectXShaderCompiler#4206, filed 2022-01-25 by momo55555, label `reflection`,
0 comments).

## What the reporter claims

The attached compute shader declares three globals that land in the implicit `$Globals`
constant buffer:

| global | type | referenced by the entry point? |
| --- | --- | --- |
| `WorldPosToProbeCoord[6]` | `float4[6]` | yes |
| `ProbeCoordToWorldPos[6]` | `float4[6]` | yes |
| `SkyLightColor` | `float4` | **no** |

`ID3D12ShaderReflection` nevertheless reports `D3D_SVF_USED` in the
`D3D12_SHADER_VARIABLE_DESC::uFlags` of `SkyLightColor`.

The reporter's own root-cause hypothesis, quoted from the body:

> `'ProbeIndex - 1'` is used to index global constant `WorldPosToProbeCoord[6]`, but since
> `ProbIndex` is a dynamic variable, it is deduced to value 0 in the compiler. This will lead
> to use offset `-1` to access `$Globals_cbuffer` with `CBufferLoadLegacy`. […] if `offset`
> is `-1`, the last field in the struct will be marked used incorrectly no matter what.

He quotes `MarkCBUse()` from `DXilCondenseResources.cpp` (`upper_bound(offset); it--;`).

## "This reproduces" means

For the shader exactly as filed, compiled as a compute shader:

1. reflection for the `$Globals` constant buffer lists a variable named `SkyLightColor`, **and**
2. its `uFlags` carries `D3D_SVF_USED`.

Both clauses are required. Clause 1 is the **instrument self-test**: if the reflection reader
prints nothing, prints under a different key, or the variable is absent, then clause 2 is
unmeasurable rather than clean. An absence of `D3D_SVF_USED` with no `SkyLightColor` line at
all is *not* evidence of a fix.

"Does not reproduce" means the dump names `SkyLightColor` and its `uFlags` is `0` (or any
value without `D3D_SVF_USED`).

## Is this observable from a command line at all? — open question, to be settled by evidence

The reported symptom is a value returned by `ID3D12ShaderReflection`, which `dxc.exe` never
calls. Three candidate instruments, in preference order:

1. **`dxa -dumpreflection`** on the compiled container. `lib/DxilContainer/D3DReflectionDumper.cpp:98-107`
   dumps `D3D12_SHADER_VARIABLE_DESC` including
   `WriteLn("uFlags: ", FlagsValue<D3D_SHADER_VARIABLE_FLAGS>(varDesc.uFlags))` (line 104),
   and `D3DReflectionStrings.cpp:526` spells `D3D_SVF_USED`. It reaches the value through
   `pVar->GetDesc(&varDesc)` (line 254), i.e. the real accessor. If this works it is a
   genuine CLI route and no host program is needed.
2. The underlying **DXIL metadata bit**. `SetCBVarUsed` is serialised as
   `kDxilFieldAnnotationCBUsedTag = 9` (`include/dxc/DXIL/DxilMetadataHelper.h:252`,
   written at `lib/DXIL/DxilMetadataHelper.cpp:1340`), so `dxc -T cs_6_0` disassembly should
   carry it. Weaker: it is one layer below the reported interface.
3. A host program driving `ID3D12ShaderReflection`. Last resort.

If none of these can show the flag, the honest verdict is `not-compiler-verifiable`, not a
forced `does-not-repro`. **Compiling the shader cleanly proves nothing about this issue** —
the shader compiles fine in the report too.

## Instrument hazards to control for (predicate reads the tool as well as the compiler)

- `dxa -dumpreflection`'s **output format is not part of the compiler's contract**. A release
  whose dumper words the flag differently, or which cannot read a newer/older container, would
  score as "fixed". Any release sweep therefore needs a **fixed reader** (ground-truth `dxa`)
  varying only the compiler that produced the container, plus a per-release positive clause
  that proves the reader saw the buffer at all.
- `bAllUsed` short-circuits: `DxilContainerReflection.cpp:1473` sets
  `bool bAllUsed = ST->getNumContainedTypes() < 2;` — a `$Globals` with a single member marks
  everything used unconditionally. Any control shader must declare **at least two** globals.
- `DxilContainerReflection.cpp:1474` also sets `bAllUsed |= !bUsageInMetadata`, and
  `m_bUsageInMetadata` is true only for validator version >= 1.5 (line 2313-2314). Below that,
  reflection recomputes usage itself in `SetCBufferUsage()` (line 2330) — a **different code
  path from the one the issue blames**. Old releases may therefore answer via the other path;
  that has to be noticed rather than folded into a single history.

## Predicted controls

- **positive / presence control**: `WorldPosToProbeCoord` is genuinely used, so it must show
  `D3D_SVF_USED` in the same dump. If it does not, the instrument is broken.
- **negative control**: the same shader with the `- 1` removed from the index expression
  (i.e. `WorldPosToProbeCoordIndex(ProbePos + 0.5f, ProbeIndex)`). If the reporter's analysis
  is right, `SkyLightColor` should then be *unused* while the rest of the shader is unchanged.
  This is the one-variable A/B that distinguishes "the negative offset does it" from
  "`$Globals` usage tracking is broken generally".

## Repro quality

`complete` — the issue body carries the entire shader. The reporter did not state a command
line; `[numthreads(64,1,1)] void ResampleCS(...)` fixes the stage and entry point, so
`-T cs_6_0 -E ResampleCS` is the only inferred part. Recorded so a reader can see what was
assumed.

## What would make this inconclusive

- `dxa -dumpreflection` failing on the container, or not printing per-variable `uFlags`.
- The `$Globals` layout differing from the report such that `SkyLightColor` is no longer the
  last field (the mechanism is specifically "the *last* field gets marked").
