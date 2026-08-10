// Reporter's own workaround form: the issue body's shader with BUGGED switched off.
// Identical in every other respect, so the two differ in exactly one way.
#define RECURSION_DEPTH 30
#define BUGGED 0

struct Payload {
    uint4 data0;
};

RaytracingAccelerationStructure tlas : register(t0, space0);

[shader("closesthit")] void
main(inout Payload payload, in BuiltInTriangleIntersectionAttributes attribs) {
    float3 dir = WorldRayDirection();

    RayDesc ray;
    ray.Origin = WorldRayOrigin() + dir * RayTCurrent();
    ray.TMin = 0.1;
    ray.Direction = float3(dir.x, dir.y, -dir.z);
    ray.TMax = 1000.0;

#if BUGGED
    payload.data0 += uint4(1,1,1,1);

    if (payload.data0.x < RECURSION_DEPTH) {
        TraceRay(tlas,
                RAY_FLAG_FORCE_OPAQUE | RAY_FLAG_CULL_BACK_FACING_TRIANGLES |
                    0, // flags
                0xff,  // instance inclusion mask
                0,     // RayContributionToHitGroupIndex
                1,     // MultiplierForGeometryContributionToHitGroupIndex
                0,     // MissShaderIndex
                ray, payload);
    }
#else
    Payload new_payload;
    new_payload = payload;
    new_payload.data0 += uint4(1,1,1,1);

    if (new_payload.data0.x < RECURSION_DEPTH) {
        TraceRay(tlas,
                 RAY_FLAG_FORCE_OPAQUE | RAY_FLAG_CULL_BACK_FACING_TRIANGLES |
                     0, // flags
                 0xff,  // instance inclusion mask
                 0,     // RayContributionToHitGroupIndex
                 1,     // MultiplierForGeometryContributionToHitGroupIndex
                 0,     // MissShaderIndex
                 ray, new_payload);

        payload = new_payload;
    }
#endif
}
