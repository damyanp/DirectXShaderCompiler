struct S {
  float2x3 m;
};

RWByteAddressBuffer buffer : register(u0);

[numthreads(1, 1, 1)]
void main() {
  float2x3 m = float2x3(42.0f, 43.0f, 44.0f, 45.0f, 46.0f, 47.0f);
  m[0] = float3(1, 2, 3);
  m[1] = float3(4, 5, 6);

  const S a = {m}; // invalid: should capture 1,2,3,4,5,6, not the init values

  buffer.Store3(0u, int3(a.m[0]));
  buffer.Store3(16u, int3(a.m[1]));
}
