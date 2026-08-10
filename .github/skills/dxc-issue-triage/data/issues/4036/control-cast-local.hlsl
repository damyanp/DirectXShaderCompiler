// issue 4036 control: the cast, but not the method call on the cast.
//
// repro.hlsl calls .Load() directly on the parenthesised cast expression.
// This file keeps the cast and moves the call onto a named local, to find
// out whether the compiler objects to the cast itself or only to calling a
// method on the cast's result.
//
// Expected: no-match under match-fails.json (compiles clean).

struct PSInput
{
	float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
	StructuredBuffer<float> buf = (StructuredBuffer<float>)ResourceDescriptorHeap[int(input.color.x)];
	return buf.Load(0);
}
