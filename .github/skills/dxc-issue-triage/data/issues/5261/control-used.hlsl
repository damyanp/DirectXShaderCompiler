RWStructuredBuffer<float> Out : register(u0);

[numthreads(32, 8, 1)] void main(uint2 threadId
                                 : SV_DispatchThreadID) {
    ByteAddressBuffer buffer = ResourceDescriptorHeap[NonUniformResourceIndex(10)];
    RayDesc result = buffer.Load<RayDesc>(sizeof(RayDesc) * 1);
    Out[0] = result.TMin + result.TMax + result.Origin.x + result.Direction.x;
}
