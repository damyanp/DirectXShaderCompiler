// #8732 defect 1 -- conditional assignment, verbatim from the issue body.
//
// `mixed` holds a BOUND texture on the fall-through path and a HEAP descriptor
// only when tid.x == 0. Correct lowering must pick per path (or diagnose).
RWByteAddressBuffer outputBytes : register(u0);
RWTexture2D<uint> boundTex : register(u1);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    uint original;
    RWTexture2D<uint> mixed = boundTex;
    if (tid.x == 0)
        mixed = ResourceDescriptorHeap[1];
    InterlockedAdd(mixed[tid.xy], 1, original);
    outputBytes.Store(0, original);
}
