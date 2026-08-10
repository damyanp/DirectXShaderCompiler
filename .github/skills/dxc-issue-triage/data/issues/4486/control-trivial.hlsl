// #4486 instrument self-test control.
//
// A shader with no loop at all. Under `-spirv` it must produce a SPIR-V module
// with an OpEntryPoint Fragment line and no OpLoopMerge, so:
//   - a release with no SPIR-V backend ("SPIR-V CodeGen not available") fails
//     the anchor and is exposed as unmeasurable rather than clean;
//   - a release whose disassembler stopped printing to stdout likewise fails
//     the anchor instead of masquerading as a fix.
//
// Expectation: no-match.

struct VertexOut
{
	float4 pos : SV_POSITION;
	float2 tc : TEXCOORD;
};

float4 PS_bright_pass( const VertexOut i ) : SV_Target0
{
	return float4( i.tc, 0.0f, 0.0f );
}
