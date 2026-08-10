struct Constants {
    uint raytracing_scene_idx;
} constants;

float4 main() : SV_Target0 {
    RaytracingAccelerationStructure rtas = ResourceDescriptorHeap[constants.raytracing_scene_idx];

    RayQuery<RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH | RAY_FLAG_CULL_BACK_FACING_TRIANGLES | RAY_FLAG_SKIP_PROCEDURAL_PRIMITIVES> query;

    // RayDesc ray = (RayDesc)0;
    // ray.Origin = float3(0, 0, 0);
    // ray.TMin = 0.01;
    // ray.Direction = float3(0, 1, 0);
    // ray.TMax = 1000000;
    //             
    // query.TraceRayInline(rtas, 0, 0xFF, ray);
    // query.Proceed();
    // if(query.CommittedStatus() != COMMITTED_TRIANGLE_HIT) {
    //     return 1;
    // }

    return 0;
}
