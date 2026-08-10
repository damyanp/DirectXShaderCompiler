> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2952](https://github.com/microsoft/DirectXShaderCompiler/issues/2952).

Still open on `main` (13730886e), and the answer to the 2024 question in this
thread is "half of it already works, and the other half is closer than it
looks".

**The function type is already available.** `CFunctionReflection::GetDesc` sets
`D3D12_FUNCTION_DESC.Version` from `DxilFunctionProps::shaderKind`
([`DxilContainerReflection.cpp:2848`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilContainerReflection.cpp#L2848)),
so `D3D12_SHVER_GET_TYPE(Version)` returns the raytracing shader kind. On a
library with one entry of every DXR 1.0 kind it gives 7/8/9/10/11/12 for
raygeneration / intersection / anyhit / closesthit / miss / callable and 6 for a
plain export — correct for all seven functions, on every release from v1.4.1907
to v1.9.2607 in the 20-stable-release matrix. `dxa -dumpreflection` already
prints it as `Shader Version: AnyHit 6.3`.

The catch is that `d3d12shader.h` defines `D3D12_SHADER_VERSION_TYPE` only up to
5. Values 6–15 are `hlsl::DXIL::ShaderKind`, which ships in no public header —
DXC's own dumper casts to the internal enum to print them
([`D3DReflectionDumper.cpp:160`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/DxilContainer/D3DReflectionDumper.cpp#L160)).
Callers can get the right answer only by hardcoding constants they were never
given.

**The payload size is in the container, but no shipped DXC header exposes a
supported reader.**
`RuntimeDataFunctionInfo` carries `PayloadSizeInBytes` and
`AttributeSizeInBytes`
([`RDAT_LibraryTypes.inl:205`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/include/dxc/DxilContainer/RDAT_LibraryTypes.inl#L205)),
present since 0a098d7cb (2018-02) — before this issue was filed. It is in the DXIL
too, as `dx.entryPoints` entry-property tags 6 and 7. But `D3D12_FUNCTION_DESC`
has no field that could hold it: enumerating all 31 numeric fields and searching
them for the size the container reports finds nothing, on every stable release
tested.
And `DxilRuntimeReflection.h` / `RDAT_*.inl` are not in any release package —
`inc/` ships `d3d12shader.h`, `dxcapi.h`, and latterly `dxcerrors.h`,
`dxcisense.h`, `dxcpix.h`. An application can pull the raw bytes with
`IDxcContainerReflection::GetPartContent(DFCC_RuntimeData)` and then has no
supported way to parse them.

So this is an API-surface request, not a data-capture one — the data has been
recorded since 2018. The options are roughly: add fields to
`D3D12_FUNCTION_DESC` (declared in DirectX-Headers, so not DXC's alone to
change), add a DXC-specific reflection interface, or ship the RDAT reader. That
is a design call for the team.

Method: `dxc.exe` cannot express a reflection query, so this was measured with a
small harness driving `IDxcContainerReflection` → `ID3D12LibraryReflection` →
`ID3D12FunctionReflection` against each release's own `dxcompiler.dll`. A
control library with no raytracing entries scores no-match on every release, so
"the API reported nothing" is not being satisfied vacuously.

[Compiler Explorer](https://godbolt.org/z/YT1q1cqjb) shows the payload size and
shader kind sitting in `dx.entryPoints` on both `dxc_1_6_2112` and trunk; it
cannot show the reflection API.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
