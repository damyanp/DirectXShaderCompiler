// #4486 discriminator: nested [unroll] loops where BOTH bounds are constants
// and the inner bound does NOT depend on the outer induction variable.
//
// repro.hlsl has both properties at once -- nesting, and an inner bound of
// (4 - j - 1) that is only knowable once j is. This shader removes the second
// so the two can be told apart, which is the difference between saying
// "nesting defeats the unroller" and "a dependent inner bound defeats it".
//
// Expectation, declared before running: match -- 1 surviving OpLoopMerge if the
// inner loop unrolled and the outer did not, 2 if neither did.
//
// MEASURED: no-match. ZERO OpLoopMerge, nine OpFOrdGreaterThan (3x3) and zero
// OpBranchConditional -- the nest unrolled completely and every comparison
// if-converted to a select. The declared expectation was a wrong prediction and
// is corrected to no-match; the correction is the finding, not a tidy-up.
//
// What it establishes: nesting alone does NOT defeat the SPIR-V unroller. What
// defeats repro.hlsl is the inner trip count (4 - j - 1) depending on the outer
// induction variable, so the inner loop's iteration count cannot be evaluated,
// so it is never removed, so the outer never becomes an inner-most loop either
// (external/SPIRV-Tools/source/opt/loop_unroller.cpp:1113, "Can only unroll
// inner loops"). repro.hlsl keeps exactly 1 OpFOrdGreaterThan inside its 2
// surviving loops; this shader keeps 9 and no loops.

float4 g_in;

float4 PS_bright_pass( float4 pos : SV_POSITION ) : SV_Target0
{
	float v[4] = { g_in.x, g_in.y, g_in.z, g_in.w };

	[unroll]
	for ( int j = 0; j < 3; j++ )
	{
		[unroll]
		for ( int k = 0; k < 3; k++ )
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
