// Repro for microsoft/DirectXShaderCompiler#4549.
//
// The two declarations are verbatim from the issue body. Everything below them
// is the minimum needed to make them live resources: DXC strips unreferenced
// globals before register allocation, and the reported diagnostic is emitted by
// the register allocator (lib/HLSL/DxilCondenseResources.cpp).
//
// RaytracingAccelerationStructure is an SRV-class resource, so register(u0) is
// wrong. The issue is about how DXC says so.

RaytracingAccelerationStructure opaque_as : register(u0);

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
