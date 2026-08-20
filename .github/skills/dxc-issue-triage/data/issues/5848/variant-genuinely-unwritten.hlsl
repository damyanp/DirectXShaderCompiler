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

void TraceRadianceRay(in RayDesc ray, inout AOPayload payload)
{
    TraceRay(Scene, RAY_FLAG_NONE, 0xFF, 0, 1, 0, ray, payload);
}

[shader("raygeneration")]
void RaygenShader()
{
    AOPayload payload;
    // Deliberately NEVER write ddxRay/ddyRay anywhere -- a genuine bug, to
    // check whether -Wpayload-access-trace can fire AT ALL when the TraceRay
    // call is inside a helper function rather than directly in raygen.
    RayDesc ray;
    ray.Origin = float3(0, 0, 0);
    ray.Direction = float3(0, 0, 1);
    ray.TMin = 0;
    ray.TMax = 1000;

    TraceRadianceRay(ray, payload);
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
