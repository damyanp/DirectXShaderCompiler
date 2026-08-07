// Variant of repro.hlsl: the same `static const uint` in [numthreads], but also
// referenced from inside the function body.
//
// Purpose: characterise the trigger. The assert in repro.hlsl is
// `MaybeODRUseExprs.empty()` in Sema::ActOnFinishFunctionBody, i.e. leftover
// potential-odr-use bookkeeping. If a full expression in the body drains that
// list (CleanupVarDeclMarking), the assert should not fire -- which would both
// confirm the mechanism and give users a workaround.
static const uint eight = 8;
RWBuffer<uint> buf;
[numthreads(eight, 8, 1)]
void main() { buf[0] = eight; }
