// #2952 identity control: the same question with a DIFFERENT payload size.
//
// repro.hlsl declares a 28-byte payload; this one declares 16. If the API
// answer depended on the particular size -- say, because the harness's field
// search were keyed to one number -- these two would disagree. They must not:
// the finding is that D3D12_FUNCTION_DESC has no payload field at all, so the
// answer is size-independent, and that sameness is what the control asserts
// (SKILL.md's #1803-style identity control).
//
// Expected: match.

struct SmallPayload {
  float4 color; // 16 bytes
};

RaytracingAccelerationStructure Scene : register(t0);
RWTexture2D<float4> Output : register(u0);

[shader("raygeneration")] void RayGenMain() {
  SmallPayload payload;
  payload.color = float4(0, 0, 0, 0);

  RayDesc ray;
  ray.Origin = float3(0, 0, 0);
  ray.Direction = float3(0, 0, 1);
  ray.TMin = 0.001;
  ray.TMax = 10000.0;

  TraceRay(Scene, RAY_FLAG_NONE, 0xFF, 0, 1, 0, ray, payload);
  Output[DispatchRaysIndex().xy] = payload.color;
}

[shader("miss")] void MissMain(inout SmallPayload payload) {
  payload.color = float4(0, 0, 1, 1);
}

[shader("closesthit")] void ClosestHitMain(
    inout SmallPayload payload, in BuiltInTriangleIntersectionAttributes attr) {
  payload.color = float4(attr.barycentrics, 0, 1);
}
