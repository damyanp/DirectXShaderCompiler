// #4486, minimal restatement: nested [unroll] `for` loops with compile-time
// constant bounds, no textures, no samplers, no helper functions.
//
// Agent-constructed, not from the thread. It exists so the finding can be read
// in a few lines of SPIR-V and shown on Compiler Explorer; repro.hlsl stays the
// faithful evidence. Same loop nest as repro.hlsl (j < 3, k < 4 - j - 1) over
// the same bubble-sort body.
//
// Expectation: match.

float4 g_in;

float4 PS_bright_pass( float4 pos : SV_POSITION ) : SV_Target0
{
	float v[4] = { g_in.x, g_in.y, g_in.z, g_in.w };

	[unroll]
	for ( int j = 0; j < (4 - 1); j++ )
	{
		[unroll]
		for ( int k = 0; k < (4 - j - 1); k++ )
		{
			[flatten]
			if ( v[k] > v[k + 1] )
			{
				float tmp = v[k];
				v[k] = v[k + 1];
				v[k + 1] = tmp;
			}
		}
	}

	return float4( v[0], v[1], v[2], v[3] );
}
