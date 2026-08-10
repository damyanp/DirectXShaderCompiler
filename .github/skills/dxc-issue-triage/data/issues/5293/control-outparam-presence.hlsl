// POSITIVE / FEATURE-PRESENCE CONTROL for the analysis that asserts.
//
// The failing code is the `out`-parameter uninitialized-value analysis added by
// 1380cf88e, "Add diagnostics for uninitialized `out` parameters (#5047)", 2023-03-01.
// Its user-visible product is -Wparameter-usage. This shader has a scalar `out` parameter
// that is never written, and no template, so a build that carries the analysis warns
//
//     warning: parameter 'result' is uninitialized when used here [-Wparameter-usage]
//
// and a build that predates it says nothing. That gives a behavioural test for whether a
// given release even contains the code under test -- which matters because the release
// binaries are Release builds and cannot show the assert itself.
//
// It must score no-match under match.json: a warning is not an internal failure.
void neverWrites(uint x, out uint result) {
    uint unused = 0;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x;
    neverWrites(10, x);
}
