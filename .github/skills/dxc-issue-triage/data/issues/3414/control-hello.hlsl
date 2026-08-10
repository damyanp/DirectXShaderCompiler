// Feature-presence control: the smallest lib_6_3 raytracing shader that uses
// TraceRay with an inout payload at all.  Run per release, it distinguishes
// "this release did not reproduce" from "this release cannot compile DXR at
// all", and it must never satisfy the #3414 predicate.
struct Payload {
    uint4 data0;
};

RaytracingAccelerationStructure tlas : register(t0, space0);

[shader("raygeneration")] void
rgs() {
    Payload payload;
    payload.data0 = uint4(0, 0, 0, 0);

    RayDesc ray;
    ray.Origin = float3(0, 0, 0);
    ray.TMin = 0.1;
    ray.Direction = float3(0, 0, 1);
    ray.TMax = 1000.0;

    TraceRay(tlas, RAY_FLAG_FORCE_OPAQUE, 0xff, 0, 1, 0, ray, payload);
}
