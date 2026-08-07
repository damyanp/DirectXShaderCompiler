// #8737 -- "Do not forget about RWTexture2DMSArray" (reporter's Desired Outcome).
//
// Case A on the array flavour. Here the address is a uint3 (x, y, array slice), so
// ALL THREE atomicBinOp coordinate operands are consumed by the address and there is
// no operand left for a sample index even in principle.
struct PSInput {
    uint3 uvw : UVW;
    uint s : SAMPLE;
};

RWTexture2DMSArray<uint, 2> tex;

uint PSMain(PSInput input) : SV_Target0
{
    uint value = 0xDEADBEEF;
    uint old_val;

    InterlockedMax(tex[input.uvw], value, old_val);

    tex[input.uvw] = value;
    tex.sample[input.s][input.uvw] = value;
    return old_val;
}
