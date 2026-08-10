// #2952 -- "Expose ray payload size / function type through Reflection"
//
// Agent-constructed. The issue has no repro: it asks whether the payload size
// and the shader kind ("raygen, miss...") of a DXR library entry can be
// retrieved from a reflection container. So this library declares one function
// of every DXR 1.0 shader kind, plus a plain (non-entry) library function, and
// gives each size a value that cannot be confused with any other number in the
// reflection output:
//
//   RayPayload      float4 + float3            = 28 bytes
//   Attributes      BuiltInTriangleIntersectionAttributes (float2) = 8 bytes
//   CallableParams  float2 + uint              = 12 bytes
//
// 28, 8 and 12 are all distinct from the resource and constant-buffer counts
// this library produces, so "the API reported the payload size" cannot be
// satisfied by coincidence.
//
// lib_6_3 is the oldest library profile in the release sequence and is DXR
// 1.0, per SKILL.md's "target the repro at the oldest profile that still shows
// the symptom".

struct RayPayload {
  float4 color;
  float3 hitPoint;
};

struct CallableParams {
  float2 uv;
  uint id;
};

RaytracingAccelerationStructure Scene : register(t0);
RWTexture2D<float4> Output : register(u0);

[shader("raygeneration")] void RayGenMain() {
  RayPayload payload;
  payload.color = float4(0, 0, 0, 0);
  payload.hitPoint = float3(0, 0, 0);

  RayDesc ray;
  ray.Origin = float3(0, 0, 0);
  ray.Direction = float3(0, 0, 1);
  ray.TMin = 0.001;
  ray.TMax = 10000.0;

  TraceRay(Scene, RAY_FLAG_NONE, 0xFF, 0, 1, 0, ray, payload);
  Output[DispatchRaysIndex().xy] = payload.color;
}

[shader("miss")] void MissMain(inout RayPayload payload) {
  payload.color = float4(0, 0, 1, 1);
}

[shader("closesthit")] void ClosestHitMain(
    inout RayPayload payload, in BuiltInTriangleIntersectionAttributes attr) {
  payload.color = float4(attr.barycentrics, 0, 1);
  payload.hitPoint = WorldRayOrigin() + RayTCurrent() * WorldRayDirection();
}

[shader("anyhit")] void AnyHitMain(
    inout RayPayload payload, in BuiltInTriangleIntersectionAttributes attr) {
  if (attr.barycentrics.x < 0.01)
    IgnoreHit();
}

[shader("intersection")] void IntersectionMain() {
  BuiltInTriangleIntersectionAttributes attr;
  attr.barycentrics = float2(0.25, 0.25);
  ReportHit(1.0, 0, attr);
}

[shader("callable")] void CallableMain(inout CallableParams params) {
  params.uv = params.uv * 2.0;
  params.id = params.id + 1;
}

// A plain library function, not an entry point: its reflected shader kind
// should be Library, which is what distinguishes "the kind field is populated"
// from "the kind field happens to hold a constant".
export float3 PlainLibraryFunction(float3 v) { return v * 2.0f; }
