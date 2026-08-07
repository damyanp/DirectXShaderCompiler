// #8737 -- "Do not forget about RWTexture2DMSArray" (reporter's Desired Outcome).
// Case B on the array flavour.
struct PSInput {
    uint3 uvw : UVW;
    uint s : SAMPLE;
};

RWTexture2DMSArray<uint, 2> tex;

uint PSMain(PSInput input) : SV_Target0
{
    uint value = 0xDEADBEEF;
    uint old_val;

    InterlockedMax(tex.sample[input.s][input.uvw], value, old_val);

    tex[input.uvw] = value;
    tex.sample[input.s][input.uvw] = value;
    return old_val;
}
