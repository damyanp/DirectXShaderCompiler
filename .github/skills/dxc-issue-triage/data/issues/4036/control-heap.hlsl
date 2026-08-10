// Feature-presence control: the smallest shader that uses
// ResourceDescriptorHeap at all, under the repro's profile and flags.
//
// Its job is to disambiguate an invalid-probe on the repro. "This release
// rejected the input" can mean the release predates Shader Model 6.6, or that
// something unrelated in the repro was rejected -- and only the first justifies
// trimming the release out of the history. Rejected here too => the feature is
// absent from that build. Clean here while the repro is rejected => the
// rejection is about the repro, and trimming the release would hide a result.
//
// Expect: compiles clean, predicate does not match.
float4 PSMain() : SV_TARGET
{
	StructuredBuffer<float> buf = ResourceDescriptorHeap[0];
	return buf.Load(0);
}
