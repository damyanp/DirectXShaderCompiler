// #4486 control for the DXIL-side predicate: the same nested loops, but with
// the outer trip count taken from a uniform, so no compiler can unroll them.
//
// Purpose: match-dxil-unrolled.json claims "DXIL materialised all six bubble-
// sort comparisons, so both [unroll] levels were unrolled". That claim is only
// worth anything if the predicate can also say *no*. This shader is the one-
// variable change that should make it say no.
//
// Expectations:
//   -spirv, match.json               -> match    (loops remain, as everywhere)
//   DXIL,   match-dxil-unrolled.json -> no-match (a runtime bound cannot unroll)

float4 g_in;
int g_count;

float4 PS_bright_pass( float4 pos : SV_POSITION ) : SV_Target0
{
	float v[4] = { g_in.x, g_in.y, g_in.z, g_in.w };

	[unroll]
	for ( int j = 0; j < g_count; j++ )
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
