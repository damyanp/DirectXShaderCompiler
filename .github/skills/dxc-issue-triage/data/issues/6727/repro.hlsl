// Issue 6727: HLSL has no way to ask for the two outputs of the DXIL
// IMul / UMul / UDiv operations, so both pairs below have to be expressed
// indirectly and neither reaches dx.op.binaryWithTwoOuts.
RWStructuredBuffer<uint4> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  uint a = Out[tid.x].x;
  uint b = Out[tid.x].y;

  // Wanted: UMul's two outputs, the high and low 32 bits of a * b.
  // Written the only way HLSL allows, which is via 64-bit arithmetic.
  uint64_t prod = (uint64_t)a * (uint64_t)b;
  uint hi = (uint)(prod >> 32);
  uint lo = (uint)prod;

  // Wanted: UDiv's two outputs, quotient and remainder of one operand pair.
  uint quot = a / b;
  uint rem = a % b;

  Out[tid.x] = uint4(hi, lo, quot, rem);
}
