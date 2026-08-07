// Collation crossover probe for microsoft/DirectXShaderCompiler#2530.
//
// NOT a case from #2530's body. This is the construct #2530's only comment
// points at ("Related to #2188"): an array bound reading a COMPONENT OF A
// CONST VECTOR. It contains no float and no conversion, so #2530's own
// mechanism -- CheckICE rejecting an explicit cast whose operand is not a
// FloatingLiteral -- cannot be what fails here.
//
// It still emits err_hlsl_vla, so the two issues share a diagnostic and an
// area while failing at different rules. Captured so that "related, not
// duplicates" is measured rather than asserted.
static const uint2 SIZE2 = uint2(1, 1);

float4 main() : SV_Target
{
    float array[SIZE2.x] = { 1.0f };
    return (float4)0;
}
