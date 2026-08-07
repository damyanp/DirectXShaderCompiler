// #8732 defect 5 -- the case the reporter states is STILL not diagnosed even on
// the #8517 branch: a heap-only conditional assignment with no bound-resource
// counterpart, so `wasBound` is never set and the mixing check does not fire.
// `mixed` has no descriptor at all on the else path.
RWByteAddressBuffer outputBytes : register(u0);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    uint original;
    RWTexture2D<uint> mixed;
    if (tid.x == 0)
        mixed = ResourceDescriptorHeap[1];
    InterlockedAdd(mixed[uint2(0, 0)], 1, original);
    outputBytes.Store(0, original);
}
