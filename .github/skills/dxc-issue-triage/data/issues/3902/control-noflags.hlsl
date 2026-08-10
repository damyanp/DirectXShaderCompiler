// Control for #3902: byte-for-byte the shape of repro.hlsl -- an UNUSED RayQuery object in
// the same entry point at the same profile -- except that the template argument declares no
// ray flags. Declared flags are then 0 and the validator's recomputed set is also 0, so the
// two agree and the shader must compile. Expect: no-match.
//
// This is what isolates the defect. If this control also failed, the bug would be "an unused
// RayQuery cannot be declared"; because it passes, the bug is specifically "template flags
// are declared into the module and survive the dead-code elimination of the code that
// justified them".

[numthreads(8, 8, 1)]
void computeRTAO(
	uint3 groupId : SV_GroupID,
	uint3 groupThreadId : SV_GroupThreadID,
	uint3 dispatchThreadId : SV_DispatchThreadID,
	uint groupIndex : SV_GroupIndex )
{
  RayQuery<RAY_FLAG_NONE> rq;
}
