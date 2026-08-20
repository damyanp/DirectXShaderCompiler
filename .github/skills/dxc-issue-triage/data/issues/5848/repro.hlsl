// Best-effort reconstruction of issue #5848: a [raypayload] struct has two
// members qualified read(anyhit):write(caller). The raygeneration shader
// writes both members directly, then calls a *helper function*
// TraceRadianceRay(...) which takes the payload as an `inout` parameter and
// itself calls TraceRay(...). The report claims DXC warns
// "field '<x>' is 'write' for 'caller' stage but field is never written for
// TraceRay call" even though the field IS written -- just in the caller of
// the function containing the TraceRay call, not in that function itself.
//
// This mirrors, but does not duplicate, the "foo"/"foo_in"/"foo_out" helper
// pattern in
// tools/clang/test/HLSLFileCheck/hlsl/payload_qualifier/nested_access.hlsl
// TEST_NUM=3: that block puts the field read/write *inside* the helper and
// checks ordinary read/write-tracking through closesthit; here the write is
// in the raygeneration shader (the caller) and the TraceRay call itself is
// what is one function away.

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

    // The reporter writes the whole nested struct in one assignment via an
    // explicit cast from a distinct-but-layout-compatible type:
    //     payload.ddxRay = (AuxilliaryRay)ddx;
    // Reproduce that exact shape rather than assigning member-by-member.
    AuxRay ddx;
    ddx.origin = float3(0, 0, 0);
    ddx.direction = float3(0, 0, 1);
    AuxRay ddy;
    ddy.origin = float3(0, 0, 0);
    ddy.direction = float3(0, 1, 0);

    payload.ddxRay = (AuxRay)ddx;
    payload.ddyRay = (AuxRay)ddy;

    RayDesc ray;
    ray.Origin = float3(0, 0, 0);
    ray.Direction = float3(0, 0, 1);
    ray.TMin = 0;
    ray.TMax = 1000;

    // TraceRay is not called here directly -- it is one function away,
    // exactly like the reporter's TraceRadianceRay() helper.
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
    // Reads ddxRay/ddyRay, matching their read(anyhit) qualifier.
    float3 o = payload.ddxRay.origin + payload.ddyRay.origin;
    if (o.x > 1000.0)
        AcceptHitAndEndSearch();
}
