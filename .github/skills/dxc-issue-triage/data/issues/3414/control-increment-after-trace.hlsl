// Control separating "the traced payload lacks the increment" from "the traced
// payload IS the caller's object".
//
// Same shader, except the increment is applied AFTER the recursive TraceRay
// instead of before it, so correct codegen hands the recursion an
// un-incremented payload.
//
// This file was written under the first reading of #3414 (a dropped store),
// where it would have been a positive control.  The measured defect turned out
// to be aliasing instead, so it is not one: it scores no-match on fixed
// compilers -- correct codegen still copies the payload, whatever value is in
// it -- and match on the 13 affected releases, because this shader traces with
// its own incoming payload too and is subject to the same defect.  Both
// outcomes are recorded in the captures; see the note in match.json.
#define RECURSION_DEPTH 30

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

    if (payload.data0.x < RECURSION_DEPTH) {
        TraceRay(tlas,
                RAY_FLAG_FORCE_OPAQUE | RAY_FLAG_CULL_BACK_FACING_TRIANGLES |
                    0, // flags
                0xff,  // instance inclusion mask
                0,     // RayContributionToHitGroupIndex
                1,     // MultiplierForGeometryContributionToHitGroupIndex
                0,     // MissShaderIndex
                ray, payload);

        payload.data0 += uint4(1,1,1,1);
    }
}
