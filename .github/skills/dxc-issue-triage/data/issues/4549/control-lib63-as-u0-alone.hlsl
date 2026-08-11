// lib_6_3 twin of control-as-u0-alone.hlsl, so the "the 'u' is discarded"
// observation can be made on v1.4.1907 too. RayQuery is Shader Model 6.5, so the
// pixel-shader version of this measurement cannot run on the oldest release; a
// DXR 1.0 library can.

RaytracingAccelerationStructure opaque_as : register(u0);

struct Payload {
  float4 color;
};

[shader("raygeneration")] void RayGen() {
  RayDesc ray;
  ray.Origin = float3(0, 0, 0);
  ray.Direction = float3(0, 0, 1);
  ray.TMin = 0;
  ray.TMax = 1000;

  Payload p;
  p.color = float4(0, 0, 0, 0);
  TraceRay(opaque_as, RAY_FLAG_NONE, 0xff, 0, 1, 0, ray, p);
}
