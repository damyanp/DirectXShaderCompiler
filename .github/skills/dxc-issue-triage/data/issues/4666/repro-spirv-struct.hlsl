// Issue 4666, second reported symptom -- the struct workaround breaks SPIR-V.
//
// The issue body says that wrapping the samplers in a struct and passing that
// struct to the function "fixes the error for DXIL", but that compiling the
// same shader for SPIR-V fails with
//
//   fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-None-04667]
//   In Vulkan, OpTypeStruct must not contain an opaque type.
//     %Test = OpTypeStruct %_arr_type_sampler_uint_2
//
// FIDELITY NOTE. A first reconstruction of this used a plain (inlinable)
// helper and compiled clean on every release tested, including the ones
// contemporary with the report -- DXC's SPIR-V path inlines the helper, the
// struct never needs a type, and no OpTypeStruct is emitted. The struct type
// only reaches the validator when the function survives inlining, which is why
// `[noinline]` is here. With it, v1.7.2207 emits the reporter's message
// character-for-character, operand included: `%Test = OpTypeStruct
// %_arr_type_sampler_uint_2`. The struct is named `Test` because that is the
// name in the quoted diagnostic (the body's prose calls it `Resources`).
//
// `[noinline]` is a deviation from anything the reporter wrote; their real
// shader is a ray-tracing helper that evidently was not inlined. Its only job
// is to keep the struct alive to codegen. control-spirv-struct-inlined.hlsl is
// the same file without it, and compiles clean -- that pair is what shows the
// attribute is a means of exposing the defect rather than the defect itself.
struct Test
{
    SamplerState Samplers[2];
};

Texture2D<float4> g_Tex;
SamplerState g_S[2];

[noinline] float4 Reflection(Test Res, float2 uv)
{
    return g_Tex.SampleLevel(Res.Samplers[0], uv, 0);
}

float4 main(float2 uv : TEXCOORD) : SV_Target
{
    Test t;
    t.Samplers[0] = g_S[0];
    t.Samplers[1] = g_S[1];
    return Reflection(t, uv);
}
