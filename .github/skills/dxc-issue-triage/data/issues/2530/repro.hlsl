// microsoft/DirectXShaderCompiler#2530 -- case 1, verbatim from the issue body.
// The array bound applies a type conversion to a `static const float`.
static const float ARRAY_SIZE = 1;

float4 main() : SV_Target
{
    float array[uint(ARRAY_SIZE)] = { 1.0f };
    return (float4)0;
}
