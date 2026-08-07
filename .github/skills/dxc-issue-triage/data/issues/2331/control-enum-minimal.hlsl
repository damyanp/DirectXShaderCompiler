// Feature-presence control for the bisection: the smallest shader that uses `enum class`,
// a scope-qualified enum type name and ConstantBuffer<T> at all, under the repro's exact
// profile and flags.  If an old release rejects repro.hlsl, this says whether the release
// predates the feature (both invalid-probe) or whether the rejection is about the repro
// (this one clean).  It must also not match the predicate.
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
    if (__GetQuality() == QualityT::Low)
        return MyCB.m_color;
    return 0;
}
