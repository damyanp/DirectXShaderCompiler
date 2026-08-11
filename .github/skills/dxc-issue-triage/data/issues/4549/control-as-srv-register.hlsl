// Control for #4549: the acceleration structure bound to an SRV register, which
// is what the reporter should have written. Same shape as repro.hlsl otherwise.
//
// Two jobs:
//  * negative control -- the predicate must NOT fire on a correctly-bound shader;
//  * feature-presence control -- if a release cannot express
//    RaytracingAccelerationStructure / RayQuery / ps_6_5, this fails too, and the
//    repro's rejection on that release is feature absence rather than a result.

RaytracingAccelerationStructure opaque_as : register(t1);

Texture2D<float> depth_buffer : register(t0);

float4 main(float4 pos : SV_Position) : SV_Target {
  RayDesc ray;
  ray.Origin = float3(pos.xy, 0);
  ray.Direction = float3(0, 0, 1);
  ray.TMin = 0;
  ray.TMax = 1000;

  RayQuery<RAY_FLAG_NONE> q;
  q.TraceRayInline(opaque_as, RAY_FLAG_NONE, 0xff, ray);
  q.Proceed();

  float d = depth_buffer.Load(int3((int2)pos.xy, 0));
  return float4(d, q.CommittedRayT(), 0, 1);
}
