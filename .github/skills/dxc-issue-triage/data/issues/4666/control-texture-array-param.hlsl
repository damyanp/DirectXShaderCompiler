// Issue 4666 -- isolating control.
//
// repro.hlsl with the SamplerState parameter removed. If the texture array
// parameter alone compiles while the sampler array parameter does not, the
// defect is specific to SamplerState rather than to resource-array parameters
// in general.
//
// Expected: no-match (compiles clean).
void Reflection(Texture2D<float4> Textures[4]) {}

float4 main() : SV_Target
{
    return 0;
}
