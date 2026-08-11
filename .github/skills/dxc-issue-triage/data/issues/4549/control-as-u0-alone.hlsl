// Variant for #4549: the acceleration structure at register(u0), with nothing
// occupying t0. Tests the reporter's quoted speculation directly -- that DXC
// ignores the 'u' and binds the acceleration structure as an SRV.
//
// Purely behavioural: no diagnostic text is involved. If DXC compiles this and
// the resource-binding table shows t0, the 'u' was discarded.

RaytracingAccelerationStructure opaque_as : register(u0);

float4 main(float4 pos : SV_Position) : SV_Target {
  RayDesc ray;
  ray.Origin = float3(pos.xy, 0);
  ray.Direction = float3(0, 0, 1);
  ray.TMin = 0;
  ray.TMax = 1000;

  RayQuery<RAY_FLAG_NONE> q;
  q.TraceRayInline(opaque_as, RAY_FLAG_NONE, 0xff, ray);
  q.Proceed();

  return float4(q.CommittedRayT(), 0, 0, 1);
}
