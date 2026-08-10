// The template function below is verbatim from the 2026-08-10 comment on the issue
// (reported as crashing in Release and asserting in Debug).
//
// AGENT-CONSTRUCTED WRAPPER: the comment quotes a function body only, so the resource,
// the entry point and the instantiation are mine. T cannot be deduced (it appears only
// in the body), so the template arguments are given explicitly.
RWStructuredBuffer<float2> Out : register(u0);

template <typename T, typename T2, typename T3>
bool TRayVsAABB(T3 rayOrigin, T3 rayDir, T3 AABBMin, T3 AABBMax, out T2 intersections)
{
	T3 invRayDir = 1.0 / rayDir;
	T3 t0 = (AABBMin - rayOrigin) * invRayDir;
	T3 t1 = (AABBMax - rayOrigin) * invRayDir;
	T3 tmin = min(t0, t1);
	T3 tmax = max(t0, t1);

	T tClose = max(max(tmin.x, tmin.y), tmin.z);
	T tFar = min(min(tmax.x, tmax.y), tmax.z);
	intersections = T2(tClose, tFar);

	return tClose <= tFar;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    float2 hits;
    bool hit = TRayVsAABB<float, float2, float3>(
        float3(0, 0, 0), float3(1, 0, 0), float3(1, 1, 1), float3(2, 2, 2), hits);
    Out[threadId.x] = hit ? hits : float2(0, 0);
}
