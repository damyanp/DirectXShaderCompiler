// Issue 4666 -- control for the SPIR-V arm: the same file without [noinline].
//
// Byte-identical to repro-spirv-struct.hlsl except that the attribute is gone.
// DXC's SPIR-V path inlines the helper, the struct type is never materialised,
// and the shader compiles. This is what shows the reported SPIR-V failure needs
// a struct type that survives to codegen -- and it is why the first, plainer
// reconstruction of this symptom was silently unfaithful.
//
// Expected: no-match (compiles clean).
struct Test
{
    SamplerState Samplers[2];
};

Texture2D<float4> g_Tex;
SamplerState g_S[2];

float4 Reflection(Test Res, float2 uv)
{
    return g_Tex.SampleLevel(Res.Samplers[0], uv, 0);
}

float4 main(float2 uv : TEXCOORD) : SV_Target
{
    Test t;
    t.Samplers[0] = g_S[0];
    t.Samplers[1] = g_S[1];
    return Reflection(t, uv);
}
