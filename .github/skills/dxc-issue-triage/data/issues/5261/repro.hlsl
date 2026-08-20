[numthreads(32, 8, 1)] void main(uint2 threadId
                                 : SV_DispatchThreadID) {
    ByteAddressBuffer buffer = ResourceDescriptorHeap[NonUniformResourceIndex(10)];
    RayDesc result = buffer.Load<RayDesc>(sizeof(RayDesc) * 1);
}
