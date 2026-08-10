// NEGATIVE CONTROL, from the description's own workaround (3): "Replacing `out` with
// `inout`". Differs from repro.hlsl in exactly that keyword. Must score no-match.
template <typename R>
void test(R x, inout uint result) {
    uint repro = 0;
    result = 10;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x;
    test(10, x);
}
