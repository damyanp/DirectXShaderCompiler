// Issue 4666 -- per-release feature-presence control for the SPIR-V arm.
//
// repro-spirv-struct.hlsl with the struct's sampler array replaced by ordinary
// float data, everything else -- including [noinline] -- unchanged. It proves,
// on the release under test, that:
//
//   * the [noinline] attribute is accepted and honoured, and
//   * a struct passed by value to a non-inlined function is materialised as an
//     OpTypeStruct and passes validation when its members are not opaque.
//
// A release that fails this control cannot express the construct at all, so its
// failure on repro-spirv-struct.hlsl says nothing about the reported defect.
//
// Expected: no-match (compiles clean).
struct Test
{
    float4 Values[2];
};

Texture2D<float4> g_Tex;
SamplerState g_S;

[noinline] float4 Reflection(Test Res, float2 uv)
{
    return g_Tex.SampleLevel(g_S, uv, 0) + Res.Values[0] + Res.Values[1];
}

float4 main(float2 uv : TEXCOORD) : SV_Target
{
    Test t;
    t.Values[0] = uv.xyxy;
    t.Values[1] = uv.yxyx;
    return Reflection(t, uv);
}
