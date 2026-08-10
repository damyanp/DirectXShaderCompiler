// DERIVED PROBE, not the reporter's code. This is the 2026-08-10 comment's TRayVsAABB with
// one change: an extra `out T` (scalar) parameter, alongside the original `out T2` (vector).
//
// Why: repro-asobo.hlsl compiles cleanly, because the analysis that asserts only tracks `out`
// parameters of SCALAR type (isTrackedVar, tools/clang/lib/Analysis/UninitializedValues.cpp),
// and T2 instantiates to float2. This file shows that the same function does assert the moment
// one of its `out` parameters is a scalar -- i.e. today's report is the same defect, and the
// quoted function on its own is not the whole trigger.
RWStructuredBuffer<float2> Out : register(u0);

template <typename T, typename T2, typename T3>
bool TRayVsAABB(T3 rayOrigin, T3 rayDir, T3 AABBMin, T3 AABBMax, out T2 intersections, out T tCloseOut)
{
	T3 invRayDir = 1.0 / rayDir;
	T3 t0 = (AABBMin - rayOrigin) * invRayDir;
	T3 t1 = (AABBMax - rayOrigin) * invRayDir;
	T3 tmin = min(t0, t1);
	T3 tmax = max(t0, t1);

	T tClose = max(max(tmin.x, tmin.y), tmin.z);
	T tFar = min(min(tmax.x, tmax.y), tmax.z);
	intersections = T2(tClose, tFar);
	tCloseOut = tClose;

	return tClose <= tFar;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    float2 hits;
    float closest;
    bool hit = TRayVsAABB<float, float2, float3>(
        float3(0, 0, 0), float3(1, 0, 0), float3(1, 1, 1), float3(2, 2, 2), hits, closest);
    Out[threadId.x] = hit ? hits : float2(closest, 0);
}
