// #3695 minimised repro (candidate C3 from manual-case-minimisation.txt).
//
// Crashes dxc with the issue's own arguments:  -T cs_6_0 -E main
//
// The reporter's shader is ~60 lines; this is the part that matters. Note that
// it is NOT simply "assigning one RWTexture2D<float4> global to another" --
// that alone is correctly diagnosed (see minimal-assign.hlsl). What crashes is
// passing a global resource to a function that RETURNS it, and assigning the
// result back to the SAME global. minimal-return.hlsl, which assigns to a
// different global, is diagnosed rather than crashing.

RWTexture2D<float4> A;

RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0, 0)] = 1.0;
  return tex;
}

[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A);
  A = local;
}
