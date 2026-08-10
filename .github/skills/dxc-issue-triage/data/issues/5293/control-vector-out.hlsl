// NEGATIVE CONTROL for the scalar-only boundary. repro.hlsl with the out parameter and the
// local widened from uint to float2. Everything else is identical.
//
// isTrackedVar() tracks an HLSL `out` parameter only when its type isScalarType(), so the
// vector out parameter is never entered into declToIndex and the assignment to it never
// reaches the failing lookup. Must score no-match. This is the control that explains why
// the 2026-08-10 comment's own function (out T2 == out float2) compiles cleanly.
template <typename R>
void test(R x, out float2 result) {
    float2 repro = 0;
    result = float2(10, 10);
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    float2 x;
    test(10, x);
}
