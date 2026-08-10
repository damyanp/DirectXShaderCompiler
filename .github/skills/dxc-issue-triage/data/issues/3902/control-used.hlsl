// Control for #3902: the SAME RayQuery declaration as repro.hlsl, with the same four
// template flags, but the object is actually traced with and its result is stored, so
// nothing can dead-code-eliminate it. Expect: compiles cleanly (no-match).
//
// This is the reporter's own control, from @DethRaid's 2023-09-01 comment: "if you
// un-comment the commented code the shader compiles without issue".
//
// It doubles as the per-release feature-presence control: a release that cannot express
// RayQuery / DXR 1.1 rejects this too, which is what distinguishes "that release predates
// the feature" from "that release rejected the repro for some unrelated reason".
//
// Uses a register-bound acceleration structure rather than ResourceDescriptorHeap so that
// it stays inside SM 6.5.

RaytracingAccelerationStructure rtas : register(t0);
RWBuffer<float> outBuf : register(u0);

[numthreads(8, 8, 1)]
void computeRTAO(
	uint3 groupId : SV_GroupID,
	uint3 groupThreadId : SV_GroupThreadID,
	uint3 dispatchThreadId : SV_DispatchThreadID,
	uint groupIndex : SV_GroupIndex )
{
  RayQuery<RAY_FLAG_CULL_NON_OPAQUE |
             RAY_FLAG_SKIP_PROCEDURAL_PRIMITIVES |
             RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH |
			 RAY_FLAG_CULL_BACK_FACING_TRIANGLES> rq;

  RayDesc ray;
  ray.Origin = float3(0, 0, 0);
  ray.Direction = float3(0, 1, 0);
  ray.TMin = 0.01;
  ray.TMax = 1000000;

  rq.TraceRayInline(rtas, 0, 0xFF, ray);
  rq.Proceed();

  outBuf[dispatchThreadId.x] = rq.CommittedStatus() == COMMITTED_TRIANGLE_HIT ? 1.0 : 0.0;
}
