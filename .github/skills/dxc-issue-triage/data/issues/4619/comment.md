> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4619](https://github.com/microsoft/DirectXShaderCompiler/issues/4619).

The issue has two asks with different answers. Its body and title are now
stale because the thread-group-size half was fixed, while the topology half
remains open.

## Thread group size

`ID3D12ShaderReflection::GetThreadGroupSize` returned `0,0,0` for mesh
shaders through v1.7.2207. The measured transition is:

| release | `[numthreads(32,2,1)]` result |
| --- | --- |
| v1.5.2010 … v1.7.2207 | `0,0,0` |
| v1.7.2212 and later | `32,2,1` |

The release boundary and source change identify PR #4745
(`80fb4622a`, merged 2022-10-27) as the fix. It changed the reflection guard
from compute-only to compute, mesh and amplification shaders, but did not
reference this issue. The issue still has no comments recording that result.

## Output primitive topology

This remains unavailable through `ID3D12ShaderReflection`. On every
mesh-capable release and on `main`, the topology-shaped
`D3D12_SHADER_DESC` fields are zero. The container does carry the data:
`PSVRuntimeInfo1::MS1.MeshOutputTopology` is `2` (`Triangle`), and the DXIL
mesh-state metadata includes the same value.

[Compiler Explorer](https://godbolt.org/z/oT63zTbMf) shows the mesh-state
metadata for `[outputtopology("triangle")]` and `[numthreads(32,2,1)]`:

```llvm
!61 = !{i32 9, !62}
!62 = !{!63, i32 3, i32 1, i32 2, i32 0}
!63 = !{i32 32, i32 2, i32 1}
```

`dxa -dumpreflection` cannot verify either ask: it never calls
`GetThreadGroupSize` and prints `GSOutputTopology` only for geometry shaders.

Retitling this issue to the topology request and noting #4745 would describe
the remaining work. Exposing topology needs reflection API surface, so the
existing `enhancement` and `reflection` labels remain appropriate.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
