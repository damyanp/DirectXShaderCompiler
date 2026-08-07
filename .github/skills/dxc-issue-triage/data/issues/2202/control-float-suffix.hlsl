float4 ps_main(float3 p : POS) : SV_Target0
{
	// The workaround tristanlabelle proposed in the issue thread: suffix the two
	// ternary results with `f` so they are float literals, not literal-floats that
	// resolve to double.
	float3 r = dot(frac( p ) < 0.5 ? 150.0f : 100.0f, 1).xxx;

	return float4(r, 1.0f);
}
