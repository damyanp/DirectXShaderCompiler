// NEGATIVE CONTROL, from the description's own workaround (1): "Removing and inlining
// the template (replacing R with uint)". Differs from repro.hlsl in exactly that.
// Must score no-match.
void test(uint x, out uint result) {
    uint repro = 0;
    result = 10;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x;
    test(10, x);
}
