// #8737 case A -- "silent UB". The reporter's shader VERBATIM, exactly as filed
// (https://github.com/microsoft/DirectXShaderCompiler/issues/8737), including the
// commented-out case B line. Compiled with -T ps_6_7 -E PSMain.
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
    // Note that for a non-MS texture RGA only passes two registers for coordinates,
    // so the hardware can actually do MS atomics (see Image Opcodes with No Sampler in ISA docs),
    // but would require a new Shader Model since atomicBinOp can't.
    InterlockedMax(tex[input.uv], value, old_val);

    // error: cast<X>() argument of incompatible type!
    // This should be a more user friendly error message.
    // InterlockedMax(tex.sample[input.s][input.uv], value, old_val);

    // --- Consistency checks, no bugs ---
    // uses textureStoreSample with sample index 0 (correct)
    tex[input.uv] = value;

    // uses textureStoreSample with sample index s (correct)
    tex.sample[input.s][input.uv] = value;
    return old_val;
}
