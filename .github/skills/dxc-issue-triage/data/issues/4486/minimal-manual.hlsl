// #4486, minimal restatement of the WORKAROUND: only the inner [unroll] loop,
// with the outer level written out by hand. Pairs with minimal-nested.hlsl and
// differs from it in exactly the loop nesting.
//
// Agent-constructed. Expectation: no-match.

float4 g_in;

void oneStep( int j, inout float v[4] )
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

float4 PS_bright_pass( float4 pos : SV_POSITION ) : SV_Target0
{
	float v[4] = { g_in.x, g_in.y, g_in.z, g_in.w };

	oneStep( 0, v );
	oneStep( 1, v );
	oneStep( 2, v );

	return float4( v[0], v[1], v[2], v[3] );
}
