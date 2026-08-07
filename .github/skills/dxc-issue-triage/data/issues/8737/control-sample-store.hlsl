// #8737 negative control for the ICE predicate (match.json = internal_failure).
//
// Same resource, same profile, same `.sample[s][uv]` double subscript -- but a
// STORE instead of an atomic. The reporter states this form is correct and lowers
// to textureStoreSample. If the ICE predicate fires here, it is not discriminating
// between "the MS double subscript" and "an atomic on the MS double subscript",
// and nothing else in this triage means anything.
struct PSInput {
    uint2 uv : UV;
    uint s : SAMPLE;
};

RWTexture2DMS<uint, 2> tex;

uint PSMain(PSInput input) : SV_Target0
{
    uint value = 0xDEADBEEF;

    // uses textureStoreSample with sample index 0 (correct)
    tex[input.uv] = value;

    // uses textureStoreSample with sample index s (correct)
    tex.sample[input.s][input.uv] = value;
    return value;
}
