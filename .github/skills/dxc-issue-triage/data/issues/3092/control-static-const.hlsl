// Negative control for #3092.
//
// Same shape as repro.hlsl, but the numthreads argument is an ordinary
// compile-time constant instead of a specialization constant. This must
// compile clean and must NOT match match.json -- which is what shows the
// predicate is specific to the spec-constant case rather than firing on any
// named constant used as a numthreads argument.

static const uint TGSIZE_X = 4;

RWStructuredBuffer<uint> Out;

[numthreads(TGSIZE_X, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  Out[tid.x] = tid.x;
}
