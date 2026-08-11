// Feature-presence / negative control for the lib_6_3 arm of #4549: same DXR 1.0
// library as translation-lib63.hlsl but with the acceleration structure on an SRV
// register. A release that cannot express lib_6_3 / TraceRay /
// RaytracingAccelerationStructure fails this too, so a clean run on the
// translation would be feature absence rather than an absence of the symptom.

RaytracingAccelerationStructure opaque_as : register(t1);

Texture2D<float> depth_buffer : register(t0);

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
  p.color = float4(depth_buffer.Load(int3(0, 0, 0)), 0, 0, 0);
  TraceRay(opaque_as, RAY_FLAG_NONE, 0xff, 0, 1, 0, ray, p);
}
