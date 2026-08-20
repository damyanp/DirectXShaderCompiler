// Trivial pixel shader: SPIR-V codegen must succeed cleanly for a shader that
// does not touch a multisampled UAV texture. Proves the internal_failure
// predicate is not simply "any SPIR-V compile crashes".
float4 PS() : SV_Target
{
    return float4(1, 0, 0, 1);
}
