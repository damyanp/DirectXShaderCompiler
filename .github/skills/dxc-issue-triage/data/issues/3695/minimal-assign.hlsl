// #3695 minimisation attempt A: global resource assignment ONLY.
//
// The reporter's hypothesis is that the crash "seems to be related to assigning
// one RWTexture2D<float4> global variable to another". This strips the shader
// to exactly that, dropping the root signature, the cbuffer globals, the loops,
// GetDimensions, and the resource-returning function.
//
// Compiled with the issue's own arguments: -T cs_6_0 -E main

RWTexture2D<float4> A;
RWTexture2D<float4> B;

[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID) {
  A = B;
  A[id.xy] = 1.0;
}
