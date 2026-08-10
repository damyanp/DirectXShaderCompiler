// Control for issue 6727: deliberately invalid HLSL.
// The predicate's absence clause ("no binaryWithTwoOuts in the output") is
// satisfied for free by output that contains no DXIL at all. The positive
// anchors must reject this. Expected: no-match.
RWStructuredBuffer<uint4> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  uint a = Out[tid.x].x
  uint b = Out[tid.x].y;
  Out[tid.x] = uint4(a / b, a % b, 0, 0);
}
