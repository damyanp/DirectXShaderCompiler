// NEGATIVE CONTROL, from the description's own workaround (2): "Removing the unused
// `uint repro = 0;` variable". Differs from repro.hlsl in exactly that line.
// Must score no-match.
template <typename R>
void test(R x, out uint result) {
    result = 10;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x;
    test(10, x);
}
