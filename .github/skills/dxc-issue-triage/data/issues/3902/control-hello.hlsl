// Feature-free control for #3902: a compute shader at the same profile with the same entry
// point and no ray tracing of any kind. Expect: no-match, exit 0.
//
// Two jobs. (1) It proves the predicate does not fire on everything -- a predicate that
// matched this would be indistinguishable from a bug that reproduces everywhere.
// (2) On the release sweep it separates "this release cannot express RayQuery / DXR 1.1"
// from "this release cannot compile cs_6_5 at all", which the RayQuery-using control on its
// own cannot tell apart.

RWBuffer<float> outBuf : register(u0);

[numthreads(8, 8, 1)]
void computeRTAO(
	uint3 groupId : SV_GroupID,
	uint3 groupThreadId : SV_GroupThreadID,
	uint3 dispatchThreadId : SV_DispatchThreadID,
	uint groupIndex : SV_GroupIndex )
{
  outBuf[dispatchThreadId.x] = groupIndex;
}
