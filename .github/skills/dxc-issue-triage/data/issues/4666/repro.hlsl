// Issue 4666 -- a function parameter of sampler-array type is rejected as an
// incomplete type.
//
// The single-line form is the reproduction published in the issue thread by
// llvm-beanz (https://godbolt.org/z/39Khq117f). An entry point is added so the
// same source compiles under a non-library profile, which reaches further back
// through the release history than the lib_6_6 of the linked session.
//
// The paired positive control is control-struct-first.hlsl: byte-identical
// apart from an unreferenced `struct Resources { SamplerState Samplers[2]; };`
// ahead of this function, which the issue body says makes the error disappear.
void Reflection(Texture2D<float4> Textures[4], SamplerState Samplers[2]) {}

float4 main() : SV_Target
{
    return 0;
}
