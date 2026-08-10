// Equivalence control for issue 3531: measures the one deviation repro.hlsl makes from the
// issue body.
//
// The snippet as filed writes through an undeclared `floatRWUAV`; repro.hlsl completes it as
// a bound RWBuffer<float>. This variant removes the bound resource entirely and writes back
// through a heap resource instead, so nothing bound is present. If it behaves the same, the
// repair is inert.

static RWByteAddressBuffer DynamicBuffer = ResourceDescriptorHeap[1];
[numthreads(1, 1, 1)]
void DynamicResources()
{
    uint val = DynamicBuffer.Load(0u);
    RWByteAddressBuffer DynamicallyIndexedDynamicBuffer = ResourceDescriptorHeap[256 + val &0xf];
    DynamicBuffer.Store(0, DynamicallyIndexedDynamicBuffer.Load(0));
}
