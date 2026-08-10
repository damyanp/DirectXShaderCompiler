// Control for issue 6727: a shader that compiles cleanly and never divides.
// Every successful compile trivially lacks binaryWithTwoOuts, so without the
// udiv/urem anchors the predicate would fire on any working shader at all.
// Expected: no-match.
RWStructuredBuffer<uint4> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  uint a = Out[tid.x].x;
  uint b = Out[tid.x].y;
  Out[tid.x] = uint4(a + b, a * b, a - b, a ^ b);
}
