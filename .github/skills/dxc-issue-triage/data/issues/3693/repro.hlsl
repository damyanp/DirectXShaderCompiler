#include "ShaderShared.h"

GlobalRootSignature DefaultRT_GlobalRootSignature =
{
    "RootFlags(0),"
    "DescriptorTable( UAV( u0 ), SRV( t0 ), CBV( b0 ) )"   // g_rtOutput, g_tlas, g_sceneCB
};

LocalRootSignature DefaultRT_LocalRootSignature =
{
    "DescriptorTable( SRV( t1, numDescriptors = 2 ) ),"    // g_indices, g_vertices
    "RootConstants( num32BitConstants = 4, b1 )"           // g_materialCB (inlined)
};

TriangleHitGroup DefaultRT_HitGroup =
{
    "",                             // AnyHit
    "DefaultRT_ClosestHitShader"    // ClosestHit
};

RaytracingShaderConfig  DefaultRT_ShaderConfig =
{
    16,                             // Max payload size (sizeof(RayPayload))
    8                               // Max attribute size (sizeof(BuiltInTriangleIntersectionAttributes))
};

RaytracingPipelineConfig DefaultRT_PipelineConfig =
{
    1                               // Max trace recursion depth
};

// Global root signature resources:
RWTexture2D<float4> g_rtOutput : register(u0);
RaytracingAccelerationStructure g_tlas : register(t0);
ConstantBuffer<SceneConstants> g_sceneCB : register(b0);

// Local root signature resources:
ByteAddressBuffer g_indices : register(t1);
StructuredBuffer<Vertex> g_vertices : register(t2);
ConstantBuffer<MaterialConstants> g_materialCB : register(b1);

struct RayPayload
{
    float4 color;
};

// Retrieve hit world position.
float3 HitWorldPosition()
{
    return WorldRayOrigin() + RayTCurrent() * WorldRayDirection();
}

// Retrieve attribute at a hit position interpolated from vertex attributes using the hit's barycentrics.
float3 HitAttribute(float3 vertexAttribute[3], BuiltInTriangleIntersectionAttributes attr)
{
    return vertexAttribute[0] +
        attr.barycentrics.x * (vertexAttribute[1] - vertexAttribute[0]) +
        attr.barycentrics.y * (vertexAttribute[2] - vertexAttribute[0]);
}

// Generate a ray in world space for a camera pixel corresponding to an index from the dispatched 2D grid.
inline void GenerateCameraRay(uint2 index, out float3 origin, out float3 direction)
{
    float2 xy = index + 0.5f; // center in the middle of the pixel.
    float2 screenPos = xy / DispatchRaysDimensions().xy * 2.0 - 1.0;

    // Invert Y for DirectX-style coordinates.
    screenPos.y = -screenPos.y;

    // Unproject the pixel coordinate into a ray.
    float4 world = mul(float4(screenPos, 0, 1), g_sceneCB.projectionViewWorld);

    world.xyz /= world.w;
    origin = g_sceneCB.cameraWorldPos;
    direction = normalize(world.xyz - origin);
}

// Diffuse lighting calculation.
float4 CalculateDiffuseLighting(float3 hitPosition, float3 normal)
{
    float3 pixelToLight = normalize(g_sceneCB.lightWorldPos - hitPosition);

    // Diffuse contribution.
    float nDotL = max(0.0f, dot(pixelToLight, normal));

    return g_materialCB.albedo * g_sceneCB.lightDiffuseColor * nDotL;
}

[shader("raygeneration")]
void DefaultRT_RayGenShader()
{
    float3 rayDir;
    float3 origin;

    // Generate a ray for a camera pixel corresponding to an index from the dispatched 2D grid.
    GenerateCameraRay(DispatchRaysIndex().xy, origin, rayDir);

    // Trace the ray.
    // Set the ray's extents.
    RayDesc ray;
    ray.Origin = origin;
    ray.Direction = rayDir;
    // Set TMin to a non-zero small value to avoid aliasing issues due to floating - point errors.
    // TMin should be kept small to prevent missing geometry at close contact areas.
    ray.TMin = 0.001;
    ray.TMax = g_sceneCB.rayMaxLength;
    RayPayload payload = { float4(0, 0, 0, 0) };
    TraceRay(g_tlas, RAY_FLAG_CULL_BACK_FACING_TRIANGLES, ~0, 0, 1, 0, ray, payload);

    // Write the raytraced color to the output texture.
    g_rtOutput[DispatchRaysIndex().xy] = payload.color;
}

[shader("closesthit")]
void DefaultRT_ClosestHitShader(inout RayPayload payload, in BuiltInTriangleIntersectionAttributes attr)
{
    float3 hitPosition = HitWorldPosition();

    // Load index buffer
    uint indexOffset = PrimitiveIndex() * 3 /* indices per primitive */ * 4 /* 4 bytes per index*/;
    const uint3 indices = g_indices.Load3(indexOffset);

    // Retrieve corresponding vertex normals for the triangle vertices.
    float3 vertexNormals[3] = { g_vertices[indices[0]].normal, g_vertices[indices[1]].normal, g_vertices[indices[3]].normal };
    //                                                                                                           ^
    //                                                                                                           |
    // THIS SHOULD LEAD TO A COMPILER WARNING AT LEAST -----------------------------------------------------------

    // Compute the triangle's interpolated normal
    float3 triangleNormal = HitAttribute(vertexNormals, attr);

    float4 diffuseColor = CalculateDiffuseLighting(hitPosition, triangleNormal);
    float4 color = g_sceneCB.lightAmbientColor + diffuseColor;

    payload.color = color;
}

[shader("miss")]
void DefaultRT_MissShader(inout RayPayload payload)
{
    float4 background = float4(0.0f, 0.2f, 0.4f, 1.0f);
    payload.color = background;
}
