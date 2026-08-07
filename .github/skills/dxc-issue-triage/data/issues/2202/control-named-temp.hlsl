float4 ps_main(float3 p : POS) : SV_Target0
{
	// The reporter's own "// Works" variant, verbatim from the same attachment
	// (test.txt, the #if 0 branch). Identical except that the ternary result is
	// bound to a named float3 before dot() sees it.
	float3 t = frac( p ) < 0.5 ? 150.0 : 100.0;
	float3 r = dot(t, 1).xxx;

	return float4(r, 1.0f);
}
