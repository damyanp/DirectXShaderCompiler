// #8737 -- does the ICE depend on the sample index being dynamic?
//
// Same as repro.hlsl but with a CONSTANT sample index and a different atomic
// (InterlockedAdd rather than InterlockedMax). If this also fails internally, the
// defect is "any atomic through the .sample[][] subscript", not one spelling of it.
struct PSInput {
    uint2 uv : UV;
    uint s : SAMPLE;
};

RWTexture2DMS<uint, 2> tex;

uint PSMain(PSInput input) : SV_Target0
{
    uint value = 0xDEADBEEF;
    uint old_val;

    InterlockedAdd(tex.sample[0][input.uv], value, old_val);

    return old_val;
}
