// Variant for #3092: the obvious workaround, and why it is closed.
//
// `static const` is what makes an initialiser usable as a numthreads argument
// (see control-static-const.hlsl), but a specialization constant may not be
// `static`. The two requirements are mutually exclusive today, so there is no
// spelling of the declaration that satisfies both.

[[vk::constant_id(1)]] static const uint TGSIZE_X = 4;

RWStructuredBuffer<uint> Out;

[numthreads(TGSIZE_X, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
  Out[tid.x] = tid.x;
}
