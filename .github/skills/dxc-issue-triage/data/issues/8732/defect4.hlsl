// #8732 defect 4 -- buffer reassigned from heap to a bound resource, completed
// from the snippet. The load must target boundBuf. Reported as producing an
// ICE on the #8517 branch before the mixing diagnostic was added.
StructuredBuffer<uint> boundBuf : register(t0);
RWByteAddressBuffer outputBytes : register(u0);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    StructuredBuffer<uint> mixedBuf = ResourceDescriptorHeap[2];
    mixedBuf = boundBuf;
    uint value = mixedBuf.Load(0);
    outputBytes.Store(0, value);
}
