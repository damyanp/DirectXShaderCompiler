RWByteAddressBuffer buffer : register(u0);

[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
        buffer.Store(id.x, 0);
        buffer = ResourceDescriptorHeap[0];
        buffer.Store(id.x, 0);
}
