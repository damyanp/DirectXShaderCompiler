#define _RootSig \
"RootFlags(0),"\
"DescriptorTable(UAV(u0, numDescriptors = 1))"

RWByteAddressBuffer IOBuffer  : register(u0);

[RootSignature(_RootSig)]
[numthreads(8, 8, 1)]
void CSMain(uint3 globalID : SV_DispatchThreadID)
{
    uint input = IOBuffer.Load(0);
    IOBuffer.Store(1, input + 1);
}
