// #4486 positive control for the OpLoopMerge detector.
//
// A loop whose trip count is a uniform cannot be unrolled by anyone, so the
// emitted SPIR-V must keep a structured loop. If this scores no-match, the
// detector is dead and every "no-match" elsewhere is worthless.
//
// Expectation: match.

struct VertexOut
{
	float4 pos : SV_POSITION;
	float2 tc : TEXCOORD;
};

Texture2D<float4> g_srcMap;
SamplerState g_RTLinearSampler;
float4 g_srcSize;

float4 PS_bright_pass( const VertexOut i ) : SV_Target0
{
	float3 acc = float3( 0.0f, 0.0f, 0.0f );
	for ( int n = 0; n < (int)g_srcSize.x; n++ )
	{
		acc += g_srcMap.SampleLevel( g_RTLinearSampler, i.tc, 0 ).rgb;
	}
	return float4( acc, 0.0f );
}
