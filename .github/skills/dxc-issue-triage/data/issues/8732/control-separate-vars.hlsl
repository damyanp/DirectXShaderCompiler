// #8732 CONTROL (negative) -- the reporter's own documented workaround:
// "use separate variables for bound and heap-loaded resources".
//
// This control carries BOTH of match.json's positive markers -- an atomic and
// an OpUntypedAccessChainKHR heap access -- and is separated from the symptom
// only by `boundTex` still being present in the module. It is what proves the
// first two clauses alone do not discriminate.
RWByteAddressBuffer outputBytes : register(u0);
RWTexture2D<uint> boundTex : register(u1);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    uint original;
    RWTexture2D<uint> heapTex = ResourceDescriptorHeap[1];
    RWTexture2D<uint> boundOnly = boundTex;
    InterlockedAdd(boundOnly[tid.xy], 1, original);
    heapTex[tid.xy] = original;
    outputBytes.Store(0, original);
}
