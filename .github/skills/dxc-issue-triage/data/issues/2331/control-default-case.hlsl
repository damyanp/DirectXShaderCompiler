// Control for match.json: the issue's own stated fix (B3) -- identical to repro.hlsl
// except for the added `default:`. The predicate must NOT match this.
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
    case QualityT::High:   return MyCB.m_color * float4 (0, 0, IntOption, 0) ;
    default:               return MyCB.m_color * float4 (0, 0, 0, IntOption) ;
} 
}
