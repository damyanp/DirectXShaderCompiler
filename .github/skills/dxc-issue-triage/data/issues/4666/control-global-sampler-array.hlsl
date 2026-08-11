// Issue 4666 -- feature-presence control.
//
// A global sampler array, indexed dynamically, with no function parameter
// involved. Proves the release understands `SamplerState[N]` as a type at all.
// If this fails on a release, that release cannot speak to the issue.
//
// Expected: no-match (compiles clean).
Texture2D<float4> g_Textures[4];
SamplerState g_Samplers[2];

float4 main(float2 uv : TEXCOORD, uint i : I) : SV_Target
{
    return g_Textures[i].SampleLevel(g_Samplers[i], uv, 0);
}
