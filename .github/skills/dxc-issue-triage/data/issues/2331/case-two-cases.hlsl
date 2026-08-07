// Body claim B1: "Commenting out any one of the three switch cases results in a valid DXIL
// code (but it shouldn't, because there is no default case)."  Identical to repro.hlsl with
// the High case commented out; line count preserved so diagnostics line up.
enum class QualityT { Low, Medium, High, };

struct MyStruct
{
     float4 m_color;
     uint4  m_shaderVariantKey[1];
};
ConstantBuffer<MyStruct> MyCB : register(b0);

::QualityT __GetQuality()
{
    uint shaderKey = (MyCB.m_shaderVariantKey[0].w >> 0) & 3;
    return (::QualityT) shaderKey;
}

float4 MainPS() :SV_Target0
{
    static const int IntOption = 4;
switch ( __GetQuality() )
{
    case QualityT::Low:    return MyCB.m_color * float4 (IntOption, 0, 0, 0) ;
    case QualityT::Medium: return MyCB.m_color * float4 (0, IntOption, 0, 0) ;
//  case QualityT::High:   return MyCB.m_color * float4 (0, 0, IntOption, 0) ;
} 
}
