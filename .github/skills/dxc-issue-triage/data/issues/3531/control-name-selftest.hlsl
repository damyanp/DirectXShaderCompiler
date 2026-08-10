// Control for issue 3531: proves clause 5 of match.json CAN fail.
//
// Identical to repro.hlsl except that the local named DynamicallyIndexedDynamicBuffer is an
// ordinary uint rather than a resource. If DXC emits debug info for it, the absence clause
// fails and the predicate scores no-match -- which is what proves the regex is not simply
// dead. Expect: no-match.

RWBuffer<float> floatRWUAV : register(u0);

static RWByteAddressBuffer DynamicBuffer = ResourceDescriptorHeap[1];
[numthreads(1, 1, 1)]
void DynamicResources()
{
    uint val = DynamicBuffer.Load(0u);
    uint DynamicallyIndexedDynamicBuffer = 256 + val &0xf;
    floatRWUAV[0] = DynamicBuffer.Load(DynamicallyIndexedDynamicBuffer);
}
