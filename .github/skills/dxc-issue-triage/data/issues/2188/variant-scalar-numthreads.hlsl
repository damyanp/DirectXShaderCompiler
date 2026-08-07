// microsoft/DirectXShaderCompiler#2188 -- isolation variant D
// The scalar counterpart of the [numthreads] half, which is also the repro of the
// cross-referenced issue #2191 ("Assert when a static const uint is used with
// [numthreads]"), wrapped in this issue's shader so it differs from repro.hlsl in
// exactly one way. Captured here to characterise #2188's own failure, not to triage
// #2191.

RWBuffer<float4> Out : register(u0);

static const uint       eight = 8;
groupshared float4      S1[64];

[numthreads(eight, 8, 1)]
void csMain(uint i : SV_GroupIndex)
{
    S1[i] = i;
    GroupMemoryBarrierWithGroupSync();
    Out[i] = S1[i];
}
