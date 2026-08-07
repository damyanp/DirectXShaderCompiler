// CONTROL for #3693's Compiler Explorer link: the same out-of-bounds access as
// case-compute.hlsl, hoisted out of the index operand into a plain local initializer.
// DXC diagnoses this form; it is here to show that the gap is about WHERE the subscript
// appears, not about whether the compiler can see it at all.
StructuredBuffer<float3> g_vertices : register(t0);
ByteAddressBuffer g_indices : register(t1);
RWBuffer<float3> g_out : register(u0);

[numthreads(1, 1, 1)]
void main(uint tid : SV_DispatchThreadID) {
  const uint3 indices = g_indices.Load3(tid * 12);

  const uint oob = indices[3];
  g_out[tid] = g_vertices[oob];
}
