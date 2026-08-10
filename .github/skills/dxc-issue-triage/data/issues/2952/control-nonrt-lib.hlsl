// #2952 negative control: a library with NO raytracing entry points.
//
// The symptom predicate is partly an absence claim ("no field of
// D3D12_FUNCTION_DESC holds the payload size"), and SKILL.md's standing trap is
// that such a clause is satisfied for free by an input that never had the thing
// in the first place. This library declares no payload anywhere, so the harness
// reports `payload-carrying-entries=0` and prints `API-PAYLOAD-SIZE=n/a`
// instead of `unavailable` -- and the predicate must NOT match.
//
// Expected: no-match.

RWBuffer<float4> Output : register(u0);

export float3 Scale(float3 v, float k) { return v * k; }

export float4 Combine(float3 a, float3 b) {
  return float4(Scale(a, 2.0f) + b, 1.0f);
}

[numthreads(8, 8, 1)] void CSMain(uint3 tid
                                  : SV_DispatchThreadID) {
  Output[tid.x] = Combine(float3(tid), float3(1, 2, 3));
}
