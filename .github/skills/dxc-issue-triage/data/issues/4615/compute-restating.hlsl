// Issue 4615: compute restating of repro.hlsl, for compilers whose DXIL backend
// cannot lower a pixel shader writing SV_Target. Same shape as repro.hlsl: one
RWBuffer<float> Out : register(u0);
// statement before the #line directive and one after it.
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  float before = tid.x * 3.0f;
#line 400 "virtual-source.hlsl"
  Out[0] = before * 2.0f;
}
