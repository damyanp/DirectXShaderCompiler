// Position matrix: where does DXC's existing out-of-bounds vector subscript
// check (err_hlsl_vector_element_index_out_of_bounds) actually fire?
// Each case is compiled separately via -D CASE=n.
StructuredBuffer<float3> g_vertices : register(t0);
ByteAddressBuffer g_indices : register(t1);
RWBuffer<float> g_out : register(u0);

float take(uint i) { return i; }

[numthreads(1, 1, 1)]
void main(uint tid : SV_DispatchThreadID) {
  const uint3 indices = g_indices.Load3(tid * 12);
  float r = 0;

#if CASE == 1
  // plain local initializer
  uint x = indices[3];
  r = x;
#elif CASE == 2
  // index of another operator[] -- the reporter's shape
  r = g_vertices[indices[3]].x;
#elif CASE == 3
  // inside an initializer list, via member access -- the reporter's exact shape
  float3 n[3] = { g_vertices[indices[0]], g_vertices[indices[1]],
                  g_vertices[indices[3]] };
  r = n[2].x;
#elif CASE == 4
  // ordinary function call argument
  r = take(indices[3]);
#elif CASE == 5
  // assignment left-hand side
  uint3 m = indices;
  m[3] = 7;
  r = m[0];
#elif CASE == 6
  // arithmetic subexpression
  r = indices[3] + 1;
#elif CASE == 7
  // swizzle spelling of the same access
  r = indices.w;
#elif CASE == 8
  // out-of-bounds on a real array, reporter's shape
  uint a[3] = { 1, 2, 3 };
  r = g_vertices[a[3]].x;
#elif CASE == 9
  // out-of-bounds on a real array, plain local initializer
  uint a[3] = { 1, 2, 3 };
  uint x = a[3];
  r = x;
#elif CASE == 10
  // index operand of a plain array subscript (no resource involved)
  float arr[4] = { 0, 1, 2, 3 };
  r = arr[indices[3]];
#elif CASE == 11
  // index operand of a vector subscript
  r = indices[indices[3]];
#endif

  g_out[tid] = r;
}
