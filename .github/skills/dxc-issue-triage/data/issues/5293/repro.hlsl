// Verbatim from the issue description (2023-06-14).
// Command is the reporter's own: -E main -T cs_6_6 repro.hlsl -HV 2021
template <typename R>
void test(R x, out uint result) {
    uint repro = 0;
    result = 10;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x;
    test(10, x);
}
