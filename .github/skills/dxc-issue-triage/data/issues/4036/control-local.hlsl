// Control: the workaround pow2clk names in the issue thread -- assign the
// descriptor-heap subscript to a local variable, then call the method on it.
// Same feature, same profile, same flags as repro.hlsl; the ONLY difference is
// that the method call is not made on the result of a cast expression.
// Expect: compiles clean, predicate does not match.
struct PSInput
{
	float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
	StructuredBuffer<float> buf = ResourceDescriptorHeap[int(input.color.x)];
	return buf.Load(0);
}
