struct AuxRay
{
    float3 origin;
    float3 direction;
};

struct Attribs
{
    float2 barys;
};

struct [raypayload] AOPayload
{
    float4 normalAndDepth : read(caller) : write(closesthit, miss);
    float  occlusion      : read(caller) : write(closesthit, miss);
    AuxRay ddxRay         : read(anyhit) : write(caller);
    AuxRay ddyRay         : read(anyhit) : write(caller);
};

RaytracingAccelerationStructure Scene : register(t0);

[shader("raygeneration")]
void RaygenShader()
{
    AOPayload payload;

    AuxRay ddx;
    ddx.origin = float3(0, 0, 0);
    ddx.direction = float3(0, 0, 1);
    AuxRay ddy;
    ddy.origin = float3(0, 0, 0);
    ddy.direction = float3(0, 1, 0);

    // Whole-struct cast-assignment, exactly as filed, but TraceRay called
    // DIRECTLY in raygen (matching nested_access.hlsl TEST_NUM=5's shape)
    // to isolate whether the cast-assignment idiom itself is the problem.
    payload.ddxRay = (AuxRay)ddx;
    payload.ddyRay = (AuxRay)ddy;

    RayDesc ray;
    ray.Origin = float3(0, 0, 0);
    ray.Direction = float3(0, 0, 1);
    ray.TMin = 0;
    ray.TMax = 1000;

    TraceRay(Scene, RAY_FLAG_NONE, 0xFF, 0, 1, 0, ray, payload);
}

[shader("closesthit")]
void ClosestHit(inout AOPayload payload, in Attribs attribs)
{
    payload.normalAndDepth = float4(0, 0, 1, 1);
    payload.occlusion = 0;
}

[shader("miss")]
void Miss(inout AOPayload payload)
{
    payload.normalAndDepth = float4(0, 0, 0, 0);
    payload.occlusion = 1;
}

[shader("anyhit")]
void AnyHit(inout AOPayload payload, in Attribs attribs)
{
    float3 o = payload.ddxRay.origin + payload.ddyRay.origin;
    if (o.x > 1000.0)
        AcceptHitAndEndSearch();
}
