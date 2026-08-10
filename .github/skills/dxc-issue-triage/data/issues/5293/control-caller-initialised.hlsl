// IDENTITY CONTROL (--expect match). repro.hlsl with the caller's variable initialised:
// `uint x = 0;` instead of `uint x;`. The obvious guess is that the trigger is passing an
// uninitialised variable to an `out` parameter, which would make initialising it a workaround.
//
// It is not. The assert fires while analysing the *instantiated callee*, at `result = 10;`
// (stack in manual-case-assert-stack.txt: Sema::InstantiateFunctionDefinition ->
// AnalysisBasedWarnings::IssueWarnings -> TransferFunctions::VisitBinaryOperator), so the
// call site's state is irrelevant. This file must still score match.
template <typename R>
void test(R x, out uint result) {
    uint repro = 0;
    result = 10;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x = 0;
    test(10, x);
}
