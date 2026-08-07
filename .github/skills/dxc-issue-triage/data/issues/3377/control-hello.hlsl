// Feature-presence control for #3377.
//
// The smallest ps_6_0 shader that uses everything the repro needs from the language --
// Texture2D<float4>, SamplerState, .Sample(), a TEXCOORD input and SV_Target -- and nothing
// else. Entry point name matches the repro so cmd.txt's arguments are reused unchanged.
//
// Two jobs:
//   1. negative control: the `internal_failure` predicate must not fire on a known-good input;
//   2. feature presence: if an old release rejects the REPRO, this says whether the release
//      lacks something the repro needs (it would reject this too) or whether the rejection is
//      specific to the repro. Without it, an `invalid-probe` on the repro is ambiguous.
//
// Expect: no-match.

SamplerState PointSampler;
Texture2D<float4> decal;

float4 main_fragment(float2 texCoord : TEXCOORD0) : SV_Target
{
	return decal.Sample(PointSampler, texCoord);
}
