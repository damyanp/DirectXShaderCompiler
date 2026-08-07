// Compute analogue of control-default-case.hlsl: case-compute.hlsl with the `default:` arm
// added.  Used to decide whether clang's backend failure on case-compute.hlsl is caused by
// the fall-off-the-end path (this one clean => yes) or by something else in the shader
// (this one fails the same way => the clang pane measures something unrelated).
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
    default:               return MyCB.m_color * float4 (0, 0, 0, IntOption) ;
} 
}

[numthreads(1, 1, 1)]
void MainCS(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x] = Shade();
}
