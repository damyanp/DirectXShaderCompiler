// issue 4036 control: the same cast-without-a-local shape that an in-tree
// test already contains.
//
// tools/clang/test/HLSLFileCheckLit/hlsl/auto/auto-no-descriptor-heap.hlsl
// line 24 writes
//     tex2.Sample((SamplerState)SamplerDescriptorHeap[0], pos.xy)
// as its "negative case".  That file is a -verify test whose other lines
// expect errors, so compilation stops after Sema and the line never reaches
// code generation.  This file is that line on its own, so it does.
//
// Expected: unknown at the time of writing -- this is a question, not an
// assertion.  Declared no-match; if it matches, the declaration is wrong
// and triage.py will say so.

struct PSInput
{
	float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
	Texture2D<float4> tex = ResourceDescriptorHeap[0];
	return tex.Sample((SamplerState)SamplerDescriptorHeap[0], input.color.xy);
}
