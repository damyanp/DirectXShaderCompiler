// Agent-constructed from #3038 body + @tex3d's comment identifying the trigger.
// Reported symptom: compiler crash when TraceRay and TraceRayInline share a RayDesc.
RaytracingAccelerationStructure scene : register(t0);
RWStructuredBuffer<float4> results : register(u0);

struct Payload { float4 color; };

[shader("raygeneration")]
void main() {
  RayDesc ray;
  ray.Origin = float3(0, 0, 0);
  ray.Direction = float3(0, 0, 1);
  ray.TMin = 0.0f;
  ray.TMax = 1000.0f;

  Payload p;
  p.color = float4(0, 0, 0, 0);
  TraceRay(scene, RAY_FLAG_NONE, 0xFF, 0, 1, 0, ray, p);

  // Same 'ray' instance reused here -- this is the reported trigger.
  RayQuery<RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH> q;
  q.TraceRayInline(scene, RAY_FLAG_NONE, 0xFF, ray);
  q.Proceed();

  results[0] = p.color;
}
