// Issue 4666 -- SPIR-V feature-presence control.
//
// The plainest possible sampler + texture shader, compiled with -spirv. It
// proves that the build under test has SPIR-V codegen at all and can lower a
// sampler, so a -spirv failure on repro-spirv-struct.hlsl is about the struct
// and not about the backend being absent. v1.4.1907 and v1.5.2003 answer
// "SPIR-V CodeGen not available" here.
//
// Expected: no-match (compiles clean).
Texture2D<float4> g_Texture;
SamplerState g_Sampler;

float4 main(float2 uv : TEXCOORD) : SV_Target
{
    return g_Texture.SampleLevel(g_Sampler, uv, 0);
}
