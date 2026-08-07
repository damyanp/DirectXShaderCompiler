// #3695 minimisation attempt B: a user function RETURNING a resource, whose
// result initialises a local resource that is then assigned to a global.
//
// This is the combination the reporter's shader has and `minimal-assign.hlsl`
// does not. Everything else from the original is dropped: no root signature, no
// cbuffer globals, no loops, no GetDimensions, no arithmetic.
//
// Compiled with the issue's own arguments: -T cs_6_0 -E main

RWTexture2D<float4> A;
RWTexture2D<float4> B;

RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0, 0)] = 1.0;
  return tex;
}

[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(B);
  A = local;
}
