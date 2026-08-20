// Compute-shader restatement of #4871's repro, for Compiler Explorer panes
// whose compilers cannot lower a pixel shader (e.g. hlsl_clang_trunk requires
// SV_Target to be a float type). The construct under test -- an empty inout
// function called with a pre-decremented argument -- is not stage-specific.
RWStructuredBuffer<uint> Out : register(u0);

void Func(inout uint byteOffset)
{
}

[numthreads(1, 1, 1)]
void CSMain(uint3 tid : SV_DispatchThreadID)
{
    uint i = tid.x;
    Func(--i);  // Subtracts 2...
    Out[0] = i;
}
