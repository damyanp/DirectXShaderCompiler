// Negative control for match.json: an unrelated, non-templated shader that
// exercises no partial template specialization at all. Confirms the
// predicate ("found unregistered decl") does not fire on ordinary valid
// HLSL 2021 SPIR-V code, i.e. it discriminates rather than matching
// everything.
struct PSInput
{
	float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
	bool test = true;
	return test ? input.color : float4(0, 0, 0, 0);
}
