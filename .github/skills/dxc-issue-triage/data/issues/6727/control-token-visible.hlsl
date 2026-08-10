// Control for issue 6727: proves the not_regex clause can actually fire.
// Identical to repro.hlsl except that this comment contains the literal token
// the predicate looks for: dx.op.binaryWithTwoOuts.i32
// Compiled with -Zi -Qembed_debug, DXC records its own input in
// !dx.source.contents, so the token appears in the output text even though the
// compiler never emits that operation. Expected: no-match, because the
// not_regex clause fails -- which is the observation that makes the clause
// falsifiable rather than unfalsifiable.
RWStructuredBuffer<uint4> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  uint a = Out[tid.x].x;
  uint b = Out[tid.x].y;

  uint64_t prod = (uint64_t)a * (uint64_t)b;
  uint hi = (uint)(prod >> 32);
  uint lo = (uint)prod;

  uint quot = a / b;
  uint rem = a % b;

  Out[tid.x] = uint4(hi, lo, quot, rem);
}
