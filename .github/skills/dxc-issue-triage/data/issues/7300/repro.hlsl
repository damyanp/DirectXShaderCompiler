#pragma pack_matrix(row_major)

RaytracingAccelerationStructure SceneBVH : register(t0);
RWTexture2D<uint> u_Output : register(u0);

[numthreads(8, 8, 1)]
void main(uint2 pixel : SV_DispatchThreadID)
{
    RayDesc ray;
    ray.Origin = float3(pixel.x, pixel.y, 0);
    ray.TMin = 0;
    ray.TMax = 1000;
    ray.Direction = float3(0, 1, 0);

    uint instanceMask = 0xFF;
    uint rayFlags = 0;

    RayQuery<RAY_FLAG_CULL_NON_OPAQUE | RAY_FLAG_SKIP_PROCEDURAL_PRIMITIVES> rayQuery;

    rayQuery.TraceRayInline(SceneBVH, rayFlags, instanceMask, ray);
    rayQuery.Proceed();

    if (rayQuery.CommittedStatus() == COMMITTED_TRIANGLE_HIT)
        u_Output[pixel] = 1;
    else
        u_Output[pixel] = 0;
}
