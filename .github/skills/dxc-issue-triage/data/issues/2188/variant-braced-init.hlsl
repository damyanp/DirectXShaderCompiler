// microsoft/DirectXShaderCompiler#2188 -- isolation variant E
// Is the blocker the vector *constructor call* `uint2(8, 8)`, or the *component read*
// `.x`? Here the vector is brace-initialised, so no constructor call is involved; only
// the component read remains. Array bound only; [numthreads] is inlined.

RWBuffer<float4> Out : register(u0);

static const uint2      c2Thread = { 8, 8 };
groupshared float4      S1[c2Thread.x * c2Thread.y];

[numthreads(8, 8, 1)]
void csMain(uint i : SV_GroupIndex)
{
    S1[i] = i;
    GroupMemoryBarrierWithGroupSync();
    Out[i] = S1[i];
}
