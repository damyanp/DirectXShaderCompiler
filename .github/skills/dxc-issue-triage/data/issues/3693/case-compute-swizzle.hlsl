// CONTROL for #3693's Compiler Explorer link: proves the Clang HLSL pane really is
// compiling and diagnosing this source. `indices.w` is the swizzle spelling of the same
// out-of-bounds element; if a compiler is silent on BOTH this and case-compute.hlsl,
// its silence on the latter is not evidence of anything.
StructuredBuffer<float3> g_vertices : register(t0);
ByteAddressBuffer g_indices : register(t1);
RWBuffer<float3> g_out : register(u0);

[numthreads(1, 1, 1)]
void main(uint tid : SV_DispatchThreadID) {
  const uint3 indices = g_indices.Load3(tid * 12);

  g_out[tid] = g_vertices[indices.w];
}
