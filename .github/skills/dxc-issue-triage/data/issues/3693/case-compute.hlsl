// #3693 restated as a compute shader.
//
// Same construct as repro.hlsl: a 3-element vector is subscripted with the constant 3,
// and that subscript is the INDEX OPERAND of another subscript. The stage is irrelevant
// to the defect, so this form is portable to every release back to v1.4.1907 (which
// predates lib_6_6) and to compilers whose raytracing support is incomplete.
StructuredBuffer<float3> g_vertices : register(t0);
ByteAddressBuffer g_indices : register(t1);
RWBuffer<float3> g_out : register(u0);

[numthreads(1, 1, 1)]
void main(uint tid : SV_DispatchThreadID) {
  const uint3 indices = g_indices.Load3(tid * 12);

  // indices[3] is out of bounds: a uint3 has elements 0..2.
  g_out[tid] = g_vertices[indices[3]];
}
