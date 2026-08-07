float4 ps_main(float3 p : POS) : SV_Target0
{
#if 0
	// Works
	float3 t = frac( p ) < 0.5 ? 150.0 : 100.0;
	float3 r = dot(t, 1).xxx;
#endif

#if 1
	// Validation error
	float3 r = dot(frac( p ) < 0.5 ? 150.0 : 100.0, 1).xxx;
#endif


	return float4(r, 1.0f);
}
