// Negative control for #3377's `internal_failure` predicate.
//
// Byte-for-byte the repro, with ONE change: the `: TEXUNIT0` semantic is removed from the
// `decal` parameter. Everything else -- the effect-syntax SamplerState, the unused
// main_vertex with its `uniform float4x4`, the `uniform` on `decal` itself -- is unchanged.
//
// Expect: no-match. If the predicate fires here too it is not discriminating, and the
// verdict would be resting on a predicate that matches everything.

SamplerState PointSampler { Filter = MIN_MAG_MIP_POINT; AddressU = Clamp; AddressV = Clamp; };

void main_vertex
(
	float4 position	: POSITION,
	float4 color	: COLOR,
	float2 texCoord : TEXCOORD0,

	uniform float4x4 modelViewProj,

	out float4 oPosition : POSITION,
	out float4 oColor    : COLOR,
	out float2 otexCoord : TEXCOORD
)
{
	oPosition = mul(modelViewProj, position);
	oColor = color;
	otexCoord = texCoord;
}

float4 main_fragment(float2 texCoord : TEXCOORD0, uniform Texture2D<float4> decal) : SV_Target
{
	return decal.Sample(PointSampler, texCoord);
}
