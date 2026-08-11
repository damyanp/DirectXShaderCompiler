// Translation of #4549's repro to a DXR 1.0 library, purely to extend the
// release history: RayQuery / ps_6_5 is Shader Model 6.5, so the pixel-shader
// repro cannot be run on releases older than that, while lib_6_3 + TraceRay
// reaches the oldest release that ships a usable dxc (v1.4.1907).
//
// The two declarations and their registers are unchanged from repro.hlsl.
// The stage is not the reporter's; repro.hlsl remains the faithful case.

RaytracingAccelerationStructure opaque_as : register(u0);

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
