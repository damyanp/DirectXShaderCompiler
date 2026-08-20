// #5849 -- "Missing DXR PAQ indication in RDAT to determine whether
// MaxPayloadSizeInBytes needs validation"
//
// Agent-constructed: the issue has no attached shader. It is a design
// proposal, not a crash report -- it argues that when Payload Access
// Qualifiers (PAQs) are used on SM 6.7+ (the default there, unless
// `-disable-payload-qualifiers` is passed), the compiler should record
// *something* in RDAT that lets the D3D12 runtime skip its
// MaxPayloadSizeInBytes check, because PAQs make that legacy field
// unnecessary. The reporter's own preferred fix (which amarpMSFT agreed
// to) is: report PayloadSizeInBytes as 0 in RDAT for any entry point that
// used PAQs.
//
// This library gives its payload a size (20 bytes: float4 + uint) that is
// distinct from every other number the compile could produce, and fully
// qualifies every field so PAQs actually engage (no
// "payload access qualifiers ignored" warning) on any real SM 6.7+ build.
// Every stage that touches the payload is covered: closesthit writes it,
// miss writes and the raygen shader reads it back after TraceRay.

struct [raypayload] Payload {
  float4 color : write(caller, closesthit, miss) : read(caller, miss);
  uint hitKind : write(caller, closesthit) : read(caller);
};

RaytracingAccelerationStructure Scene : register(t0);
RWStructuredBuffer<float4> Output : register(u0);

[shader("closesthit")]
void MyClosestHit(inout Payload p, in BuiltInTriangleIntersectionAttributes attr) {
  p.color = float4(attr.barycentrics, 0, 1);
  p.hitKind = HitKind();
}

[shader("miss")]
void MyMiss(inout Payload p) {
  p.color = float4(0, 0, 0, 0);
}

[shader("raygeneration")]
void MyRayGen() {
  Payload p = (Payload)0;
  RayDesc ray;
  ray.Origin = float3(0, 0, 0);
  ray.Direction = float3(0, 0, 1);
  ray.TMin = 0.001;
  ray.TMax = 10000.0;
  TraceRay(Scene, RAY_FLAG_NONE, 0xFF, 0, 1, 0, ray, p);
  Output[0] = float4(p.color.rgb, (float)p.hitKind);
}
