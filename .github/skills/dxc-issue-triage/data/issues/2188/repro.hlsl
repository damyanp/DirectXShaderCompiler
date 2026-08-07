// microsoft/DirectXShaderCompiler#2188
// Reporter's shader, verbatim declarations; the elided `void csMain() ....` body is
// completed here so the file compiles. The completion is shared byte-for-byte with
// control-inlined.hlsl, so the only difference between the two is the thing under test.

RWBuffer<float4> Out : register(u0);

static const uint2	c2Thread = uint2(8, 8);
static const uint       cThread = c2Thread.x*c2Thread.y;
groupshared float4      S1[cThread];

[numthreads(c2Thread.x, c2Thread.y, 1)]
void csMain(uint i : SV_GroupIndex)
{
    S1[i] = i;
    GroupMemoryBarrierWithGroupSync();
    Out[i] = S1[i];
}
