// SPIR-V-backend-presence control for #3927.
//
// The smallest pixel shader that can be compiled with -spirv at all. Run with the repro's
// exact flags against the releases that reject the repro: if this fails there too, the
// rejection is "this build has no SPIR-V code generator", not anything about the repro, and
// those probes are invalid evidence rather than clean results.
float4 main() : SV_Target0
{
	return 1.0f;
}
