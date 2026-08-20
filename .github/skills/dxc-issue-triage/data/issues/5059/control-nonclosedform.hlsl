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

    // Same trip-count shape as the reported repro (loop while processed !=
    // input, incrementing processed each iteration), but the accumulated
    // value is read from memory each iteration instead of being a closed-form
    // arithmetic series (input-1)*(input-2)/2. SCEV can still count the trip
    // count, but there is no summation for it to fold into a
    // multiply-based closed form, so nothing needs extra bits to guard
    // against overflow. This isolates "any bounded while loop" (which must
    // NOT trigger the predicate) from "a loop SCEV rewrites into an
    // overflow-guarded closed form" (which does).
    while (processed != input)
    {
        result += IOBuffer.Load(4 * (processed % 4));
        processed++;
    }

    IOBuffer.Store(1, result);
}
