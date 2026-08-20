// Minimal HLSL covering the three surfaces #5173 says lose their semantic
// annotation when walked through IDxcCursor: a struct field, a function
// parameter, and a function return type.
struct PSInput
{
    float4 position : SV_POSITION;
    float2 uv : TEXCOORD0;
};

float4 main(PSInput input, float3 normal : NORMAL0) : SV_TARGET
{
    return float4(input.uv, 0, 1);
}
