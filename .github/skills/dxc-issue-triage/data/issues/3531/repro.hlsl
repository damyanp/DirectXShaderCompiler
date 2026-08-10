// Repro for issue 3531 — "No debug info for locally-declared dynamic resources (SM 6.6)".
//
// The issue body's snippet is reproduced verbatim except for one repair: it uses an
// undeclared `floatRWUAV`, so as filed it does not compile. The declaration below is the
// minimal completion (a bound RWBuffer<float>, which is what the name describes).
// variant-alldynamic replaces it with a heap resource to prove the repair is inert.

RWBuffer<float> floatRWUAV : register(u0);

static RWByteAddressBuffer DynamicBuffer = ResourceDescriptorHeap[1];
[numthreads(1, 1, 1)]
void DynamicResources()
{
    uint val = DynamicBuffer.Load(0u);
    RWByteAddressBuffer DynamicallyIndexedDynamicBuffer = ResourceDescriptorHeap[256 + val &0xf];
    floatRWUAV[0] = DynamicallyIndexedDynamicBuffer.Load(0);
}
