// Compute restating of repro.hlsl, for Compiler Explorer: clang's HLSL backend cannot lower
// a pixel shader writing SV_Target, so a pixel pane says nothing about this issue.  The
// construct under test -- a switch over an enum-typed value that covers every enumerator,
// has no default, and sits in a non-void function -- is not stage-specific.  Verified to
// still reproduce in DXC before being published (variant-compute-main-debug.txt).
enum class QualityT { Low, Medium, High, };

struct MyStruct
{
     float4 m_color;
     uint4  m_shaderVariantKey[1];
};
ConstantBuffer<MyStruct> MyCB : register(b0);
RWBuffer<float4> Out : register(u0);

::QualityT __GetQuality()
{
    uint shaderKey = (MyCB.m_shaderVariantKey[0].w >> 0) & 3;
    return (::QualityT) shaderKey;
}

float4 Shade()
{
    static const int IntOption = 4;
switch ( __GetQuality() )
{
    case QualityT::Low:    return MyCB.m_color * float4 (IntOption, 0, 0, 0) ;
    case QualityT::Medium: return MyCB.m_color * float4 (0, IntOption, 0, 0) ;
    case QualityT::High:   return MyCB.m_color * float4 (0, 0, IntOption, 0) ;
} 
}

[numthreads(1, 1, 1)]
void MainCS(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x] = Shade();
}
