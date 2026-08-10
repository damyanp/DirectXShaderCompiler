RWStructuredBuffer<uint4> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  uint a = Out[tid.x].x;
  uint b = Out[tid.x].y;
  Out[tid.x] = uint4(a / b, a % b, 0, 0);
}
