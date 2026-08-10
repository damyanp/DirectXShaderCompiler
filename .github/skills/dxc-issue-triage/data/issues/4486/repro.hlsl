// #4486 repro: nested [unroll] `for` loops with compile-time-constant bounds.
//
// Source: the self-contained shader posted by maintainer pow2clk on 2022-06-29
// (the issue body's own snippet has no entry point and dead arrays, so the
// loops are optimised away). pow2clk's version calls boxMedianOneStep(0/1/2),
// which is the reporter's *workaround*; the nested-loop body below is the
// reporter's 2022-06-14 comment, item 2 -- "The original loop in boxMedian()
// looked like this". Restoring it is what makes this the shader the title
// describes. The only adaptation is `float4 tmpColor` -> `float3`, because the
// completed shader declares `float3 colors[4]`; and the unused `float max = 0;`
// is dropped.
//
// control-manual-unroll.hlsl holds pow2clk's version unchanged, so the two
// files differ in exactly the thing under test.

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

	[unroll]
	for ( int j = 0; j < (4 - 1); j++ )
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

	return float3( ( colors[1] + colors[2] ) * 0.5 );
}

float4 PS_bright_pass(const VertexOut i ) : SV_Target0
{
	float3 color = boxMedian(g_srcMap, g_RTLinearSampler, g_srcSize.zw, i.tc).rgb;
	return float4(color, 0.0f);
}
