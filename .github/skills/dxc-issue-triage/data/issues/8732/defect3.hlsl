// #8732 defect 3 -- assignment inside a loop, completed from the snippet.
// The atomic must target boundTex when the loop body never runs (tid.y == 0).
RWByteAddressBuffer outputBytes : register(u0);
RWTexture2D<uint> boundTex : register(u1);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    uint original;
    RWTexture2D<uint> mixed = boundTex;
    for (uint i = 0; i < tid.y; ++i)
        mixed = ResourceDescriptorHeap[i];
    InterlockedAdd(mixed[tid.xy], 3, original);
    outputBytes.Store(0, original);
}
