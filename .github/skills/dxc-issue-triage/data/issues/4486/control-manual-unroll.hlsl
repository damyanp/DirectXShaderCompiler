// #4486 control: the reporter's WORKAROUND, which they report produces
// "perfectly flat" code with zero warp divergence.
//
// This is maintainer pow2clk's 2022-06-29 shader, unchanged: the outer
// [unroll] loop is replaced by three explicit boxMedianOneStep() calls, so
// every remaining loop is innermost with a compile-time-constant bound.
//
// Expectation: no-match. It shares the [unroll] for(i<4) sampling loop with
// repro.hlsl, so a no-match here also proves that any OpLoopMerge surviving in
// repro.hlsl comes from the nested pair and not from the sampling loop.

struct VertexOut
{
	float4 pos : SV_POSITION;
	float2 tc : TEXCOORD;
};

Texture2D<float4> g_srcMap;
SamplerState g_RTLinearSampler;
float4 g_srcSize;

float luminance(float3 RGB) {
      return RGB.g * 2.0 + RGB.r + RGB.b;
}

void boxMedianOneStep( int j, inout float3 colors[4], inout float luminances[4] )
{
	[unroll]
	for ( int k = 0; k < (4 - j - 1); k++ )
	{
		[flatten]
		if ( luminances[k] > luminances[k + 1] )
		{
			float tmpLum = luminances[k];
			luminances[k] = luminances[k + 1];
			luminances[k + 1] = tmpLum;

			float3 tmpColor = colors[k];
			colors[k] = colors[k + 1];
			colors[k + 1] = tmpColor;
		}
	}
}

float3 boxMedian( uniform Texture2D<float4> tex, uniform SamplerState sampleState, float2 invTextureSize, float2 tc )
{
	float2 offsets[4] =
	{
		float2(-1.0, -1.0),
		float2(1.0, -1.0),
		float2(1.0, 1.0),
		float2(-1.0, 1.0)
	};

	float3 colors[4];
	float luminances[4];

	[unroll]
	for ( int i = 0; i < 4; i++ )
	{
		const float2 currentTC = tc + offsets[i] * invTextureSize;
		colors[i] = float3( tex.SampleLevel( sampleState, currentTC, 0 ).rgb );
		luminances[i] = luminance( colors[i].rgb );
	}

	boxMedianOneStep( 0, colors, luminances );
	boxMedianOneStep( 1, colors, luminances );
	boxMedianOneStep( 2, colors, luminances );

	return float3( ( colors[1] + colors[2] ) * 0.5 );
}

float4 PS_bright_pass(const VertexOut i ) : SV_Target0
{
	float3 color = boxMedian(g_srcMap, g_RTLinearSampler, g_srcSize.zw, i.tc).rgb;
	return float4(color, 0.0f);
}
