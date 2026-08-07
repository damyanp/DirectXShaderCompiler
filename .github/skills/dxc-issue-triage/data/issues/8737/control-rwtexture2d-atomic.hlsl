// #8737 negative control for the silent-UB predicate (match-silent-ub.json).
//
// The identical InterlockedMax, on a NON-multisampled RWTexture2D. This is a
// legitimate, fully supported use: RWTexture2D is in DXIL.rst's "Valid resource
// type" table for AtomicBinOp with 2 active coordinates, so coordinate c2 being
// `undef` here is correct and expected.
//
// It exists because "atomicBinOp with an undef c2" on its own matches this
// perfectly-good shader too. The predicate must therefore ALSO require the UAV to
// be multisampled (`2dMS` in the resource table), and this control is what proves
// it does. Expect: no-match.
struct PSInput {
    uint2 uv : UV;
    uint s : SAMPLE;
};

RWTexture2D<uint> tex;

uint PSMain(PSInput input) : SV_Target0
{
    uint value = 0xDEADBEEF;
    uint old_val;

    InterlockedMax(tex[input.uv], value, old_val);

    tex[input.uv] = value;
    return old_val;
}
