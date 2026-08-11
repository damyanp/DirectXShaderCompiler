// Issue 4666 -- NEGATIVE control for the predicate.
//
// A shader with no sampler array anywhere: a single sampler passed by value to
// a function. The predicate for this issue must not fire on it. A predicate
// that matches this too would be matching "an error happened" rather than the
// reported diagnostic.
//
// Expected: no-match (compiles clean).
Texture2D<float4> g_Texture;
SamplerState g_Sampler;

float4 Reflection(Texture2D<float4> Tex, SamplerState Samp, float2 uv)
{
    return Tex.SampleLevel(Samp, uv, 0);
}

float4 main(float2 uv : TEXCOORD) : SV_Target
{
    return Reflection(g_Texture, g_Sampler, uv);
}
