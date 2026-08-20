#define _RootSig \
"RootFlags(0),"\
"DescriptorTable(UAV(u0, numDescriptors = 1))"

RWByteAddressBuffer IOBuffer  : register(u0);

[RootSignature(_RootSig)]
[numthreads(8, 8, 1)]
void CSMain(uint3 globalID : SV_DispatchThreadID)
{
    uint input     = IOBuffer.Load(0);
    uint processed = 0;
    uint result    = 1;
 
    while (processed != input)
    {
        result   += processed;
        processed++;
    }
    
    IOBuffer.Store(1, result);
}