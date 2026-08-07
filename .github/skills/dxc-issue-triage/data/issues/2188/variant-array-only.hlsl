// microsoft/DirectXShaderCompiler#2188 -- isolation variant A
// Only the groupshared array bound uses the static const; [numthreads] is inlined.
// Everything else is byte-identical to repro.hlsl.

RWBuffer<float4> Out : register(u0);

static const uint2	c2Thread = uint2(8, 8);
static const uint       cThread = c2Thread.x*c2Thread.y;
groupshared float4      S1[cThread];

[numthreads(8, 8, 1)]
void csMain(uint i : SV_GroupIndex)
{
    S1[i] = i;
    GroupMemoryBarrierWithGroupSync();
    Out[i] = S1[i];
}
