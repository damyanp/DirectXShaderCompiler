// #4619 control -- POSITIVE control for ask A.
//
// The same [numthreads(32, 2, 1)] as repro.hlsl, on a compute shader. This is
// the stage ID3D12ShaderReflection::GetThreadGroupSize has always supported,
// so it must report 32,2,1. It is what proves the accessor, the container walk
// and this harness all work; a 0,0,0 here would mean the instrument is broken
// and the mesh result says nothing (SKILL.md: "a control cannot catch a broken
// reader" -- so make the instrument prove a presence in the same population).
//
// Expected: no-match under match.json.

RWBuffer<uint> Out : register(u0);

[numthreads(32, 2, 1)]
void main(uint3 tid : SV_DispatchThreadID) { Out[tid.x] = tid.y; }
