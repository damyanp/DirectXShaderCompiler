// The reporter's main file, verbatim from the issue body (their name: cs_pragma.hlsl).
// Run at the reported -T cs_6_6 to confirm the minimisation in repro.hlsl is faithful.
#include "includeA.hlsli"
#include "includeB.hlsli"

RWTexture2D<float4> myOutput: register(u0);
Texture2D<float4> myTexInput: register(t0);
ConstantBuffer<Foo> Bar: register(b0);

[RootSignature("RootFlags(0), DescriptorTable(UAV(u0), CBV(b0), SRV(t0))")]
[numthreads(8, 8, 1)]
void main(uint3 thread_id : SV_DispatchThreadID)
{
    float4 outValue = myTexInput.Load(int3(thread_id.xy, 0));
    myOutput[thread_id.xy] = outValue * Bar.m_scale;
}
