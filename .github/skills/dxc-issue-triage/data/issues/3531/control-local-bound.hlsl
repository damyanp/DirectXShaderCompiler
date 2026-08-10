// Control for issue 3531: is the gap specific to DYNAMIC resources, or does any locally
// declared resource lack debug info?
//
// Identical in shape to repro.hlsl except that the local resource aliases an ordinary bound
// RWByteAddressBuffer instead of ResourceDescriptorHeap. `val` is kept live so the detector's
// self-test clause is exercised here exactly as it is in the repro.

RWBuffer<float> floatRWUAV : register(u0);
RWByteAddressBuffer BoundBuffer : register(u1);

static RWByteAddressBuffer DynamicBuffer = BoundBuffer;
[numthreads(1, 1, 1)]
void DynamicResources()
{
    uint val = DynamicBuffer.Load(0u);
    RWByteAddressBuffer DynamicallyIndexedDynamicBuffer = BoundBuffer;
    floatRWUAV[256 + val &0xf] = DynamicallyIndexedDynamicBuffer.Load(0);
}
