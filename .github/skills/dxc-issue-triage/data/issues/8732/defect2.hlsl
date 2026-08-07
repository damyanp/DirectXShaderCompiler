// #8732 defect 2 -- reassignment to a bound resource, completed from the
// snippet in the issue body. Straight-line code, no control flow: the atomic
// must target boundTex, because that is the last thing assigned to `mixed`.
RWByteAddressBuffer outputBytes : register(u0);
RWTexture2D<uint> boundTex : register(u1);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    uint original;
    RWTexture2D<uint> mixed = ResourceDescriptorHeap[2];
    mixed = boundTex;
    InterlockedAdd(mixed[tid.xy], 2, original);
    outputBytes.Store(0, original);
}
