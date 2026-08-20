// Control: identical to repro.hlsl but the literal index into `_pad` is
// in-bounds (0 instead of 2000). Proves the OpAccessChain/anchor and general
// codegen shape are unaffected by the index value itself -- any difference in
// diagnostics between this and the primary repro is attributable to the
// literal being out-of-bounds, not to some unrelated property of the shader.
struct LineStyle
{
    float phaseShift;
    uint _pad[1u];
};
[[vk::binding(3, 0)]] StructuredBuffer<LineStyle> lineStyles : register(t1);


struct PSInput
{
    float4 position : SV_Position;
};

float4 main(PSInput input) : SV_TARGET
{
    return float(lineStyles[45]._pad[0]).xxxx;
}
