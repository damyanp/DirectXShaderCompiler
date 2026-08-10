// Compiler Explorer restating of #3902. Compiler Explorer is single-source, so the repro and
// the control that distinguishes it live in one file behind a preprocessor guard, and the
// panes differ only by -DUSE_RAYQUERY. Verified locally in both arms before publishing:
// see variant-ce-plain-main-debug.txt and variant-ce-used-main-debug.txt.
//
// Without the define the entry point is repro.hlsl's shape: a RayQuery object is declared and
// never used.
// With the define the same object is traced with and its result is stored.

RaytracingAccelerationStructure rtas : register(t0);
RWBuffer<float> outBuf : register(u0);

[numthreads(8, 8, 1)]
void computeRTAO(uint3 dispatchThreadId : SV_DispatchThreadID)
{
  RayQuery<RAY_FLAG_CULL_NON_OPAQUE |
           RAY_FLAG_SKIP_PROCEDURAL_PRIMITIVES |
           RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH |
           RAY_FLAG_CULL_BACK_FACING_TRIANGLES> rq;

#ifdef USE_RAYQUERY
  RayDesc ray;
  ray.Origin = float3(0, 0, 0);
  ray.Direction = float3(0, 1, 0);
  ray.TMin = 0.01;
  ray.TMax = 1000000;

  rq.TraceRayInline(rtas, 0, 0xFF, ray);
  rq.Proceed();

  outBuf[dispatchThreadId.x] = rq.CommittedStatus() == COMMITTED_TRIANGLE_HIT ? 1.0 : 0.0;
#endif
}
