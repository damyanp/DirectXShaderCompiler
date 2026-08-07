// microsoft/DirectXShaderCompiler#2188 -- NEGATIVE CONTROL
// The reporter's own "note": same shader with the numeric constants inlined, which they
// say "does work fine". The `static const` declarations are kept so that only their *use*
// as a compile-time constant differs from repro.hlsl. Body identical to repro.hlsl.

RWBuffer<float4> Out : register(u0);

static const uint2	c2Thread = uint2(8, 8);
static const uint       cThread = c2Thread.x*c2Thread.y;
groupshared float4      S1[64];

[numthreads(8, 8, 1)]
void csMain(uint i : SV_GroupIndex)
{
    S1[i] = i;
    GroupMemoryBarrierWithGroupSync();
    Out[i] = S1[i];
}
