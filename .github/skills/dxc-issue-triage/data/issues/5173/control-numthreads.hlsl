// Positive control for #5173's harness (isense_probe.cpp / measure.py).
// [numthreads(...)] is attached via the ordinary Clang Attr mechanism
// (HLSLNumThreads in Attr.td, with a real spelling), unlike HLSLSemantic.
// This proves the cursor-tree walk CAN surface an attribute cursor when one
// is actually created through D->attrs() -- the absence of any such cursor
// for the semantics in repro.hlsl is therefore a property of how semantics
// are stored, not a blind spot in this harness or in GetChildren's use of
// clang_visitChildren.
[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID)
{
}
