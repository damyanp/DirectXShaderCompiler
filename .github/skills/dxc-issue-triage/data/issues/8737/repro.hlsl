// #8737 case B -- the ICE. The reporter's shader with the ONE change the report
// asks for: the line they left commented out is made live, and the implicit-sample
// atomic is commented out instead. Everything else is verbatim.
//
// The two cases must be separate translation units: an internal failure aborts the
// compile, so with both live case B would destroy the DXIL that case A is about.
struct PSInput {
    uint2 uv : UV;
    uint s : SAMPLE;
};

RWTexture2DMS<uint, 2> tex;

uint PSMain(PSInput input) : SV_Target0
{
    uint value = 0xDEADBEEF;
    uint old_val;

    // atomicBinOp cannot pass a sample index. RGA passes an uninitialized register (v5)!
    // This should be an error!
    // InterlockedMax(tex[input.uv], value, old_val);

    // error: cast<X>() argument of incompatible type!
    // This should be a more user friendly error message.
    InterlockedMax(tex.sample[input.s][input.uv], value, old_val);

    // --- Consistency checks, no bugs ---
    // uses textureStoreSample with sample index 0 (correct)
    tex[input.uv] = value;

    // uses textureStoreSample with sample index s (correct)
    tex.sample[input.s][input.uv] = value;
    return old_val;
}
