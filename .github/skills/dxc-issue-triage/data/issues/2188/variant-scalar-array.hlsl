// microsoft/DirectXShaderCompiler#2188 -- isolation variant C
// Is the *vector component read* the trigger, or is any `static const` rejected as a
// compile-time constant? Here the const is a plain scalar with a literal initialiser and
// is used only as the array bound; [numthreads] is inlined.

RWBuffer<float4> Out : register(u0);

static const uint       cThread = 64;
groupshared float4      S1[cThread];

[numthreads(8, 8, 1)]
void csMain(uint i : SV_GroupIndex)
{
    S1[i] = i;
    GroupMemoryBarrierWithGroupSync();
    Out[i] = S1[i];
}
